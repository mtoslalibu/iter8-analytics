from iter8_analytics.metrics_backend.prometheusquery import PrometheusQuery
import dateutil.parser as parser
from datetime import datetime, timezone, timedelta

class Iter8MetricFactory:
    def __init__(self, metrics_backend_url):
        self.metrics_backend_url = metrics_backend_url

    def get_iter8_metric(self, metric_spec):
        if metric_spec["type"] == "histogram":
            metrics_object = Iter8Histogram(metric_spec, self.metrics_backend_url)
        elif metric_spec["type"] == "gauge":
            metrics_object = Iter8Gauge(metric_spec, self.metrics_backend_url)
        elif metric_spec["type"] == "counter":
            metrics_object = Iter8Counter(metric_spec, self.metrics_backend_url)
        else:
            raise ValueError("Unknown type in metric_spec")
        return metrics_object

    @staticmethod
    def create_metric_spec(metrics_config, metric_name, entity_tag):
        metric_spec = {}
        metric_spec["name"] = metric_name
        metric_spec["type"] = metrics_config[metric_name]["type"]
        metric_spec["query_specs"] = []
        for query in metrics_config[metric_name]["query_templates"].keys():
            query_spec = {}
            query_spec["query_name"] = query
            query_spec["query_template"] = metrics_config[metric_name]["query_templates"][query]
            query_spec["zero_value_on_null"] = False
            if query_spec["query_name"] == "value" or query_spec["query_name"] == "sample_size":
                query_spec["zero_value_on_null"] = metrics_config[metric_name]["zero_value_on_null"]
            query_spec["entity_tags"] = entity_tag
            metric_spec["query_specs"].append(query_spec)
        return metric_spec

    @staticmethod
    def get_interval_and_offset_str(start_time, end_time):
        start = parser.parse(start_time)
        end = parser.parse(end_time)
        now = datetime.now(timezone.utc)
        if start <= end:
            interval = max(end - start, timedelta(seconds = 1))
            interval_str = str(int(interval.total_seconds())) + "s"
            if end < now:
                offset = now-end
                if offset.total_seconds() >= 1.0:
                    offset_str = str(int(offset.total_seconds())) + "s"
            else:
                offset_str = ""
        else:
            raise ValueError("Start time cannot exceed end time")
        return interval_str,offset_str

class Iter8Metric:
    def __init__(self, metric_spec, metrics_backend_url):
        self.name = metric_spec["name"]
        self.type = metric_spec["type"]
        self.query_specs = metric_spec["query_specs"]
        self.metrics_backend_url = metrics_backend_url
        self.prom_queries = [PrometheusQuery(self.metrics_backend_url, query_spec) for query_spec in self.query_specs]

    def get_stats(self, interval_str, offset_str):
        results = {}
        for query in self.prom_queries:
            results[query.query_spec["query_name"]] = query.query_from_template(interval_str, offset_str)
        return results


class Iter8Histogram(Iter8Metric): # custom
    def __init__(self, metric_spec, metrics_backend_url):
        """
        name = "iter8_latency",
        type = "histogram",
        query_specs = [{
            "query_name": "sample_size",
            "zero_value_on_null": true,
            "query_template": "sum(increase(istio_requests_total{reporter='source'}[$interval]$offset_str)) by ($entity_labels)",
            "entity_tags": {
                "destination_workload": "reviews-v2",
                "destination_service_namespace": "default"
            }
        }, {
            "query_name": "min",
            "zero_value_on_null": true,
            "query_template": "sum(increase(istio_request_duration_seconds_bucket{reporter="source", source_app="istio-ingressgateway"}[$interval]$offset_str)) by (le, $entity_labels)",
            "aggregation": "min",
            "entity_tags": {
                "destination_workload": "reviews-v2",
                "destination_service_namespace": "default"
            }
        }, {
            "query_name": "mean",
            "zero_value_on_null": true,
            "query_template": "(sum(increase(istio_request_duration_seconds_sum{source_app='istio-ingressgateway', reporter='source'}[$interval]$offset_str)) by ($entity_labels)) / (sum(increase(istio_request_duration_seconds_count{source_app='istio-ingressgateway', reporter='source'}[$interval]$offset_str)) by ($entity_labels))",
            "entity_tags": {
                "destination_workload": "reviews-v2",
                "destination_service_namespace": "default"
            }
        }, {
            "query_name": "max",
            "zero_value_on_null": true,
            "query_template": "sum(increase(istio_request_duration_seconds_bucket{reporter="source", source_app="istio-ingressgateway"}[$interval]$offset_str)) by (le, $entity_labels)",
            "aggregation": "max",
            "entity_tags": {
                "destination_workload": "reviews-v2",
                "destination_service_namespace": "default"
            }
        }, {
            "query_name": "stddev",
            "zero_value_on_null": true,
            "query_template": "sum(increase(istio_request_duration_seconds_bucket{reporter="source", source_app="istio-ingressgateway"}[$interval]$offset_str)) by (le, $entity_labels)",
            "aggregation": "stddev",
            "entity_tags": {
                "destination_workload": "reviews-v2",
                "destination_service_namespace": "default"
            }
        }, {
            "query_name": "first_quantile",
            "zero_value_on_null": true,
            "query_template": "histogram_quantile(0.25, sum(rate(istio_request_duration_seconds_bucket{reporter="source", source_app="istio-ingressgateway"}[$interval]$offset_str)) by (le, $entity_labels))",
            "entity_tags": {
                "destination_workload": "reviews-v2",
                "destination_service_namespace": "default"
            }
        }, {
            "query_name": "median",
            "zero_value_on_null": true,
            "query_template": "histogram_quantile(0.5, sum(rate(istio_request_duration_seconds_bucket{reporter="source", source_app="istio-ingressgateway"}[$interval]$offset_str)) by (le, $entity_labels))",
            "entity_tags": {
                "destination_workload": "reviews-v2",
                "destination_service_namespace": "default"
            }
        }, {
            "query_name": "third_quantile",
            "zero_value_on_null": true,
            "query_template": "histogram_quantile(0.75, sum(rate(istio_request_duration_seconds_bucket{reporter="source", source_app="istio-ingressgateway"}[$interval]$offset_str)) by (le, $entity_labels))",
            "entity_tags": {
                "destination_workload": "reviews-v2",
                "destination_service_namespace": "default"
            }
        }, {
            "query_name": "95th_percentile",
            "zero_value_on_null": true,
            "query_template": "histogram_quantile(0.95, sum(rate(istio_request_duration_seconds_bucket{reporter="source", source_app="istio-ingressgateway"}[$interval]$offset_str)) by (le, $entity_labels))",
            "entity_tags": {
                "destination_workload": "reviews-v2",
                "destination_service_namespace": "default"
            }
        }, {
            "query_name": "99th_percentile",
            "zero_value_on_null": true,
            "query_template": "histogram_quantile(0.99, sum(rate(istio_request_duration_seconds_bucket{reporter="source", source_app="istio-ingressgateway"}[$interval]$offset_str)) by (le, $entity_labels))",
            "entity_tags": {
                "destination_workload": "reviews-v2",
                "destination_service_namespace": "default"
            }
        }]
        """
        super().__init__(metric_spec, metrics_backend_url)

class Iter8Gauge(Iter8Metric): # custom
    def __init__(self, metric_spec, metrics_backend_url):
        """
        name = "iter8_error_rate",
        type = "gauge",
        query_specs = [{
            "query_name": "sample_size",
            "query_template": "sum(increase(istio_requests_total{reporter='source'}[$interval]$offset_str)) by ($entity_labels)",
            "entity_tags": {
                "destination_service_name": "reviews-v2-service",
                "destination_service_namespace": "default"
            }
        }, {
            "query_name": "value",
            "query_template": "sum(increase(istio_requests_total{response_code=~'5..',reporter='source'}[$interval]$offset_str)) by ($entity_labels)) / (sum(increase(istio_requests_total{reporter='source'}[$interval]$offset_str)) by ($entity_labels))",
            "entity_tags": {
                "destination_service_name": "reviews-v2-service",
                "destination_service_namespace": "default"
            }
        }]
        """
        super().__init__(metric_spec, metrics_backend_url)
        # the above call should have created self.prom

class Iter8Counter(Iter8Gauge): # counter is a gauge whose value keeps increasing
    pass
