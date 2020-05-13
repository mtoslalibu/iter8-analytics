"""Core module for querying prometheus and returning metric data.

Todo:
    * Create unit tests for these functions
    * Docstrings
"""
from datetime import datetime, timedelta, timezone
from typing import Dict, Iterable, Any
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

# For logging
logger = logging.getLogger(__name__)

class DataPoint(BaseModel):
    """A single data point for a given metric and given version.
    """
    value: float = Field(None, description = "Value of the metric")
    timestamp: datetime = Field(None, description = "Time at which this metric was last queried and updated")
    status: StatusEnum = Field(StatusEnum.all_ok, description = "Status of this data point derived from prometheus response")

class CounterDataPoint(DataPoint):
    """A single counter data point for a given counter metric and given version.
    """

class RatioDataPoint(DataPoint):
    """A single ratio data point for a given ratio metric and given version.
    """

class AggregatedCounterDataPoint(CounterDataPoint):
    """A single aggregated counter data point for a given metric and given version.
    """

class AggregatedRatioDataPoint(RatioDataPoint):
    """A single aggregated ratio data point for a given metric and given version.
    """

class RatioMaxMin(BaseModel):
    maximum: float = Field(None,  description = "maximum observed value of a ratio metric")
    minimum: float = Field(None,  description = "minimum observed value of a ratio metric")

class QuerySpec(BaseModel):
    """Base class for prometheus query spec
    """
    version_label_keys: Iterable[str] # prometheus label names (for grouping)
    start_time: datetime # start time for computing duration in the query

class CounterQuerySpec(QuerySpec):
    """Base class for prometheus counter query spec
    """
    query_template: Any

    class Config:
        arbitrary_types_allowed = True

class RatioQuerySpec(QuerySpec):
    """Base class for prometheus ratio query spec
    """
    numerator_template: Any
    denominator_template: Any

    class Config:
        arbitrary_types_allowed = True

def get_counter_metrics(
    counter_metric_specs: Dict[iter8id, CounterMetricSpec], 
    versions: Iterable[Version], 
    start_time) -> Dict[iter8id,  Dict[iter8id, CounterDataPoint]]:
    """Query prometheus and get counter metric data for given set of counter metrics and versions.

    Args:
        counter_metric_specs (Dict[iter8id, CounterMetricSpec]): dictionary whose values are the counter metric specs and whose keys are counter metric ids.
        versions (Iterable[Version]): A iterable of version objects.
        start_time (datetime): start time which dictates the duration parameter used in the query.

    Returns:
        Dict[iter8id,  Dict[iter8id, CounterDataPoint]]: dictionary whose keys are version ids and whose values are dictionaries. The inner dictionary has keys which are metric ids and values which are current counter data point values. For e.g.:
        {
            "version1": {
                "metric1": CounterDataPoint(...),
                "metric2": CounterDataPoint(...)
            }, 
            "version2": {
                "metric1": CounterDataPoint(...),
                "metric2": CounterDataPoint(...)
            }
        }      
    """
    cmd = {version.id: {} for version in versions} #  initialize cmd
    # populate cmd
    for counter_metric_spec in counter_metric_specs.values():
        query_spec = CounterQuerySpec(
            version_label_keys = versions[0].version_labels.keys(),
            query_template = counter_metric_spec.query_template,
            start_time = start_time
        )
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

def get_ratio_metrics(
    ratio_metric_specs: Dict[iter8id, RatioMetricSpec], 
    counter_metric_specs: Dict[iter8id, CounterMetricSpec], 
    counter_metrics: Dict[iter8id,  Dict[iter8id, CounterDataPoint]], 
    versions: Iterable[Version],
    start_time: datetime) -> Dict[iter8id,  Dict[iter8id, RatioDataPoint]]:
    """Query prometheus and get ratio metric data for given set of ratio metrics and versions.

    Args:
        ratio_metric_specs (Dict[iter8id, RatioMetricSpec]): dictionary whose values are the ratio metric specs and whose keys are ratio metric ids
        counter_metric_specs (Dict[iter8id, CounterMetricSpec]): dictionary whose values are the counter metric specs and whose keys are counter metric ids.
        counter_metrics (Dict[iter8id,  Dict[iter8id, CounterDataPoint]]): dictionary whose keys are version ids and whose values are dictionaries. The inner dictionary has keys which are  metric ids and values which are current counter data point values. Typically, the object returned by get_counter_metrics(...) method will be used as the value of this argument.
        versions (Iterable[Version]): A iterable of version objects.
        start_time (datetime): start time which dictates the duration parameter used in the query.

    Returns:
        Dict[iter8id,  Dict[iter8id, RatioDataPoint]]: dictionary whose keys are version ids and whose values are dictionaries. The inner dictionary has keys which are metric ids and values which are current ratio data point values. For e.g.:
        {
            "version1": {
                "metric1": RatioDataPoint(...),
                "metric2": RatioDataPoint(...)
            }, 
            "version2": {
                "metric1": RatioDataPoint(...),
                "metric2": RatioDataPoint(...)
            }
        }      
    """

    rmd = {version.id: {} for version in versions} #  initialize rmd

    # populate rmd
    for ratio_metric_spec in ratio_metric_specs.values():
        query_spec = RatioQuerySpec(
            version_label_keys = versions[0].version_labels.keys(),
            numerator_template = counter_metric_specs[ratio_metric_spec.numerator].query_template,
            denominator_template = counter_metric_specs[ratio_metric_spec.denominator].query_template,
            start_time = start_time
        )
        prmq = PrometheusRatioMetricQuery(query_spec, versions)
        current_time = datetime.now(timezone.utc)
        rmd_from_prom = prmq.query_from_spec(current_time)

        for version in versions:
            if version.id in rmd_from_prom:
                rmd[version.id][ratio_metric_spec.id] = rmd_from_prom[version.id]
            else:
                if version.id in counter_metrics and counter_metrics[version.id][ratio_metric_spec.denominator]:
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
    """Base class for querying prometheus.

    Attributes:
        prometheus_url (str): Prom url for quering
        query_spec (QuerySpec): Query spec for prom query
        version_labels_to_id (Dict[Set<Tuple<str, str>>, str]): Dictionary mapping version labels to their ids
    """
    def __init__(self, query_spec, versions):
        """Initialize prometheus metric query object.

        Args:
            query_spec (QuerySpec): Prom query spec
            versions (Iterable<Version>): Iterable of version objects.
        """
        prometheus_url = os.getenv(constants.ITER8_ANALYTICS_METRICS_BACKEND_URL_ENV)
        self.prometheus_url = prometheus_url + "/api/v1/query"
        self.query_spec = query_spec
        self.version_labels_to_id = {
            frozenset(version.version_labels.items()): version.id for version in versions
        }

    def query_from_spec(self, current_time):
        """Query prometheus using query spec.

        Args:
            current_time (datetime): Current time needed to compute duration value within the query.

        Returns:
            query_result (Dict[str, Dict[str, DataPoint]]]): Post processed query result
        """
        interval = int((current_time - self.query_spec.start_time).total_seconds())
        kwargs = {
            "interval": f"{interval}s",
            "version_labels": ",".join(self.query_spec.version_label_keys) # also hard coded
        }
        query = self.get_query(kwargs)
        return self.query(query, current_time)

    def query(self, query, current_time):
        """Query prometheus using query parameters.

        Args:
            current_time (datetime): Current time needed to compute duration value within the query.

        Returns:
            query_result (Dict[str, Dict[str, DataPoint]]]): Post processed query result

        Raises:
            Exception: HTTP connection errors related to prom requests.
        """
        params = {'query': query}
        try:
            query_result = requests.get(self.prometheus_url, params=params).json()
            logger.debug("query result -- raw")
            logger.debug(query_result)
        except Exception as e:
            logger.error("Error while attempting to connect to prometheus")
            raise(e)
        return self.post_process(query_result, current_time)

    def post_process(self, raw_query_result,  ts):
        """Post process prom query result

        Args:
            raw_query_result ({
                "data": {
                    "result": {
                        "value": [float], # sequence whose element index 1 is the metric value
                        "metric": Dict[str, str] # version labels
                    }
                }
            }): Raw prometheus result
            ts (datetime): time stamp at which prom query was made

        Returns:
            query_result (Dict[str, Dict[str, DataPoint]]]): Post processed query result
        
        Raises:
            ValueError: If query was unsuccessful for reasons such as bad template, prom result contained no data or returned data in a non-vector form which cannot be post processed.
        """
        prom_result = {}
        if raw_query_result["status"] != "success":
            raise ValueError("Query did not succeed. Check your query template.")
        elif "data" not in raw_query_result:
            return ValueError("Query did not succeed. Prometheus returned without data.")
        elif raw_query_result["data"]['resultType'] != 'vector':
            return ValueError("Query succeeded but returned a non-vector result")
        else:
            results = raw_query_result["data"]["result"]
            for result in results:
                version_id = self.get_version_id(result['metric'])
                if version_id:
                    prom_result[version_id] = self.result_value_to_data_point(result['value'][1])

        return prom_result

    def get_version_id(self, version_labels):
        """Get version id from version label.

        Args:
            version_labels (Dict[str, str]): Dictionary of labels and their values for a version

        Returns:
            version_id (str): id of the corresponding version      
        """
        return self.version_labels_to_id.get(frozenset(version_labels.items()), None)


class PrometheusCounterMetricQuery(PrometheusMetricQuery):
    """Derived class for querying prometheus for counter metric.
    """
    def get_query(self, query_args):
        """Extrapolate query from counter query spec and query_args

        Args:
            query_args (Dict[str, str]): Dictionary of values of template variables in counter query spec

        Returns:
            query (str): The query string used for querying prom
        """

        query_template = Template(self.query_spec.query_template)
        query = query_template.substitute(**query_args)
        logger.debug(f"Query: {query}")
        return query

    def result_value_to_data_point(self, result_value: str, ts: datetime) -> CounterDataPoint:
        """Convert prometheus result value in string format to CounterDataPoint

        Args:
            result_value (str): Raw prometheus result value
            ts (datetime): time stamp at which prom query was made

        Returns:
            counter_data_point (CounterDataPoint): Counter data point
        """

        result_float = float(result_value)
        assert(not math.isnan(result_float))
        return CounterDataPoint(
            value = result_float,
            timestamp = ts)

class PrometheusRatioMetricQuery(PrometheusMetricQuery):
    """Derived class for querying prometheus for counter metric.
    """
    def get_query(self, query_args):
        """Extrapolate query from ratio query spec and query_args

        Args:
            query_args (Dict[str, str]): Dictionary of values of template variables in query_spec

        Returns:
            query (str): The query string used for querying prom
        """
        num_query_template = Template(self.query_spec.numerator_template)
        num_query = num_query_template.substitute(**query_args)
        den_query_template = Template(self.query_spec.denominator_template)
        den_query = den_query_template.substitute(**query_args)
        query = f"({num_query}) / ({den_query})"
        logger.debug(f"Query: {query}")
        return query

    def result_value_to_data_point(self, result_value: str, ts: datetime) -> RatioDataPoint:
        """Convert prometheus result value in string format to RatioDataPoint

        Args:
            result_value (str): Raw prometheus result value
            ts (datetime): time stamp at which prom query was made

        Returns:
            ratio_data_point (RatioDataPoint): Ratio data point
        """

        result_float = float(result_value)
        return RatioDataPoint(
            value = None,
            timestamp = ts,
            status = StatusEnum.nan_value
        ) if math.isnan(result_float) else RatioDataPoint(
            value = result_float,
            timestamp = ts
        )