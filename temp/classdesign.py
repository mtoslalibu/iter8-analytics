class Iter8Metric:
    def __init__(self, specs):
        self.specs = specs
        raise NotImplementedError

    def get_stats(self, interval, offset):
        raise NotImplementedError

class Iter8Histogram(Iter8Metric): # custom
    def __init__(self, specs):
        pass

    def get_stats(self, interval, offset):
        pass
        ### Return something like this...
        # "sample_size": 347,
        # "statistics": {
        #   "min": 20.3,
        #   "mean": 56.8,
        #   "max": 1204.8,
        #   "stddev": 201.3,
        #   "first_quartile": 200,
        #   "median": 70,
        #   "third_quartile": 200,
        #   "95th_percentile": 600,
        #   "99th_percentile": 750
        # }

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
            "query_name": "error_rate",
            "query_template": "sum(increase(istio_requests_total{response_code=~'5..',reporter='source'}[$interval]$offset_str)) by ($entity_labels)) / (sum(increase(istio_requests_total{reporter='source'}[$interval]$offset_str)) by ($entity_labels))",
            "entity_tags": {
                "destination_service_name": "reviews-v2-service",
                "destination_service_namespace": "default"
            }
        }]
        """
        super().__init__(specs)
        # the above call should have created self.prom

    def get_stats(self, interval, offset):
        results = self.prom.get_results(interval, offset)
        return {
            "sample_size": results["sample_size"],
            "value": results["error_rate"]
        }

class Iter8Counter(Iter8Gauge): # counter is a gauge whose value keeps increasing
    pass
