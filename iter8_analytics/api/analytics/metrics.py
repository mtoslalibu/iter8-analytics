"""
Data structures and functions for manipulating metrics
"""
from datetime import datetime, timedelta
from typing import Dict, Sequence, Union
from uuid import UUID
import os
import logging
import requests
from string import Template
import math

from iter8_analytics.api.analytics.experiment_iteration_request import CounterMetricSpec

import iter8_analytics.constants as constants

# Module dependencies
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

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
def get_counter_metric_data(counter_metric_specs: Dict[Union[int, str, UUID], CounterMetricSpec], version_ids: Sequence[Union[int, str, UUID]], start_time, version_labels):
    cmd = {} #  initialize cmd
    for version_id in version_ids:
        cmd[version_id] = {}
    # populate cmd
    for counter_metric_spec in counter_metric_specs.values():
        query_spec = {
            "version_labels": version_labels, 
            "query_template": counter_metric_spec.query_template
        }
        pcmq = PrometheusCounterMetricQuery(query_spec)
        cmd_from_prom = {}
        for version_id in version_ids:
            if version_id in cmd_from_prom:
                cmd[version_id][counter_metric_spec.id] = cmd_from_prom[version_id]
            else:
                cmd[version_id][counter_metric_spec.id] = CounterDataPoint()
    return cmd

class PrometheusCounterMetricQuery():
    def __init__(self, query_spec):
        prometheus_url = os.getenv(constants.ITER8_ANALYTICS_METRICS_BACKEND_URL_ENV)
        self.prometheus_url = prometheus_url + "/api/v1/query"
        self.query_spec = query_spec

    def query_from_spec(self):
        kwargs = {
            "interval": "5m", # hard coded for now...
            "version_labels": ",".join(self.query_spec["version_labels"]) # also hard coded
        }
        query_template = Template(self.query_spec["query_template"])
        query = query_template.substitute(**kwargs)
        return self.query(query)

    def query(self, query):
        params = {'query': query}
        logger.debug("Query params")
        logger.debug(params)
        try:
            query_result = requests.get(self.prometheus_url, params=params).json()
            logger.debug("Query results")
            logger.debug(query_result)
        except Exception as e:
            logger.error("Error while attempting to connect to prometheus")
            raise(e)
        return self.post_process(query_result)

    @classmethod
    def get_version_id(cls, version_dict):
        return version_dict['destination_workload'] # hardcoded for now

    def post_process(self, query_result):
        ts = datetime.now()
        prom_result = {}
        if query_result["status"] != "success":
            prom_result["message"] = "Query did not succeed. Check your query template."
            raise ValueError("Query did not succeed. Check your query template.")
        elif "data" not in query_result:
            return prom_result
        else:
            results = query_result["data"]["result"]
            if results == []:
                return prom_result
            else:
                logger.debug("detailed prom results")
                logger.debug(results)

                for result in results:
                    result_float = float(result["value"][1])
                    assert(not math.isnan(result_float))
                    prom_result[self.get_version_id(result['metric'])] = CounterDataPoint(
                        value = result_float,
                        timestamp = ts
                    )
        return prom_result