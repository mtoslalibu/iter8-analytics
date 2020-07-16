"""
Module containing detailed criterion classes
"""
# core python dependencies
import logging
# from typing import Dict

# external module dependencies
import numpy as np

# iter8 dependencies
from iter8_analytics.api.analytics.types import *
# from iter8_analytics.api.analytics.metrics import *
# from iter8_analytics.api.analytics.utils import *
from iter8_analytics.api.analytics.detailedmetric import *
# from iter8_analytics.api.analytics.detailedcriterion import *

class DetailedCriterion():
    """Base class for a detailed criterion.

    Attributes:
        spec (CriterionSpec): criterion spec
    """
    def __init__(self, criterion_spec, detailed_version):
        """Initialize detailed criterion object.

        Args:
            criterion_spec (CriterionSpec): criterion spec
            detailed_version (DetailedVersion): detailed version to which this detailed criterion belongs   
        """
        self.spec = criterion_spec
        self.detailed_version = detailed_version
        # some redundancy is ok
        self.id = self.spec.id
        self.metric_id = self.spec.metric_id 

    def create_assessment(self):
        if self.metric_id in self.detailed_version.metrics["counter_metrics"]:
            self.assessment = CriterionAssessment(
                id = self.id,
                metric_id = self.metric_id,
                statistics = self.create_statistics(),
                threshold_assessment = self.create_threshold_assessment()
            )
        else: # criterion.metric_id in self.metrics["ratio_metrics"]
            self.assessment = CriterionAssessment(
                id = self.id,
                metric_id = self.metric_id,
                statistics = self.create_statistics(),
                threshold_assessment = self.create_threshold_assessment()
            )

    def create_statistics(self):
        if self.metric_id in self.detailed_version.metrics["counter_metrics"]:
            return Statistics(value = self.detailed_version.metrics["counter_metrics"][self.metric_id].aggregated_metric.value)
        else:
            return Statistics(value = self.detailed_version.metrics["ratio_metrics"][self.metric_id].aggregated_metric.value, 
            ratio_statistics = self.get_ratio_statistics())

    def get_ratio_statistics(self):
        b = self.detailed_version.metrics["ratio_metrics"][self.metric_id].belief
        if b.status == StatusEnum.uninitialized_belief:
            return None
        # if samples for this metric are all nans, return None
        ms = b.sample_posterior()
        if np.any(np.isnan(ms)):
            return None
        # if samples for this metric are all constant, return None
        if np.min(ms) == np.max(ms):
            return None
        # compute credible interval based on sample
        gap = (1.0 - AdvancedParameters.posterior_probability_for_credible_intervals)*100.0
        cilp = gap / 2.0
        ciup = (gap/2.0) + AdvancedParameters.posterior_probability_for_credible_intervals*100.0
        ci = Interval(lower = np.percentile(ms, cilp), upper = np.percentile(ms, ciup))
        # else, get samples of this metric for baseline, and all other candidates
        # compute the relevant statistics and return ratio metrics
        # tbd
        return RatioStatistics(credible_interval = ci)

    def get_criterion_mask(self):
        return np.ones((Belief.sample_size, ))

    def create_threshold_assessment(self):
        pass

    def get_assessment(self):
        return self.assessment

    # def create_threshold_assessment(self, criterion):
    #     """Create threshold assessment.

    #     Args:
    #         criterion (Criterion): A criterion object from the experiment with a threshold

    #     Returns:
    #         threshold (ThresholdAssessment): A threshold assessment object or none if metric values are unavailable to create the assessment
    #     """         

    #     return None # short circuiting for now... 
        
    #     def get_probability_of_satisfying_threshold(belief, criterion):
    #         return 1.0

    #     if criterion.threshold is None:
    #         return None

    #     mid = criterion.metric_id
    #     data_point = self.metrics["counter_metrics"][mid].aggregated_metric if mid in self.metrics["counter_metrics"] else self.metrics["ratio_metrics"][mid].aggregated_metric
    #     if data_point.value is None:
    #         return None

    #     return ThresholdAssessment(
    #         threshold_breached = self.threshold_breached[criterion.id],
    #         probability_of_satisfying_threshold = self.probability_of_satisfying_threshold[criterion.id]
    #     )


    # def check_breach(self, data_point, limit, preferred_direction):
    #     """Check if metric value has breached a limit.

    #         Args:
    #             data_point (DataPoint): aggregated counter or ratio data point
    #             limit (float): limit to be checked
    #             preferred_direction (DirectionEnum): preferred direction for the metric

    #         Returns:
    #             status (bool): True if the data point has breached threshold. False otherwise.
    #     """
    #     if preferred_direction == DirectionEnum.lower:
    #         return data_point.value > limit
    #     elif preferred_direction == DirectionEnum.higher:
    #         return data_point.value < limit

    # def check_threshold_breaches(self):
    #     """Check and record if thresholds have been breached in criteria
    #     """
    #     raise NotImplementedError()

    # def compute_probabilities_of_breaching_thresholds(self):
    #     """Compute and record probabilities of thresholds being breached in criteria
    #     """
    #     raise NotImplementedError()



    # def get_threshold_details(self, criterion, detailed_baseline_version):
    #     """Compute and record probabilities of thresholds being breached in criteria
    #     """
    #     if criterion.metric_id in self.aggregated_counter_metrics:
    #         data_point = self.aggregated_counter_metrics[criterion.metric_id]
    #         preferred_direction = self.experiment.counter_metric_specs[criterion.metric_id].preferred_direction
    #         baseline_data_point = detailed_baseline_version.aggregated_counter_metrics[criterion.metric_id]

    #     if criterion.threshold.threshold_type == ThresholdEnum.absolute:
    #         limit = criterion.threshold.value
    #     else:
    #         limit = criterion.threshold.value * baseline_data_point.value

    #     return {
    #         data_point: data_point,
    #         limit: limit,
    #         preferred_direction: preferred_direction
    #     }
