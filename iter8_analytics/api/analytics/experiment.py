"""
Class and methods to run an iteration of an iter8 eperiment, and return assessment and recommendations
"""
import logging
from uuid import UUID
from typing import Union, Dict

from iter8_analytics.api.analytics.experiment_iteration_request import ExperimentIterationParameters, RatioMetricSpec, Version

from iter8_analytics.api.analytics.experiment_iteration_response import *

from iter8_analytics.api.analytics.endpoints.examples import ar_example

from iter8_analytics.api.analytics.metrics import *

from iter8_analytics.api.analytics.utils import *

logger = logging.getLogger(__name__)

class DetailedVersion():
    def __init__(self, spec, is_baseline, experiment):
        self.id = spec.id
        self.labels = spec.version_labels
        self.is_baseline = is_baseline
        self.experiment = experiment # parent experiment to which this version belongs
        # dictionary(metric id -> aggregated counter metric data point)

        # get stuff from last state here and set old here... 
        self.old_aggregated_counter_metric_data: Dict[[str, int, UUID], AggregatedCounterDataPoint] = {}
            
        if experiment.eip.last_state:
            self.old_aggregated_counter_metric_data = experiment.eip.last_state['version_data'][self.id]['aggregated_counter_metric_data']
        else:
            for metric_id in self.experiment.experiment_counter_metric_specs:
                self.old_aggregated_counter_metric_data[metric_id] = AggregatedCounterDataPoint()

        self.old_aggregated_ratio_metric_data: Dict[[str, int, UUID], AggregatedRatioDataPoint] = {}
            
        if experiment.eip.last_state:
            self.old_aggregated_ratio_metric_data = experiment.eip.last_state['version_data'][self.id]['aggregated_ratio_metric_data']
        else:
            for metric_id in self.experiment.experiment_ratio_metric_specs:
                self.old_aggregated_ratio_metric_data[metric_id] = AggregatedRatioDataPoint()

        # these will get populated through their respective update methods
        self.aggregated_counter_metric_data: Dict[Union[str, int, UUID], AggregatedCounterDataPoint] = {}
        self.aggregated_ratio_metric_data: Dict[Union[str, int, UUID], AggregatedRatioDataPoint] = {}

    def update_counter_metrics(self, new_counter_metrics: Dict[Union[str, int, UUID], CounterDataPoint]):
        # for each counter metric, update the aggregated counter metric data
        for metric_id in new_counter_metrics:
            old_value = self.old_aggregated_counter_metric_data[metric_id].value
            if new_counter_metrics[metric_id].value is not None:
                self.aggregated_counter_metric_data[metric_id] = AggregatedCounterDataPoint(
                    value = new_counter_metrics[metric_id].value,
                    timestamp = new_counter_metrics[metric_id].timestamp,
                    delta_value = new_counter_metrics[metric_id].value - old_value if old_value is not None else None,
                    delta_timestamp = new_counter_metrics[metric_id].timestamp - self.old_aggregated_counter_metric_data[metric_id].timestamp if old_value is not None else None
                )
            else:
                self.aggregated_counter_metric_data[metric_id] = self.old_aggregated_counter_metric_data[metric_id]
        
    def update_ratio_metrics(self):
        for ms in self.experiment.experiment_ratio_metric_specs.values():
            # get value
            num = ms.numerator
            den = ms.denominator
            current_ratio = None
            # values are available for numerator and denominator and they were computed in times close to each other
            self.aggregated_ratio_metric_data[ms.id] = self.old_aggregated_ratio_metric_data[ms.id]
            if self.aggregated_counter_metric_data[den].value:
                if self.aggregated_counter_metric_data[num].value is not None: 
                    delta_timestamp = self.aggregated_counter_metric_data[num].timestamp - self.aggregated_counter_metric_data[den].timestamp
                    # num and den timestamps are 100 msec apart
                    if delta_timestamp.total_seconds() < 0.1: 
                        self.aggregated_counter_metric_data[ms.id] = AggregatedRatioDataPoint(
                            value = self.aggregated_counter_metric_data[num].value / self.aggregated_counter_metric_data[den].value,
                            timestamp = self.aggregated_counter_metric_data[num].timestamp + (delta_timestamp / 2),
                            maximum = None,
                            minimum = None
                        )
            # next get max and min... passing for now

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
        self.criterion_assessments = []
        for criterion in self.experiment.eip.criteria:
            if criterion.metric_id in self.aggregated_counter_metric_data:
                self.criterion_assessments.append(CriterionAssessment(
                    id = criterion.id,
                    metric_id = criterion.metric_id,
                    statistics = Statistics(
                        value = self.aggregated_counter_metric_data[criterion.metric_id].value
                    )
                ))
            elif criterion.metric_id in self.aggregated_ratio_metric_data:
                self.criterion_assessments.append(CriterionAssessment(
                    id = criterion.id,
                    metric_id = criterion.metric_id,
                    statistics = Statistics(
                        value = self.aggregated_ratio_metric_data[criterion.metric_id].value
                    )
                ))
            else:
                logger.error("Criterion metric is neither counter nor ratio")
                logger.error(criterion)
                raise ValueError("Criterion metric_id is neither counter nor ratio")

class DetailedBaselineVersion(DetailedVersion):
    def __init__(self, spec, experiment):
        super().__init__(spec, True, experiment)

class DetailedCandidateVersion(DetailedVersion):
    def __init__(self, spec, experiment):
        super().__init__(spec, False, experiment)

class Experiment():
    """The main experiment class"""

    def __init__(self, eip: ExperimentIterationParameters):  
        self.eip = eip

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

        # Initialize detailed versions
        self.detailed_versions = {}
        self.detailed_versions[self.eip.baseline.id] = DetailedBaselineVersion(self.eip.baseline, self)
        for spec in self.eip.candidates:
            self.detailed_versions[spec.id] = DetailedCandidateVersion(spec, self)

    def run(self) -> Iter8AssessmentAndRecommendation:
        """Perform a single iteration of the experiment and output assessment and recommendation"""  
        self.update_counter_metric_data()
        for detailed_version in self.detailed_versions.values():
            detailed_version.update_counter_metrics(self.new_counter_metric_data[detailed_version.id])
            detailed_version.update_ratio_metrics()
            detailed_version.update_beliefs()
            detailed_version.create_posterior_samples()
            detailed_version.create_assessment()
        self.create_winner_assessments()
        self.create_traffic_recommendations()
        return self.assemble_assessment_and_recommendations()

    def update_counter_metric_data(self):
        """Query prometheus to update counter metric data. Prometheus instance creation, and all prometheus related errors are detected and the relevant status codes are populated here..."""
        # Pick up version ids
        version_ids = self.detailed_versions.keys()

        # version id -> dictionary(metric id -> counter data point)
        self.new_counter_metric_data: Dict[Union[str, int, UUID],  Dict[Union[str, int, UUID], CounterDataPoint]] = get_counter_metric_data(self.experiment_counter_metric_specs, version_ids, self.eip.start_time)

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
                    id = version.id,
                    request_count = 0,
                    criterion_assessments = version.criterion_assessments,
                    win_probability = 1/len(self.detailed_versions)
                )
            else:
                candidate_assessments.append(CandidateVersionAssessment(
                    id = version.id,
                    request_count = 0,
                    criterion_assessments = version.criterion_assessments,
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

