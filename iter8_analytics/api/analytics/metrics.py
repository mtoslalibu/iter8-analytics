"""
Data structures and functions for manipulating metrics
"""
from datetime import datetime, timedelta
from typing import Dict, Sequence, Union
from uuid import UUID

from iter8_analytics.api.analytics.experiment_iteration_request import CounterMetricSpec

# Module dependencies
from pydantic import BaseModel, Field

class CounterDataPoint(BaseModel):
    value: float = Field(None, description = "Value of the counter metric")
    timestamp: datetime = Field(None, description = "Time at which this counter metric was last queries and updated")

class AggregatedCounterDataPoint(BaseModel):
    value: float = Field(None, description = "Value of the counter metric")
    timestamp: datetime = Field(None, description = "Time at which this counter metric was last queries and updated")
    delta_value: float = Field(None, description = "Diff between current value and previous value")
    delta_timestamp: timedelta = Field(None, description = "Diff between current timestamp and previous time stamp")

class AggregatedRatioDataPoint(BaseModel):
    value: float = Field(None, description = "Value of the ratio metric")
    timestamp: datetime = Field(None, description = "Time at which this counter metric was last queries and updated")
    minimum: float = Field(None, description = "Known minimum value of the ratio metric")
    maximum: float = Field(None, description = "Known maximum value of the ratio metric")

# valid for live experiments...  notice absence of end_time
def get_counter_metric_data(counter_metric_specs: Dict[Union[int, str, UUID], CounterMetricSpec], version_ids: Sequence[Union[int, str, UUID]], start_time):
    cmd = {} #  initialize cmd
    for version_id in version_ids:
        cmd[version_id] = {}
    # populate cmd
    for metric_id in counter_metric_specs:
        # populate the cmd_from_prom through prometheus queries
        cmd_from_prom = {}
        for version_id in version_ids:
            if version_id in cmd_from_prom:
                cmd[version_id][metric_id] = cmd_from_prom[version_id]
            else:
                cmd[version_id][metric_id] = CounterDataPoint()
    return cmd

# class Iter8MetricFactory:
#     def __init__(self, metrics_backend_url):
#         self.metrics_backend_url = metrics_backend_url

#     def get_iter8_counter_metric(self, counter_metric_spec):
#         return Iter8CounterMetric(counter_metric_spec, self.metrics_backend_url)

#     @staticmethod
#     def create_metric_spec(criterion, entity_tag):
#         metric_spec = {}
#         metric_spec["name"] = criterion.metric_name
#         metric_spec[request_parameters.IS_COUNTER_STR] = criterion.is_counter
#         metric_spec[request_parameters.ABSENT_VALUE_STR] = criterion.absent_value
#         metric_spec["query_specs"] = [{"query_name": "value", "query_template": criterion.metric_query_template, request_parameters.IS_COUNTER_STR: criterion.is_counter, request_parameters.ABSENT_VALUE_STR: criterion.absent_value, "entity_tags": entity_tag},
#         {"query_name": "sample_size", "query_template": criterion.metric_sample_size_query_template, request_parameters.IS_COUNTER_STR: True, request_parameters.ABSENT_VALUE_STR: "0", "entity_tags": entity_tag}]
#         return metric_spec

#     @staticmethod
#     def get_interval(start_time, end_time):
#         start = parser.parse(start_time)
#         end = parser.parse(end_time)
#         now = datetime.now(timezone.utc)
#         offset_str = ""
#         if start <= end:
#             interval = max(end - start, timedelta(seconds = 1))
#             interval_str = str(int(interval.total_seconds())) + "s"
#             if end < now:
#                 offset = now-end
#                 if offset.total_seconds() >= 1.0:
#                     offset_str = str(int(offset.total_seconds())) + "s"
#         else:
#             raise ValueError("Start time cannot exceed end time")
#         return interval_str,offset_str

# class Iter8Metric:
#     def __init__(self, metric_spec, metrics_backend_url):
#         self.name = metric_spec["name"]
#         self.is_counter = metric_spec[request_parameters.IS_COUNTER_STR]
#         self.absent_value = metric_spec[request_parameters.ABSENT_VALUE_STR]
#         self.query_specs = metric_spec["query_specs"]
#         self.metrics_backend_url = metrics_backend_url
#         self.prom_queries = [PrometheusQuery(self.metrics_backend_url, query_spec) for query_spec in self.query_specs]

#     def get_stats(self, interval_str, offset_str):
#         results = {responses.STATISTICS_STR: {}, "messages": []}
#         for query in self.prom_queries:
#             prom_result = query.query_from_template(interval_str, offset_str)
#             results[responses.STATISTICS_STR][query.query_spec["query_name"]] = prom_result["value"]
#             results["messages"].append(str(query.query_spec["query_name"]+": "+ prom_result["message"]))

#         log.debug(results)
#         """
#         Format of results:
#         results = {'statistics': {'sample_size': '12', 'value': 13}, 'messages': ["sample_size: Query success, result found", "value: Query success, result found"]}
#         """
#         return results
