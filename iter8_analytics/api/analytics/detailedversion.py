"""
Module containing classes to run an iteration of an iter8 eperiment, and return assessment and recommendations
"""
# core python dependencies
import logging
from typing import Dict

# external module dependencies
import numpy as np

# iter8 dependencies
from iter8_analytics.api.analytics.types import *
from iter8_analytics.api.analytics.metrics import *
from iter8_analytics.api.analytics.utils import *
from iter8_analytics.api.analytics.detailedmetrics import *

from iter8_analytics.constants import ITER8_REQUEST_COUNT

logger = logging.getLogger('iter8_analytics')

class DetailedVersion():
    """Base class for a version.

    Attributes:
        spec (str): version spec
        id (str): unique iter8id of this version. contained in spec.
        is_baseline (bool): boolean indicating if this is the baseline version
        experiment (Experiment): parent experiment object to which this detailed version belongs
        pseudo_reward (float): value used to evaluate version in place of reward, if there is no reward metric in the list of criteria
    """
    def __init__(self, spec, is_baseline, experiment, pseudo_reward):
        """Initialize detailed version object.

        Args:
            spec (str): version spec
            id (str): unique iter8id of this version. contained in spec.
            version_labels (dict): version labels dict from spec
            is_baseline (bool): boolean indicating if this is the baseline version
            experiment (Experiment): parent experiment object to which this detailed version belongs
        """
        self.spec = spec # there's some duplication here. Ok for now.
        self.id = spec.id
        self.version_labels = spec.version_labels
        self.is_baseline = is_baseline
        self.experiment = experiment # link back to parent experiment
        self.pseudo_reward = pseudo_reward

        self.metrics = {
            "counter_metrics": {
                cms.id: DetailedCounterMetric(cms, self) for cms in self.experiment.counter_metric_specs.values()
            },
            "ratio_metrics": {
                rms.id: DetailedRatioMetric(rms, self) for rms in self.experiment.ratio_metric_specs.values()
                }
        }

        # populated aggregated counter and ratio metrics from last state
        if experiment.eip.last_state:
            if experiment.eip.last_state.aggregated_counter_metrics:
                if self.id in experiment.eip.last_state.aggregated_counter_metrics:
                    for metric_id in experiment.eip.last_state.aggregated_counter_metrics[self.id]:
                        self.metrics["counter_metrics"][metric_id].set_aggregated_metric(experiment.eip.last_state.aggregated_counter_metrics[self.id][metric_id])

            if experiment.eip.last_state.aggregated_ratio_metrics:
                if self.id in experiment.eip.last_state.aggregated_ratio_metrics:
                    for metric_id in experiment.eip.last_state.aggregated_ratio_metrics[self.id]:
                        self.metrics["ratio_metrics"][metric_id].set_aggregated_metric(experiment.eip.last_state.aggregated_ratio_metrics[self.id][metric_id])

        self.threshold_breached = {
            criterion.id: None for criterion in self.experiment.eip.criteria if criterion.threshold
        }
        self.probability_of_satisfying_threshold = {
            criterion.id: None for criterion in self.experiment.eip.criteria if criterion.threshold
        }

    def aggregate_counter_metrics(self, new_counter_metrics: Dict[iter8id, CounterDataPoint]):
        """combine aggregated counter metrics from last state for this version with new counter metrics. Aggregated results stored in self.aggregated_counter_metrics

        Args:
            new_counter_metrics (Dict[iter8id, CounterDataPoint]): dictionary mapping from metric id to CounterDataPoint
        """
        for metric_id in new_counter_metrics:
            if new_counter_metrics[metric_id].value is not None:
                self.metrics["counter_metrics"][metric_id].set_aggregated_metric(AggregatedCounterDataPoint(
                    ** new_counter_metrics[metric_id].dict()
                ))
        
    def aggregate_ratio_metrics(self, new_ratio_metrics: Dict[iter8id, RatioDataPoint]):
        """combine aggregated ratio metrics from last state for this version with new ratio metrics. Aggregated results stored in self.aggregated_ratio_metrics

        Args:
            new_ratio_metrics (Dict[iter8id, RatioDataPoint]): dictionary mapping from metric id to RatioDataPoint
        """
        for metric_id in new_ratio_metrics:
            if new_ratio_metrics[metric_id].value is not None:
                self.metrics["ratio_metrics"][metric_id].set_aggregated_metric(AggregatedRatioDataPoint(
                    ** new_ratio_metrics[metric_id].dict()
                ))
                
    def update_beliefs(self):
        """Update beliefs for ratio metrics. If belief update is not possible due to insufficient data, then the relevant status codes are populated here
        """
        for rm in self.metrics["ratio_metrics"].values():
            rm.update_belief()

    def create_posterior_samples(self):
        """Create posterior samples used for assessment and traffic routing
        """
        self.create_ratio_metric_samples()
        self.create_utility_samples()

    def create_ratio_metric_samples(self):
        """Create ratio metric samples used for assessment and traffic routing
        """
        for rm in self.metrics["ratio_metrics"].values():
            if rm.belief.status == StatusEnum.all_ok:
                rm.belief.sample_posterior()

    def get_reward_sample(self):
        self.reward_metric_id = None
        for criterion in self.experiment.eip.criteria:
            if criterion.is_reward:
                self.reward_metric_id = criterion.metric_id
                break

        if not self.reward_metric_id: # return pseudo-reward
            return np.full((Belief.sample_size, ), np.float(self.pseudo_reward))
        else: # try and return a real reward
            drm = self.metrics["ratio_metrics"][self.reward_metric_id]
            if drm.belief.status == StatusEnum.all_ok:
                return drm.belief.sample_posterior()
            else: 
                return np.full((Belief.sample_size, ), np.nan)

    def get_criterion_mask(self, criterion):
        return np.ones((Belief.sample_size, ))
        # raise NotImplementedError

    def create_utility_samples(self):
        """Create utility samples used for winner assessment and traffic routing. This could be an array of nans if data is not available for its computation.
        """
        if not self.metrics["counter_metrics"][ITER8_REQUEST_COUNT].aggregated_metric.value:
            logger.warning(f"No requests so far for version: {self.id}")
            self.utility_sample = np.full((Belief.sample_size, ), 1.0e10) # large number
        else:
            self.utility_sample = self.get_reward_sample()

        for criterion in self.experiment.eip.criteria:
            self.utility_sample *= self.get_criterion_mask(criterion)

        # bias term to ensure baseline is picked when all versions have zero utilities
        if self.is_baseline:
            self.utility_sample += 1.0e-10
            
    def get_utility(self):
        return self.utility_sample

    def create_threshold_assessment(self, criterion):
        """Create threshold assessment.

        Args:
            criterion (Criterion): A criterion object from the experiment with a threshold

        Returns:
            threshold (ThresholdAssessment): A threshold assessment object or none if metric values are unavailable to create the assessment
        """         

        return None # short circuiting for now... 
        
        def get_probability_of_satisfying_threshold(belief, criterion):
            return 1.0

        if criterion.threshold is None:
            return None

        mid = criterion.metric_id
        data_point = self.metrics["counter_metrics"][mid].aggregated_metric if mid in self.metrics["counter_metrics"] else self.metrics["ratio_metrics"][mid].aggregated_metric
        if data_point.value is None:
            return None

        return ThresholdAssessment(
            threshold_breached = self.threshold_breached[criterion.id],
            probability_of_satisfying_threshold = self.probability_of_satisfying_threshold[criterion.id]
        )

    def create_assessment(self):
        """Create assessment for this version. Results are stored in self.criterion_assessments
        """
        self.criterion_assessments = []
        for criterion in self.experiment.eip.criteria:
            if criterion.metric_id in self.metrics["counter_metrics"]:
                self.criterion_assessments.append(CriterionAssessment(
                    id = criterion.id,
                    metric_id = criterion.metric_id,
                    statistics = Statistics(
                        value = self.metrics["counter_metrics"][criterion.metric_id].aggregated_metric.value
                    ),
                    threshold_assessment = self.create_threshold_assessment(criterion)
                ))
            else: # criterion.metric_id in self.metrics["ratio_metrics"]
                self.criterion_assessments.append(CriterionAssessment(
                    id = criterion.id,
                    metric_id = criterion.metric_id,
                    statistics = Statistics(
                        value = self.metrics["ratio_metrics"][criterion.metric_id].aggregated_metric.value
                    ),
                    threshold_assessment = self.create_threshold_assessment(criterion)
                ))

    def check_breach(self, data_point, limit, preferred_direction):
        """Check if metric value has breached a limit.

            Args:
                data_point (DataPoint): aggregated counter or ratio data point
                limit (float): limit to be checked
                preferred_direction (DirectionEnum): preferred direction for the metric

            Returns:
                status (bool): True if the data point has breached threshold. False otherwise.
        """
        if preferred_direction == DirectionEnum.lower:
            return data_point.value > limit
        elif preferred_direction == DirectionEnum.higher:
            return data_point.value < limit

    def check_threshold_breaches(self):
        """Check and record if thresholds have been breached in criteria
        """
        raise NotImplementedError()

    def compute_probabilities_of_breaching_thresholds(self):
        """Compute and record probabilities of thresholds being breached in criteria
        """
        raise NotImplementedError()

    def get_threshold_details(self, criterion, detailed_baseline_version):
        """Compute and record probabilities of thresholds being breached in criteria
        """
        if criterion.metric_id in self.aggregated_counter_metrics:
            data_point = self.aggregated_counter_metrics[criterion.metric_id]
            preferred_direction = self.experiment.counter_metric_specs[criterion.metric_id].preferred_direction
            baseline_data_point = detailed_baseline_version.aggregated_counter_metrics[criterion.metric_id]

        if criterion.threshold.threshold_type == ThresholdEnum.absolute:
            limit = criterion.threshold.value
        else:
            limit = criterion.threshold.value * baseline_data_point.value

        return {
            data_point: data_point,
            limit: limit,
            preferred_direction: preferred_direction
        }

class DetailedBaselineVersion(DetailedVersion):
    def __init__(self, spec, experiment):
        super().__init__(spec, True, experiment, 1.0) # baseline always has pseudo_reward = 1.0

    def check_threshold_breaches(self):
        """Check if thresholds have been breached in criteria
        """
        self.threshold_breached = {
            criterion.id: self.check_breach(** self.get_threshold_details(criterion, self)) for criterion in self.experiment.eip.criteria if criterion.threshold
        }

class DetailedCandidateVersion(DetailedVersion):
    def __init__(self, spec, experiment, pseudo_reward):
        super().__init__(spec, False, experiment, pseudo_reward)

    def check_threshold_breaches(self):
        """Check if thresholds have been breached in criteria
        """
        self.threshold_breached = {
            criterion.id: self.check_breach(** self.get_threshold_details(criterion, self)) for criterion in self.experiment.eip.criteria if criterion.threshold
        }

    def check_threshold_breaches(self):
        """Check if thresholds have been breached in criteria
        """
        self.threshold_breached = {
            criterion.id: self.check_breach(** self.get_threshold_details(criterion, self.detailed_baseline_versions)) for criterion in self.experiment.eip.criteria if criterion.threshold
        }