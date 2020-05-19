"""
Class and methods to run an iteration of an iter8 eperiment, and return assessment and recommendations
"""
# core python stuff
import logging
from typing import Dict

# iter8 stuff
from iter8_analytics.api.analytics.types import *
from iter8_analytics.api.analytics.metrics import *
from iter8_analytics.api.analytics.utils import *

logger = logging.getLogger('iter8_analytics')

class DetailedVersion():
    def __init__(self, spec, is_baseline, experiment):
        self.spec = spec
        self.id = spec.id
        self.is_baseline = is_baseline
        self.experiment = experiment
        """parent experiment to which this version belongs"""

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

        """populated aggregated counter and ratio metrics"""

    def aggregate_counter_metrics(self, new_counter_metrics: Dict[iter8id, CounterDataPoint]):
        for metric_id in new_counter_metrics:
            if new_counter_metrics[metric_id].value is not None:
                self.aggregated_counter_metrics[metric_id] = AggregatedCounterDataPoint(
                    ** new_counter_metrics[metric_id].dict()
                )
        
    def aggregate_ratio_metrics(self, new_ratio_metrics: Dict[iter8id, RatioDataPoint]):
        for metric_id in new_ratio_metrics:
            if new_ratio_metrics[metric_id].value is not None:
                self.aggregated_ratio_metrics[metric_id] = AggregatedRatioDataPoint(
                    ** new_ratio_metrics[metric_id].dict()
                )

    def set_ratio_max_mins(self, ratio_max_mins):
        self.ratio_max_mins = ratio_max_mins

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
    """The experiment class which provides necessary methods for running a single iteration of an iter8 experiment"""

    def __init__(self, eip: ExperimentIterationParameters): 
        """Initialize the experiment object.

        Args:
            eip (ExperimentIterationParameters): Experiment iteration parameters

        Raises:
            KeyError: Ratio metrics contain metric ids other than counter metric ids in their numerator or denominator. Also when unknown metric id is found in criteria
        """

        self.eip = eip

        self.traffic_split = {} 
        """Initialized traffic split dictionary"""
 
        all_counter_metric_specs = {}
        all_ratio_metric_specs = {}
        for cms in self.eip.metric_specs.counter_metrics: 
            all_counter_metric_specs[cms.id] = cms
        for rms in self.eip.metric_specs.ratio_metrics: 
            all_ratio_metric_specs[rms.id] = rms
        """Got all counter and ratio metric specs into their respective dictionaries"""

        self.counter_metric_specs = {}
        self.ratio_metric_specs = {}
        for cri in self.eip.criteria:
            if cri.metric_id in all_counter_metric_specs:
                """this is a counter metric"""
                self.counter_metric_specs[cri.metric_id] = all_counter_metric_specs[cri.metric_id]
            elif cri.metric_id in all_ratio_metric_specs:
                """this is a ratio metric"""
                self.ratio_metric_specs[cri.metric_id] = all_ratio_metric_specs[cri.metric_id]
                num = self.ratio_metric_specs[cri.metric_id].numerator
                den = self.ratio_metric_specs[cri.metric_id].denominator
                try:
                    self.counter_metric_specs[num] = all_counter_metric_specs[num]
                    self.counter_metric_specs[den] = all_counter_metric_specs[den]
                except KeyError as ke:
                    """unknown numerator or denominator"""
                    logger.error(f"Unknown numerator or denominator found: {ke}")
                    raise(ke)
            else:
                """this is an unknown metric id"""
                logger.error(f"Unknown metric id found in criteria: {cri.metric_id}")
                raise KeyError(f"Unknown metric id found in criteria: {cri.metric_id}")    
        """Initialized counter and ratio metric specs relevant to this experiment"""

        self.detailed_versions = {
            spec.id: DetailedCandidateVersion(spec, self) for spec in self.eip.candidates
        }
        self.detailed_versions[self.eip.baseline.id] = DetailedBaselineVersion(self.eip.baseline, self)
        """Initialized detailed versions"""

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
        """This is in the shape of a Dict[str, RatioMaxMin], where the keys are ratio metric ids and values are their max mins"""

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
        return {
            version_id: self.detailed_versions[version_id].aggregated_counter_metrics for version_id in self.detailed_versions
        }

    def get_aggregated_ratio_metrics(self):
        return {
            version_id: self.detailed_versions[version_id].aggregated_ratio_metrics for version_id in self.detailed_versions            
        }

    def get_ratio_max_mins(self):
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

        return new_ratio_max_min(metric_id_to_list_of_values)

    # until above is get metrics from prometheus

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
            "status": [],
            "last_state": {
                "aggregated_counter_metrics": self.aggregated_counter_metrics,
                "aggregated_ratio_metrics": self.aggregated_ratio_metrics,
                "ratio_max_mins": self.ratio_max_mins
            }
        })
        return it8ar
