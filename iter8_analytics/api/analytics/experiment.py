"""
Module containing classes to run an iteration of an iter8 eperiment, and return assessment and recommendations
"""
# core python dependencies
import logging
from typing import Dict

# iter8 dependencies
from iter8_analytics.api.analytics.types import *
from iter8_analytics.api.analytics.metrics import *
from iter8_analytics.api.analytics.utils import *
from iter8_analytics.constants import ITER8_REQUEST_COUNT

logger = logging.getLogger('iter8_analytics')

class DetailedVersion():
    """Base class for a version.

    Attributes:
        spec (str): version spec
        id (str): unique iter8id of this version. contained in spec.
        is_baseline (bool): boolean indicating if this is the baseline version
        experiment (Experiment): parent experiment object to which this detailed version belongs
    """
    def __init__(self, spec, is_baseline, experiment):
        """Initialize detailed version object.

        Args:
            spec (str): version spec
            id (str): unique iter8id of this version. contained in spec.
            is_baseline (bool): boolean indicating if this is the baseline version
            experiment (Experiment): parent experiment object to which this detailed version belongs
        """
        self.spec = spec
        self.id = spec.id
        self.is_baseline = is_baseline
        self.experiment = experiment
        """linked back to parent experiment to which this version belongs
        """

        self.aggregated_counter_metrics = {
            metric_id: AggregatedCounterDataPoint() for metric_id in self.experiment.counter_metric_specs
        }
        self.aggregated_ratio_metrics = {
            metric_id: AggregatedRatioDataPoint() for metric_id in self.experiment.ratio_metric_specs
        }

        if experiment.eip.last_state:
            if experiment.eip.last_state.aggregated_counter_metrics:
                if self.id in experiment.eip.last_state.aggregated_counter_metrics:
                    for metric_id in experiment.eip.last_state.aggregated_counter_metrics[self.id]:
                        self.aggregated_counter_metrics[metric_id] = experiment.eip.last_state.aggregated_counter_metrics[self.id][metric_id]

            if experiment.eip.last_state.aggregated_ratio_metrics:
                if self.id in experiment.eip.last_state.aggregated_ratio_metrics:
                    for metric_id in experiment.eip.last_state.aggregated_ratio_metrics[self.id]:
                        self.aggregated_ratio_metrics[metric_id] = experiment.eip.last_state.aggregated_ratio_metrics[self.id][metric_id]
        """populated aggregated counter and ratio metrics
        """

    def aggregate_counter_metrics(self, new_counter_metrics: Dict[iter8id, CounterDataPoint]):
        """combine aggregated counter metrics from last state for this version with new counter metrics. Aggregated results stored in self.aggregated_counter_metrics

        Args:
            new_counter_metrics (Dict[iter8id, CounterDataPoint]): dictionary mapping from metric id to CounterDataPoint
        """
        for metric_id in new_counter_metrics:
            if new_counter_metrics[metric_id].value is not None:
                self.aggregated_counter_metrics[metric_id] = AggregatedCounterDataPoint(
                    ** new_counter_metrics[metric_id].dict()
                )
            # else: # new counter is none, so we will retain old value
            #     pass
        
    def aggregate_ratio_metrics(self, new_ratio_metrics: Dict[iter8id, RatioDataPoint]):
        """combine aggregated ratio metrics from last state for this version with new ratio metrics. Aggregated results stored in self.aggregated_ratio_metrics

        Args:
            new_ratio_metrics (Dict[iter8id, RatioDataPoint]): dictionary mapping from metric id to RatioDataPoint
        """
        for metric_id in new_ratio_metrics:
            if new_ratio_metrics[metric_id].value is not None:
                self.aggregated_ratio_metrics[metric_id] = AggregatedRatioDataPoint(
                    ** new_ratio_metrics[metric_id].dict()
                )
            # else: # new ratio is none, so we will retain old value
            #     pass


    def set_ratio_max_mins(self, ratio_max_mins):
        """Update max and min for each ratio metric. Updated values are stored in self.ratio_max_mins

        Args:
            ratio_max_mins (Dict[iter8id, RatioMaxMin]): dictionary mapping from metric id to RatioMaxMin
        """
        self.ratio_max_mins = ratio_max_mins

    def update_beliefs(self):
        """Update beliefs for ratio metrics. If belief update is not possible due to insufficient data, then the relevant status codes are populated here
        """
        # for rms in self.spec.metric_specs.ratio_metrics:
        #     metric_spec.update_belief()
        pass

    def create_posterior_samples(self):
        """Create posterior samples used for assessment and traffic routing
        """
        self.create_ratio_metric_samples()
        self.create_utility_samples()

    def create_ratio_metric_samples(self):
        """Create ratio metric samples used for assessment and traffic routing
        """
        pass

    def create_utility_samples(self):
        """Create utility samples used for assessment and traffic routing
        """
        pass

    def create_assessment(self):
        """Create assessment for this version. Results are stored in self.criterion_assessments
        """
        self.criterion_assessments = []
        for criterion in self.experiment.eip.criteria:
            if criterion.metric_id in self.aggregated_counter_metrics:
                self.criterion_assessments.append(CriterionAssessment(
                    id = criterion.id,
                    metric_id = criterion.metric_id,
                    statistics = Statistics(
                        value = self.aggregated_counter_metrics[criterion.metric_id].value
                    )
                ))
            else: # criterion.metric_id in self.aggregated_ratio_metrics
                self.criterion_assessments.append(CriterionAssessment(
                    id = criterion.id,
                    metric_id = criterion.metric_id,
                    statistics = Statistics(
                        value = self.aggregated_ratio_metrics[criterion.metric_id].value
                    )
                ))

class DetailedBaselineVersion(DetailedVersion):
    def __init__(self, spec, experiment):
        super().__init__(spec, True, experiment)

class DetailedCandidateVersion(DetailedVersion):
    def __init__(self, spec, experiment):
        super().__init__(spec, False, experiment)

class Experiment():
    """The experiment class which provides necessary methods for running a single iteration of an iter8 experiment
    """

    def __init__(self, eip: ExperimentIterationParameters): 
        """Initialize the experiment object.

        Args:
            eip (ExperimentIterationParameters): Experiment iteration parameters

        Raises:
            KeyError: Ratio metrics contain metric ids other than counter metric ids in their numerator or denominator. Also when unknown metric id is found in criteria
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
            logger.warning("iter8_request_count metric is missing in metric specs")
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
                    raise(ke)
            else:
                """this is an unknown metric id
                """
                logger.error(f"Unknown metric id found in criteria: {cri.metric_id}")
                raise KeyError(f"Unknown metric id found in criteria: {cri.metric_id}")    
        """Initialized counter and ratio metric specs relevant to this experiment
        """

        self.detailed_versions = {
            spec.id: DetailedCandidateVersion(spec, self) for spec in self.eip.candidates
        }
        self.detailed_versions[self.eip.baseline.id] = DetailedBaselineVersion(self.eip.baseline, self)
        """Initialized detailed versions
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
            detailed_version.set_ratio_max_mins(self.ratio_max_mins)
        
        self.aggregated_ratio_metrics = self.get_aggregated_ratio_metrics()

        for detailed_version in self.detailed_versions.values():
            detailed_version.update_beliefs()
            detailed_version.create_posterior_samples()
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
            version_id: self.detailed_versions[version_id].aggregated_counter_metrics for version_id in self.detailed_versions
        }

    def get_aggregated_ratio_metrics(self):
        """Get aggregated ratio metrics for this detailed version
        
        Returns:
            a dictionary (Dict[iter8id, AggregatedRatioMetric]): dictionary mapping metric id to an aggregated ratio metric for this version
        """  
        return {
            version_id: self.detailed_versions[version_id].aggregated_ratio_metrics for version_id in self.detailed_versions            
        }

    def get_ratio_max_mins(self):
        """Get ratio max mins
        
        Returns:
            a dictionary (Dict[iter8id, RatioMaxMin]): dictionary mapping metric ids to RatioMaxMin for this version
        """  
        metric_id_to_list_of_values = {
            metric_id: [] for metric_id in self.ratio_metric_specs
        }

        if self.eip.last_state:
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
        pass

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
        pass

    def create_top_2_recommendation(self):
        """Create traffic recommendations for the progressive strategy -- uses the top-2 posterior Bayesian routing (top-2 PBR) algorithm
        """
        pass

    def create_uniform_recommendation(self):
        """Create traffic recommendations based on uniform traffic split
        """
        self.traffic_split["uniform"] = {}
        integral_split_gen = gen_round([100/len(self.detailed_versions)]*len(self.detailed_versions), 100) # round the uniform split so that it sums up to 100
        # assign one of the rounded splits to a detailed_version
        for key in self.detailed_versions:
            self.traffic_split["uniform"][key] = next(integral_split_gen)
        """Split traffic uniformly across versions and round
        """

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
            request_count = None
            if ITER8_REQUEST_COUNT in self.counter_metric_specs:
                request_count = version.aggregated_counter_metrics[ITER8_REQUEST_COUNT].value
            else:
                logger.warning("iter8_request_count metric is missing in metric specs")

            if version.is_baseline:
                baseline_assessment = VersionAssessment(
                    id = version.id,
                    request_count = request_count,
                    criterion_assessments = version.criterion_assessments,
                    win_probability = 1/len(self.detailed_versions)
                )
            else:
                candidate_assessments.append(CandidateVersionAssessment(
                    id = version.id,
                    request_count = request_count,
                    criterion_assessments = version.criterion_assessments,
                    win_probability = 1/len(self.detailed_versions)
                ))
            """populated baseline and candidate assessments
            """
        it8ar = Iter8AssessmentAndRecommendation(** {
            "timestamp": datetime.now(),
            "baseline_assessment": baseline_assessment,
            "candidate_assessments": candidate_assessments,
            "traffic_split_recommendation": self.traffic_split,
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
