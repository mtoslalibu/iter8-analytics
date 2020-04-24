"""
Class and methods to run an iteration of an iter8 eperiment, and return assessment and recommendations
"""
import logging

from iter8_analytics.api.analytics.experiment_iteration_request import ExperimentIterationParameters, RatioMetricSpec

from iter8_analytics.api.analytics.experiment_iteration_response import Iter8AssessmentAndRecommendation

from iter8_analytics.api.analytics.endpoints.examples import ar_example

from iter8_analytics.api.analytics.metrics import *

from iter8_analytics.api.analytics.utils import *

logger = logging.getLogger(__name__)

class DetailedVersion():
    """A version class which yields version assessments"""
    def __init__(self, spec, is_baseline):
        self.spec = spec
        self.is_baseline = is_baseline

    def set_aggregated_counter_metric_data(self, acmdpv):
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
            # if counter metric...
            # else if ratio metric...
              # find numerator counter metric ... else raise exception
              # find denominator counter metric... else raise exception
            # else raise exception
        self.detailed_versions = {}
        self.detailed_versions[self.eip.baseline.id] = DetailedVersion(self.eip.baseline, True)
        for vspec in self.eip.candidates:
            self.detailed_versions[vspec.id] = DetailedVersion(vspec, False)
        self.traffic_split = {}

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
        ocmd = None # old counter metric data
        if self.eip.last_state:
            if "counter_metric_data" in self.eip.last_state:
                ocmd = self.eip.last_state["counter_metric_data"]

        # Lineup inputs needed to query relevant counter metrics
        #   Convert all counter and ratio metrics into dictionaries... 
        cspec_dict = {}
        for cs in self.eip.metric_specs.counter_metrics:
            cspec_dict[cs.id] = cs
        rspec_dict = {}
        for rs in self.eip.metric_specs.ratio_metrics:
            rspec_dict[rs.id] = rs
        
        #   Go through all criteria and pick up relevant counter metric specs
        rcms = {} # relevant counter metric specs
        for criterion in self.eip.criteria:
            if criterion.metric_id in cspec_dict:
                rcms[criterion.metric_id] = cspec_dict[criterion.metric_id]
            else:
                try:
                    # get the relevant ratio metric spec
                    rms = rspec_dict[criterion.metric_id]
                    rcms[rms.numerator] = cspec_dict[rms.numerator]
                    rcms[rms.denominator] = cspec_dict[rms.denominator]
                except KeyError as ke:
                    logger.error(ke)
                    logger.error("RSpec dict")
                    logger.error(rspec_dict)
                    logger.error("CSpec dict")
                    logger.error(cspec_dict)
                    raise(ke)

        # Pick up version ids
        version_ids = self.detailed_versions.keys()

        ncmd = get_counter_metric_data(rcms, version_ids)
        acmd = aggregate_counter_metric_data(ocmd, ncmd) # aggregated data
        for cm in acmd: # for each counter metric in acmd
            for ver in acmd[cm]: # for each version for with aggregated counter metric data
                self.detailed_versions[ver].set_aggregated_counter_metric_data(acmd[cm][ver])

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
        it8ar = Iter8AssessmentAndRecommendation(** ar_example)
        it8ar.traffic_split_recommendation = self.traffic_split
        return it8ar

