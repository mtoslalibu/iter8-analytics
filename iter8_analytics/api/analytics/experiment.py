"""
Module containing classes to run an iteration of an iter8 eperiment, and return assessment and recommendations
"""
# core python dependencies
import logging
from typing import Dict

# external module dependencies
import numpy as np
import pandas as pd
from fastapi import HTTPException

# iter8 dependencies
from iter8_analytics.api.analytics.types import *
from iter8_analytics.api.analytics.metrics import *
from iter8_analytics.api.analytics.utils import *
from iter8_analytics.constants import ITER8_REQUEST_COUNT
import iter8_analytics.api.analytics.detailedversion

# type aliases
DetailedVersion = iter8_analytics.api.analytics.detailedversion.DetailedVersion
DetailedBaselineVersion = iter8_analytics.api.analytics.detailedversion.DetailedBaselineVersion
DetailedCandidateVersion = iter8_analytics.api.analytics.detailedversion.DetailedCandidateVersion

logger = logging.getLogger('iter8_analytics')

class Experiment():
    """The experiment class which provides necessary methods for running a single iteration of an iter8 experiment
    """

    def __init__(self, eip: ExperimentIterationParameters): 
        """Initialize the experiment object.

        Args:
            eip (ExperimentIterationParameters): Experiment iteration parameters

        Raises:
            HTTPException: Ratio metrics contain metric ids other than counter metric ids in their numerator or denominator. Also when unknown metric id is found in criteria
        """

        self.eip = eip

        self.traffic_split = {}
        """Initialized traffic split dictionary
        """
 
        all_counter_metric_specs = {}
        all_ratio_metric_specs = {}
        for cms in self.eip.metric_specs.counter_metrics: 
            all_counter_metric_specs[cms.id] = cms
        for rms in self.eip.metric_specs.ratio_metrics: 
            all_ratio_metric_specs[rms.id] = rms
        # Got all counter and ratio metric specs into their respective dictionaries

        # ITER8_REQUEST_COUNT is a special metric. Lets add this always in counter metrics
        self.counter_metric_specs = {}
        if ITER8_REQUEST_COUNT in all_counter_metric_specs:
            self.counter_metric_specs[ITER8_REQUEST_COUNT] = all_counter_metric_specs[ITER8_REQUEST_COUNT]
        else:
            logger.error("iter8_request_count metric is missing in metric specs")
            raise HTTPException(status_code=422, detail = f"{ITER8_REQUEST_COUNT} is a mandatory counter metric which is missing from the list of metric specs")
        self.ratio_metric_specs = {}

        for cri in self.eip.criteria:
            if cri.metric_id in all_counter_metric_specs:
                """this is a counter metric
                """
                self.counter_metric_specs[cri.metric_id] = all_counter_metric_specs[cri.metric_id]
            elif cri.metric_id in all_ratio_metric_specs:
                """this is a ratio metric
                """
                self.ratio_metric_specs[cri.metric_id] = all_ratio_metric_specs[cri.metric_id]
                num = self.ratio_metric_specs[cri.metric_id].numerator
                den = self.ratio_metric_specs[cri.metric_id].denominator
                try:
                    self.counter_metric_specs[num] = all_counter_metric_specs[num]
                    self.counter_metric_specs[den] = all_counter_metric_specs[den]
                except KeyError as ke:
                    """unknown numerator or denominator
                    """
                    logger.error(f"Unknown numerator or denominator found: {ke}")
                    raise HTTPException(status_code=422, detail=f"Unknown numerator or denominator found: {ke}")
            else:
                """this is an unknown metric id
                """
                logger.error(f"Unknown metric id found in criteria: {cri.metric_id}")
                raise HTTPException(status_code=422, detail=f"Unknown metric id found in criteria: {cri.metric_id}")    
        """Initialized counter and ratio metric specs relevant to this experiment
        """

        self.detailed_candidate_versions = {
            spec.id: DetailedCandidateVersion(spec, self, index + 2) for index, spec in enumerate(self.eip.candidates)
        }
        self.detailed_versions = {
            ver: self.detailed_candidate_versions[ver] for ver in self.detailed_candidate_versions
        }
        self.detailed_baseline_version = DetailedBaselineVersion(self.eip.baseline, self)
        self.detailed_versions[self.eip.baseline.id] = self.detailed_baseline_version
        """Initialized detailed versions. Pseudo reward for baseline = 1.0; pseudo reward for candidate is 2 + its index in the candidates list (i.e., the first candidate has pseudo reward 2.0, 2nd has 3.0, and so on)
        """

    def run(self) -> Iter8AssessmentAndRecommendation:
        """Perform a single iteration of the experiment and return assessment and recommendation
        
        Returns:
            it8ar (Iter8AssessmentAndRecommendation): Iter8 assessment and recommendation
        """  
        self.new_counter_metrics: Dict[iter8id,  Dict[iter8id, CounterDataPoint]] = get_counter_metrics(
            self.counter_metric_specs, 
            [version.spec for version in self.detailed_versions.values()],
            self.eip.start_time
        )
 
        for detailed_version in self.detailed_versions.values():
            detailed_version.aggregate_counter_metrics(self.new_counter_metrics[detailed_version.id])

        self.aggregated_counter_metrics = self.get_aggregated_counter_metrics()

        self.new_ratio_metrics: Dict[iter8id,  Dict[iter8id, RatioDataPoint]] = get_ratio_metrics(
            self.ratio_metric_specs, 
            self.counter_metric_specs, 
            self.aggregated_counter_metrics,
            [version.spec for version in self.detailed_versions.values()],
            self.eip.start_time
        )

        self.ratio_max_mins = self.get_ratio_max_mins()
        """This is in the shape of a Dict[str, RatioMaxMin], where the keys are ratio metric ids and values are their max mins
        """

        for detailed_version in self.detailed_versions.values():
            detailed_version.aggregate_ratio_metrics(
                self.new_ratio_metrics[detailed_version.id]
            )
        
        self.aggregated_ratio_metrics = self.get_aggregated_ratio_metrics()

        self.utilities = pd.DataFrame()

        for detailed_version in self.detailed_versions.values():
            detailed_version.update_beliefs()
            detailed_version.create_posterior_samples()
            self.utilities[detailed_version.id] = detailed_version.get_utility()
            detailed_version.create_assessment()
        self.create_winner_assessments()
        self.create_traffic_recommendations()
        return self.assemble_assessment_and_recommendations()

    def get_aggregated_counter_metrics(self):
        """Get aggregated counter metrics for this detailed version
        
        Returns:
            a dictionary (Dict[iter8id, AggregatedCounterMetric]): dictionary mapping metric id to an aggregated counter metric for this version
        """  
        return {
            version.id: {
                dcm.metric_id: dcm.aggregated_metric for dcm in version.metrics["counter_metrics"].values()
            } for version in self.detailed_versions.values()
        }

    def get_aggregated_ratio_metrics(self):
        """Get aggregated ratio metrics for this detailed version
        
        Returns:
            a dictionary (Dict[iter8id, AggregatedRatioMetric]): dictionary mapping metric id to an aggregated ratio metric for this version
        """  
        return {
            version.id: {
                drm.metric_id: drm.aggregated_metric for drm in version.metrics["ratio_metrics"].values()
            } for version in self.detailed_versions.values()
        }

    def get_ratio_max_mins(self):
        """Get ratio max mins
        
        Returns:
            a dictionary (Dict[iter8id, RatioMaxMin]): dictionary mapping metric ids to RatioMaxMin for this version
        """  
        metric_id_to_list_of_values = {
            metric_id: [] for metric_id in self.ratio_metric_specs
        }

        if self.eip.last_state and self.eip.last_state.ratio_max_mins:
            for metric_id in self.ratio_metric_specs:
                a = self.eip.last_state.ratio_max_mins[metric_id].minimum
                b = self.eip.last_state.ratio_max_mins[metric_id].maximum
                if a is not None:
                    metric_id_to_list_of_values[metric_id].append(a)
                    metric_id_to_list_of_values[metric_id].append(b)

        for version_id in self.new_ratio_metrics:
            for metric_id in self.new_ratio_metrics[version_id]:
                a = self.new_ratio_metrics[version_id][metric_id].value
                if a is not None:
                    metric_id_to_list_of_values[metric_id].append(a)
        """populated the max and min of each metric from last state, along with all the metric values seen for this metric in this iteration. New max min values for each metric will be derived from these.
        """  
        return new_ratio_max_min(metric_id_to_list_of_values)

    def create_winner_assessments(self):
        """Create winner assessment. If winner cannot be created due to insufficient data, then the relevant status codes are populated
        """
        # get the fraction of the time a particular version emerged as the winner
        rank_df = self.utilities.rank(axis = 1, method = 'min')
        low_rank = rank_df <= 1
        self.win_probababilities = low_rank.sum() / low_rank.sum().sum()

    def create_traffic_recommendations(self):
        """Create traffic recommendations for individual algorithms
        """
        self.create_progressive_recommendation() # PBR  = posterior Bayesian sampling
        self.create_top_2_recommendation()
        self.create_uniform_recommendation()
        self.mix_recommendations() # after taking into account step size and current split

    def create_progressive_recommendation(self):
        """Create traffic recommendations for the progressive strategy -- uses the posterior Bayesian routing (PBR) algorithm
        """
        self.create_top_k_recommendation(1)

    def create_top_2_recommendation(self):
        """Create traffic recommendations for the progressive strategy -- uses the top-2 posterior Bayesian routing (top-2 PBR) algorithm
        """
        self.create_top_k_recommendation(2)

    def create_uniform_recommendation(self):
        """Create traffic recommendations based on uniform traffic split
        """
        self.create_top_k_recommendation(len(self.detailed_versions))

    def create_top_k_recommendation(self, k):
        """
        Create traffic split using the top-k PBR algorithm
        """
        self.traffic_split[k] = {}

        # get the fractional split
        rank_df = self.utilities.rank(axis = 1, method = 'min', ascending = False)

        low_rank = rank_df <= k

        fractional_split = low_rank.sum() / low_rank.sum().sum()
        # round the fractional split so that it sums up to 100
        integral_split_gen = gen_round(fractional_split * 100, 100)
        for key in self.utilities:
            self.traffic_split[k][key] = next(integral_split_gen)

    def mix_recommendations(self):
        """Create the final traffic recommendation
        """
        pass

    def assemble_assessment_and_recommendations(self):
        """Create and return the final assessment and recommendation
        """        
        baseline_assessment = None
        candidate_assessments = []
        for version in self.detailed_versions.values():
            request_count = version.metrics["counter_metrics"][ITER8_REQUEST_COUNT].aggregated_metric.value

            if version.is_baseline:
                baseline_assessment = VersionAssessment(
                    id = version.id,
                    request_count = request_count,
                    criterion_assessments = version.criterion_assessments,
                    win_probability = self.win_probababilities[version.id]
                )
            else:
                candidate_assessments.append(CandidateVersionAssessment(
                    id = version.id,
                    request_count = request_count,
                    criterion_assessments = version.criterion_assessments,
                    win_probability = self.win_probababilities[version.id]
                ))

        ts = {
            'progressive': self.traffic_split[1],
            'top_2': self.traffic_split[2],
            'uniform': self.traffic_split[len(self.detailed_versions)]
        }

        it8ar = Iter8AssessmentAndRecommendation(** {
            "timestamp": datetime.now(),
            "baseline_assessment": baseline_assessment,
            "candidate_assessments": candidate_assessments,
            "traffic_split_recommendation": ts,
            "winner_assessment": WinnerAssessment(
                winning_version_found = False
            ),
            "status": [],
            "last_state": {
                "aggregated_counter_metrics": self.aggregated_counter_metrics,
                "aggregated_ratio_metrics": self.aggregated_ratio_metrics,
                "ratio_max_mins": self.ratio_max_mins
            }
        })
        return it8ar
