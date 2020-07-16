"""
Module containing detailed metric classes with related update methods
"""
# core python dependencies
import logging

# external module dependencies
import numpy as np

# iter8 dependencies
from iter8_analytics.api.analytics.types import *

class Belief():
    """Base class for belief probability distributions.
    """
    sample_size = 10000 # hardcoded for now. super ugly!

    def __init__(self, status: StatusEnum):
        self.status = status
        self.sample = None

    def sample_posterior(self):
        if self.sample is None:
            self.compute_sample()
        return self.sample

class GaussianBelief(Belief):
    def __init__(self, mean: float, variance: float):
        super().__init__(StatusEnum.all_ok)
        self.mean = mean
        self.variance = variance
        self.stddev = np.sqrt(variance)

    def compute_sample(self):
        self.sample = np.random.normal(loc = self.mean, scale = self.stddev, size = self.sample_size)

class ConstantBelief(Belief):
    def __init__(self, value):
        super().__init__(StatusEnum.all_ok)
        self.value = value

    def compute_sample(self):
        self.sample = np.full((self.sample_size, ), np.float(self.value))

class DetailedMetric():
    """Base class for a detailed metric.

    Attributes:
        metric_spec (MetricSpec): metric spec
        detailed_version (DetailedVersion): detailed version to which this detailed metric belongs
        aggregated_metric (DataPoint): Aggregated counter or ratio data point
    """
    def __init__(self, metric_spec, detailed_version):
        """Initialize detailed version object.

        Args:
            metric_spec (MetricSpec): metric spec
            detailed_version (DetailedVersion): detailed version to which this detailed metric belongs
        """
        self.metric_spec = metric_spec # there's some duplication here. Ok for now.
        self.metric_id = self.metric_spec.id
        self.detailed_version = detailed_version
        self.version_id = self.detailed_version.id
        """linked back to parent detailed version to which this metric spec belongs
        """

    def set_aggregated_metric(self, aggregated_metric):
        """Set aggregated metric data point.

        Args:
            aggregated_metric (DataPoint): aggregated counter or ratio data point
        """
        self.aggregated_metric = aggregated_metric

class DetailedCounterMetric(DetailedMetric):
    def __init__(self, metric_spec, detailed_version):
        super().__init__(metric_spec, detailed_version)
        self.aggregated_metric = AggregatedCounterDataPoint(status = StatusEnum.uninitialized_value)

class DetailedRatioMetric(DetailedMetric):
    def __init__(self, metric_spec, detailed_version):
        super().__init__(metric_spec, detailed_version)
        self.belief = Belief(status = StatusEnum.uninitialized_belief)
        self.aggregated_metric = AggregatedRatioDataPoint(status = StatusEnum.uninitialized_value)

    def update_belief(self):
        ratio_max_mins = self.detailed_version.experiment.ratio_max_mins

        if self.aggregated_metric.value:
            denominator_id = self.metric_spec.denominator
            denominator_value = self.detailed_version.metrics["counter_metrics"][denominator_id].aggregated_metric.value
            if denominator_value is not None:
                if denominator_value > 0:
                    mm = ratio_max_mins[self.metric_id]
                    if mm.maximum is not None and mm.minimum is not None:
                        width = mm.maximum - mm.minimum
                        if width > 0:
                            self.belief = GaussianBelief(mean = self.aggregated_metric.value, variance=width / (1 + denominator_value))
                        else:
                            self.belief = ConstantBelief(value = mm.maximum)
