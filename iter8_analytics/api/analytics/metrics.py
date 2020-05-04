"""
Data structures and functions for manipulating metrics
"""
from datetime import datetime, timedelta, timezone
from typing import Dict, Sequence
import os
import logging
import requests
from string import Template
import math

from iter8_analytics.api.analytics.experiment_iteration_request import CounterMetricSpec, RatioMetricSpec, iter8id, Version
from iter8_analytics.api.analytics.experiment_iteration_response import StatusEnum
import iter8_analytics.constants as constants

# Module dependencies
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

class CounterDataPoint(BaseModel):
    value: float = Field(None, description = "Value of the counter metric")
    timestamp: datetime = Field(None, description = "Time at which this counter metric was last queries and updated")
    status: StatusEnum = Field(StatusEnum.all_ok, description = "Status of the prometheus response")

class RatioDataPoint(BaseModel):
    value: float = Field(None, description = "Value of the ratio metric")
    timestamp: datetime = Field(None, description = "Time at which this ratio metric was last queries and updated")
    status: StatusEnum = Field(StatusEnum.all_ok, description = "Status of the prometheus response")

class AggregatedCounterDataPoint(BaseModel):
    value: float = Field(None, description = "Value of the counter metric")
    timestamp: datetime = Field(None, description = "Time at which this counter metric was last queries and updated")
    delta_value: float = Field(None, description = "Diff between current value and previous value")
    delta_timestamp: timedelta = Field(None, description = "Diff between current timestamp and previous time stamp")
    status: StatusEnum = Field(StatusEnum.all_ok, description = "Status of the prometheus response")

class AggregatedRatioDataPoint(BaseModel):
    value: float = Field(None, description = "Value of the ratio metric")
    timestamp: datetime = Field(None, description = "Time at which this counter metric was last queries and updated")
    minimum: float = Field(None, description = "Known minimum value of the ratio metric")
    maximum: float = Field(None, description = "Known maximum value of the ratio metric")
    status: StatusEnum = Field(StatusEnum.all_ok, description = "Status of the prometheus response")

# valid for live experiments...  notice absence of end_time
def get_counter_metric_data(
    counter_metric_specs: Dict[iter8id, CounterMetricSpec], 
    versions: Sequence[Version], 
    start_time) -> Dict[iter8id,  Dict[iter8id, CounterDataPoint]]:
    cmd = {version.id: {} for version in versions} #  initialize cmd
    # populate cmd
    for counter_metric_spec in counter_metric_specs.values():
        query_spec = {
            "version_label_keys": versions[0].version_labels.keys(),
            "query_template": counter_metric_spec.query_template,
            "start_time": start_time
        }
        pcmq = PrometheusCounterMetricQuery(query_spec, versions)
        current_time = datetime.now(timezone.utc)
        cmd_from_prom = pcmq.query_from_spec(current_time)
        status = StatusEnum.zeroed_counter if cmd_from_prom else StatusEnum.no_versions_in_prom_response
        for version in versions:
            if version.id in cmd_from_prom:
                cmd[version.id][counter_metric_spec.id] = cmd_from_prom[version.id]
            else:
                cmd[version.id][counter_metric_spec.id] = CounterDataPoint(
                    value = 0,
                    timestamp = current_time,
                    status = status
                )
    return cmd

def get_ratio_metric_data(
    ratio_metric_specs: Dict[iter8id, RatioMetricSpec], 
    counter_metric_specs: Dict[iter8id, CounterMetricSpec], 
    counter_metric_data: Dict[iter8id,  Dict[iter8id, CounterDataPoint]], 
    versions: Sequence[Version],
    start_time: datetime) -> Dict[iter8id,  Dict[iter8id, RatioDataPoint]]:

    rmd = {version.id: {} for version in versions} #  initialize rmd

    # populate rmd
    for ratio_metric_spec in ratio_metric_specs.values():
        query_spec = {
            "version_label_keys": versions[0].version_labels.keys(),
            "numerator_template": counter_metric_specs[ratio_metric_spec.numerator].query_template,
            "denominator_template": counter_metric_specs[ratio_metric_spec.denominator].query_template,
            "start_time": start_time
        }
        prmq = PrometheusRatioMetricQuery(query_spec, versions)
        current_time = datetime.now(timezone.utc)
        rmd_from_prom = prmq.query_from_spec(current_time)

        for version in versions:
            if version.id in rmd_from_prom:
                rmd[version.id][ratio_metric_spec.id] = rmd_from_prom[version.id]
            else:
                if version.id in counter_metric_data and counter_metric_data[version.id][ratio_metric_spec.denominator]:
                    rmd[version.id][ratio_metric_spec.id] = RatioDataPoint(
                        value = 0,
                        timestamp = current_time,
                        status = StatusEnum.zeroed_ratio
                    )
                else:
                    rmd[version.id][ratio_metric_spec.id] = RatioDataPoint(
                        value = None,
                        timestamp = current_time,
                        status = StatusEnum.absent_version_in_prom_response
                    )
    return rmd

class PrometheusMetricQuery():
    def __init__(self, query_spec, versions):
        prometheus_url = os.getenv(constants.ITER8_ANALYTICS_METRICS_BACKEND_URL_ENV)
        self.prometheus_url = prometheus_url + "/api/v1/query"
        self.query_spec = query_spec
        self.version_labels_to_id = {
            frozenset(version.version_labels.items()): version.id for version in versions
        }

    def query_from_spec(self, current_time):
        interval = int((current_time - self.query_spec['start_time']).total_seconds())
        kwargs = {
            "interval": f"{interval}s",
            "version_labels": ",".join(self.query_spec["version_label_keys"]) # also hard coded
        }
        query = self.get_query(kwargs)
        return self.query(query, current_time)

    def query(self, query, current_time):
        params = {'query': query}
        try:
            query_result = requests.get(self.prometheus_url, params=params).json()
            logger.debug("query result -- raw")
            logger.debug(query_result)
        except Exception as e:
            logger.error("Error while attempting to connect to prometheus")
            raise(e)
        return self.post_process(query_result, current_time)

    def get_version_id(self, version_labels):
        return self.version_labels_to_id.get(frozenset(version_labels.items()), None)


class PrometheusCounterMetricQuery(PrometheusMetricQuery):
    def get_query(self, query_args):
        query_template = Template(self.query_spec["query_template"])
        query = query_template.substitute(**query_args)
        logger.debug(f"Query: {query}")
        return query

    def post_process(self, query_result,  ts):
        prom_result = {}
        if query_result["status"] != "success":
            prom_result["message"] = "Query did not succeed. Check your query template."
            raise ValueError("Query did not succeed. Check your query template.")
        elif "data" not in query_result:
            return ValueError("Query did not succeed. Prometheus returned without data.")
        elif query_result["data"]['resultType'] != 'vector':
            return ValueError("Query succeeded but returned a non-vector result")
        else:
            results = query_result["data"]["result"]
            for result in results:
                result_float = float(result["value"][1])
                assert(not math.isnan(result_float))
                version_id = self.get_version_id(result['metric'])
                if version_id:
                    prom_result[version_id] = CounterDataPoint(
                        value = result_float,
                        timestamp = ts
                    )
        return prom_result

class PrometheusRatioMetricQuery(PrometheusMetricQuery):
    def get_query(self, query_args):
        num_query_template = Template(self.query_spec["numerator_template"])
        num_query = num_query_template.substitute(**query_args)
        den_query_template = Template(self.query_spec["denominator_template"])
        den_query = den_query_template.substitute(**query_args)
        query = f"({num_query}) / ({den_query})"
        logger.debug(f"Query: {query}")
        return query

    def post_process(self, query_result, ts):
        prom_result = {}
        if query_result["status"] != "success":
            prom_result["message"] = "Query did not succeed. Check your query template."
            raise ValueError("Query did not succeed. Check your query template.")
        elif "data" not in query_result:
            return ValueError("Query did not succeed. Prometheus returned without data.")
        elif query_result["data"]['resultType'] != 'vector':
            return ValueError("Query succeeded but returned a non-vector result")
        else:
            results = query_result["data"]["result"]
            for result in results:
                result_float = float(result["value"][1])
                logger.debug(f"result_float: {result_float}")
                version_id = self.get_version_id(result['metric'])
                if version_id:
                    if math.isnan(result_float):
                        prom_result[version_id] = RatioDataPoint(
                            value = None,
                            timestamp = ts,
                            status = StatusEnum.nan_value
                        )
                    else:
                        prom_result[version_id] = RatioDataPoint(
                            value = result_float,
                            timestamp = ts
                        )
        return prom_result