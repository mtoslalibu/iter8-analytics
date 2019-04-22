class Iter8Metric:
    def __init__(self, name, type, query_specs):
        self.name = name
        self.type = type
        self.query_specs = query_specs
        self.prom_queries = [PrometheusQuery(prom_url, query_spec) for query_spec in query_specs]

    def get_stats(self, interval_str, offset_str=""):
        results = {}
        for query in self.prom_queries:
            results[query.query_name] = query.query_from_template(interval_str, offset_str)
        return results


class Iter8Histogram(Iter8Metric): # custom
    def __init__(self, name, type, query_specs):
        """
        name = "iter8_latency",
        type = "histogram",
        query_specs = [{
            "query_name": "sample_size",
            "query_template": "sum(increase(istio_requests_total{reporter='source'}[$interval]$offset_str)) by ($entity_labels)",
            "entity_tags": {
                "destination_service_name": "treenode-s6dml-service",
                "destination_service_namespace": "default"
            }
        }, {
            "query_name": "min",
            "query_template": "sum(increase(istio_request_duration_seconds_bucket{reporter="source", source_app="istio-ingressgateway"}[$interval]$offset_str)) by (le, $entity_labels)",
            "aggregation": "min",
            "entity_tags": {
                "destination_service_name": "reviews-v2-service",
                "destination_service_namespace": "default"
            }
        }, {
            "query_name": "mean",
            "query_template": "(sum(increase(istio_request_duration_seconds_sum{source_app='istio-ingressgateway', reporter='source'}[$interval]$offset_str)) by ($entity_labels)) / (sum(increase(istio_request_duration_seconds_count{source_app='istio-ingressgateway', reporter='source'}[$interval]$offset_str)) by ($entity_labels))",
            "entity_tags": {
                "destination_service_name": "reviews-v2-service",
                "destination_service_namespace": "default"
            }
        }, {
            "query_name": "max",
            "query_template": "sum(increase(istio_request_duration_seconds_bucket{reporter="source", source_app="istio-ingressgateway"}[$interval]$offset_str)) by (le, $entity_labels)",
            "aggregation": "max",
            "entity_tags": {
                "destination_service_name": "reviews-v2-service",
                "destination_service_namespace": "default"
        }, {
            "query_name": "stddev",
            "query_template": "sum(increase(istio_request_duration_seconds_bucket{reporter="source", source_app="istio-ingressgateway"}[$interval]$offset_str)) by (le, $entity_labels)",
            "aggregation": "stddev",
            "entity_tags": {
                "destination_service_name": "reviews-v2-service",
                "destination_service_namespace": "default"
        }, {
            "query_name": "first_quartile",
            "query_template": "histogram_quantile(0.25, sum(rate(istio_request_duration_seconds_bucket{reporter="source", source_app="istio-ingressgateway"}[$interval]$offset_str)) by (le, $entity_labels))",
            "entity_tags": {
                "destination_service_name": "reviews-v2-service",
                "destination_service_namespace": "default"
        }, {
            "query_name": "median",
            "query_template": "histogram_quantile(0.5, sum(rate(istio_request_duration_seconds_bucket{reporter="source", source_app="istio-ingressgateway"}[$interval]$offset_str)) by (le, $entity_labels))",
            "entity_tags": {
                "destination_service_name": "reviews-v2-service",
                "destination_service_namespace": "default"
        }, {
            "query_name": "third_quartile",
            "query_template": "histogram_quantile(0.75, sum(rate(istio_request_duration_seconds_bucket{reporter="source", source_app="istio-ingressgateway"}[$interval]$offset_str)) by (le, $entity_labels))",
            "entity_tags": {
                "destination_service_name": "reviews-v2-service",
                "destination_service_namespace": "default"
        }, {
            "query_name": "95th_percentile",
            "query_template": "histogram_quantile(0.95, sum(rate(istio_request_duration_seconds_bucket{reporter="source", source_app="istio-ingressgateway"}[$interval]$offset_str)) by (le, $entity_labels))",
            "entity_tags": {
                "destination_service_name": "reviews-v2-service",
                "destination_service_namespace": "default"
        }, {
            "query_name": "99th_percentile",
            "query_template": "histogram_quantile(0.99, sum(rate(istio_request_duration_seconds_bucket{reporter="source", source_app="istio-ingressgateway"}[$interval]$offset_str)) by (le, $entity_labels))",
            "entity_tags": {
                "destination_service_name": "reviews-v2-service",
                "destination_service_namespace": "default"
        }]
        """
        super().__init__(name, type, query_specs)

class Iter8Gauge(Iter8Metric): # custom
    def __init__(self, name, type, query_specs):
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
            "query_name": "gauge",
            "query_template": "sum(increase(istio_requests_total{response_code=~'5..',reporter='source'}[$interval]$offset_str)) by ($entity_labels)) / (sum(increase(istio_requests_total{reporter='source'}[$interval]$offset_str)) by ($entity_labels))",
            "entity_tags": {
                "destination_service_name": "reviews-v2-service",
                "destination_service_namespace": "default"
            }
        }]
        """
        super().__init__(name, type, query_specs)
        # the above call should have created self.prom

class Iter8Counter(Iter8Gauge): # counter is a gauge whose value keeps increasing
    pass
