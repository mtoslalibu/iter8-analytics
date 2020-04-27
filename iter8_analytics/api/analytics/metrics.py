"""
Data structures and functions for manipulating metrics
"""
from datetime import datetime
from typing import Dict, Sequence, Union
from uuid import UUID

from iter8_analytics.api.analytics.experiment_iteration_request import CounterMetricSpec

# Module dependencies
from pydantic import BaseModel, Field

class CounterDataPoint(BaseModel):
    value: float = 0.0 # value of the counter metric
    timestamp: datetime = datetime.now() # time at which this counter metric was last queries and updated

def get_counter_metric_data(counter_metric_specs: Sequence[CounterMetricSpec], version_ids: Sequence[Union[int, str, UUID]]):
    counter_metric_data = {}
    for cmsid in counter_metric_specs:
        # issue prometheus query
        # parse response into counter_metric_data
        # dummy data for now...
        counter_metric_data[cmsid] = {}
        for version_id in version_ids:
            counter_metric_data[cmsid][version_id] = 1.0
    return counter_metric_data

def aggregate_counter_metric_data(old_counter_metric_data, new_counter_metric_data):
    # aggregated_counter_metric_data = {}
    # dummy data for now
    return new_counter_metric_data
    # return aggregated_counter_metric_data