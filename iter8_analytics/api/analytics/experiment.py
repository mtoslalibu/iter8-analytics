"""
Class and methods to run an iteration of an iter8 eperiment, and return assessment and recommendations
"""
import logging

from iter8_analytics.api.analytics.experiment_iteration_request import ExperimentIterationParameters, RatioMetricSpec

from iter8_analytics.api.analytics.experiment_iteration_response import Iter8AssessmentAndRecommendation, VersionAssessment, CandidateVersionAssessment, WinnerAssessment

from iter8_analytics.api.analytics.endpoints.examples import ar_example

from iter8_analytics.api.analytics.metrics import *

from iter8_analytics.api.analytics.utils import *

logger = logging.getLogger(__name__)

class DetailedVersion():
    """A version class which yields version assessments"""
    def __init__(self, spec, is_baseline):
        self.spec = spec
        self.is_baseline = is_baseline
        # self.aggregated_counter_metric_data = {}

    def set_aggregated_counter_metric_data(self, metric_id, data):
        """acmdpv: aggregated counter metric data per version"""
        pass

    def update_metrics(self):
        pass

    def update_beliefs(self):
        """Update beliefs for ratio metrics. If belief update is not possible due to insufficient data, then the relevant status codes are populated here"""
        # for rms in self.spec.metric_specs.ratio_metrics:
        #     metric_spec.update_belief()
        pass

    def create_posterior_samples(self):
        """These samples are used for assessment and traffic routing"""
        self.create_ratio_metric_samples()
        self.create_utility_samples()

    def create_ratio_metric_samples(self):
        """These samples are used for assessment and traffic routing"""
        pass

    def create_utility_samples(self):
        """These samples are used for assessment and traffic routing"""
        pass

    def create_assessment(self):
        pass

class Experiment():
    """The main experiment class"""

    def __init__(self, eip: ExperimentIterationParameters):  
        self.eip = eip

        # Initialize detailed versions
        self.detailed_versions = {}
        self.detailed_versions[self.eip.baseline.id] = DetailedVersion(self.eip.baseline, True)
        for vspec in self.eip.candidates:
            self.detailed_versions[vspec.id] = DetailedVersion(vspec, False)

        # Declare traffic split dictionary
        self.traffic_split = {}

        # Get all counter and ratio metric specs into dictionaries
        self.all_counter_metric_specs = {}
        for cms in self.eip.metric_specs.counter_metrics:
            self.all_counter_metric_specs[cms.id] = cms
        self.all_ratio_metric_specs = {}
        for rms in self.eip.metric_specs.ratio_metrics:
            self.all_ratio_metric_specs[rms.id] = rms

        # Initialize counter and ratio metric specs relevant to this experiment
        self.experiment_counter_metric_specs = {}
        self.experiment_ratio_metric_specs = {}
        for cri in self.eip.criteria:
            if cri.metric_id in self.all_counter_metric_specs:
                self.experiment_counter_metric_specs[cri.metric_id] = self.all_counter_metric_specs[cri.metric_id]
            elif cri.metric_id in self.all_ratio_metric_specs:
                self.experiment_ratio_metric_specs[cri.metric_id] = self.all_ratio_metric_specs[cri.metric_id]
                num = self.experiment_ratio_metric_specs[cri.metric_id].numerator
                den = self.experiment_ratio_metric_specs[cri.metric_id].denominator
                try:
                    self.experiment_counter_metric_specs[num] = self.all_counter_metric_specs[num]
                    self.experiment_counter_metric_specs[den] = self.all_counter_metric_specs[den]
                except KeyError as ke: # unknown numerator or denominator
                    logger.error(ke)
                    raise(ke)
            else: # unknown metric id
                logger.error(f"Unknown metric id found in criteria: {cri.metric_id}")
                raise Exception(f"Unknown metric id found in criteria: {cri.metric_id}")

    def run(self) -> Iter8AssessmentAndRecommendation:
        """Perform a single iteration of the experiment and output assessment and recommendation"""  
        self.update_counter_metric_data()
        for detailed_version in self.detailed_versions.values():
            detailed_version.update_metrics()
            detailed_version.update_beliefs()
            detailed_version.create_posterior_samples()
            detailed_version.create_assessment()
        self.create_winner_assessments()
        self.create_traffic_recommendations()
        return self.assemble_assessment_and_recommendations()

    def update_counter_metric_data(self):
        """Query prometheus to update counter metric data. Prometheus instance creation, and all prometheus related errors are detected and the relevant status codes are populated here..."""
        # Fix old counter metrics
        self.old_counter_metric_data = None
        if self.eip.last_state:
            if "counter_metric_data" in self.eip.last_state:
                self.old_counter_metric_data = self.eip.last_state["counter_metric_data"]

        # Pick up version ids
        version_ids = self.detailed_versions.keys()

        self.new_counter_metric_data = get_counter_metric_data(self.experiment_counter_metric_specs, version_ids)

        aggregated_counter_metric_data = aggregate_counter_metric_data(self.old_counter_metric_data, self.new_counter_metric_data) # aggregated data
        for acm in aggregated_counter_metric_data: # for each aggregated counter metric data point
            for ver in aggregated_counter_metric_data[acm]: # for each version with aggregated counter metric data
                self.detailed_versions[ver].set_aggregated_counter_metric_data(acm, aggregated_counter_metric_data[acm][ver])
        logger.debug("Aggregated counter metric data")
        logger.debug(aggregated_counter_metric_data)

    def create_winner_assessments(self):
        """Create winner assessment. If winner cannot be created due to insufficient data, then the relevant status codes are populated"""
        pass

    def create_traffic_recommendations(self):
        """Create traffic recommendations for individual algorithms"""
        self.create_epsilon_greedy_recommendation()
        self.create_pbr_recommendation() # PBR  = posterior Bayesian sampling
        self.create_top_2_pbr_recommendation()
        self.create_uniform_recommendation()
        self.mix_recommendations() # after taking into account step size and current split

    def create_epsilon_greedy_recommendation(self):
        pass

    def create_pbr_recommendation(self):
        pass

    def create_top_2_pbr_recommendation(self):
        pass

    def create_uniform_recommendation(self):
        """Split the traffic uniformly across versions"""
        self.traffic_split["unif"] = {}
        integral_split_gen = gen_round([100/len(self.detailed_versions)]*len(self.detailed_versions), 100) # round the uniform split so that it sums up to 100
        # assign one of the rounded splits to a detailed_version
        for key in self.detailed_versions:
            self.traffic_split["unif"][key] = next(integral_split_gen)

    def mix_recommendations(self):
        """Create the final traffic recommendation"""
        pass

    def assemble_assessment_and_recommendations(self):
        """Create and return the final assessment and recommendation"""
        
        baseline_assessment = None
        candidate_assessments = []
        for version in self.detailed_versions.values():
            if version.is_baseline:
                baseline_assessment = VersionAssessment(
                    id = version.spec.id,
                    request_count = 0,
                    criterion_assessments = [],
                    win_probability = 1/len(self.detailed_versions)
                )
            else:
                candidate_assessments.append(CandidateVersionAssessment(
                    id = version.spec.id,
                    request_count = 0,
                    criterion_assessments = [],
                    win_probability = 1/len(self.detailed_versions)
                ))
        it8ar = Iter8AssessmentAndRecommendation(** {
            "timestamp": datetime.now(),
            "baseline_assessment": baseline_assessment,
            "candidate_assessments": candidate_assessments,
            "traffic_split_recommendation": self.traffic_split,
            "winner_assessment": WinnerAssessment(
                winning_version_found = False
            ),
            "status": []
        })
        return it8ar

