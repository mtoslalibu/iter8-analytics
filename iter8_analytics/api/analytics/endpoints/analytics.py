"""
REST resources related to canary analytics.
"""

import iter8_analytics.api.analytics.request_parameters as request_parameters
import iter8_analytics.api.analytics.responses as responses
from iter8_analytics.api.restplus import api
from iter8_analytics.metrics_backend.iter8metric import Iter8MetricFactory
from iter8_analytics.metrics_backend.successcriteria import DeltaCriterion, ThresholdCriterion
import iter8_analytics.constants as constants
from flask_restplus import Resource
from flask import request

import json
import os
import logging

log = logging.getLogger(__name__)

metrics_config = {
  "iter8_latency": {
    "type": "histogram",
    "zero_value_on_null": True,
    "query_templates": {
      "sample_size": "sum(increase(istio_requests_total{reporter='source'}[$interval]$offset_str)) by ($entity_labels)",
      "min": "sum(increase(istio_request_duration_seconds_bucket{reporter='source'}[$interval]$offset_str)) by (le, $entity_labels)",
      "mean": "(sum(increase(istio_request_duration_seconds_sum{reporter='source'}[$interval]$offset_str)) by ($entity_labels)) / (sum(increase(istio_request_duration_seconds_count{reporter='source'}[$interval]$offset_str)) by ($entity_labels))",
      "max": "sum(increase(istio_request_duration_seconds_bucket{reporter='source'}[$interval]$offset_str)) by (le, $entity_labels)",
      "stddev": "sum(increase(istio_request_duration_seconds_bucket{reporter='source'}[$interval]$offset_str)) by (le, $entity_labels)",
      "first_quartile": "histogram_quantile(0.25, sum(rate(istio_request_duration_seconds_bucket{reporter='source'}[$interval]$offset_str)) by (le, $entity_labels))",
      "median": "histogram_quantile(0.5, sum(rate(istio_request_duration_seconds_bucket{reporter='source'}[$interval]$offset_str)) by (le, $entity_labels))",
      "third_quartile": "histogram_quantile(0.75, sum(rate(istio_request_duration_seconds_bucket{reporter='source'}[$interval]$offset_str)) by (le, $entity_labels))",
      "95th_percentile": "histogram_quantile(0.95, sum(rate(istio_request_duration_seconds_bucket{reporter='source'}[$interval]$offset_str)) by (le, $entity_labels))",
      "99th_percentile": "histogram_quantile(0.99, sum(rate(istio_request_duration_seconds_bucket{reporter='source'}[$interval]$offset_str)) by (le, $entity_labels))",
      "value": "(sum(increase(istio_request_duration_seconds_sum{reporter='source'}[$interval]$offset_str)) by ($entity_labels)) / (sum(increase(istio_request_duration_seconds_count{reporter='source'}[$interval]$offset_str)) by ($entity_labels))"
    }
  },
  "iter8_error_rate": {
    "type": "gauge",
    "zero_value_on_null": True,
    "query_templates": {
      "sample_size": "sum(increase(istio_requests_total{reporter='source'}[$interval]$offset_str)) by ($entity_labels)",
      "value": "sum(increase(istio_requests_total{response_code=~'5..',reporter='source'}[$interval]$offset_str)) by ($entity_labels) / sum(increase(istio_requests_total{reporter='source'}[$interval]$offset_str)) by ($entity_labels)"
    }
  },
  "iter8_error_count": {
    "type": "counter",
    "zero_value_on_null": True,
    "query_templates": {
      "sample_size": "sum(increase(istio_requests_total{reporter='source'}[$interval]$offset_str)) by ($entity_labels)",
      "value": "sum(increase(istio_requests_total{response_code=~'5..',reporter='source'}[$interval]$offset_str)) by ($entity_labels)) / (sum(increase(istio_requests_total{reporter='source'}[$interval]$offset_str)) by ($entity_labels))"
    }
  }
}

prom_url = os.getenv(constants.ITER8_ANALYTICS_METRICS_BACKEND_URL_ENV)

analytics_namespace = api.namespace(
    'analytics',
    description='Operations to support canary releases and A/B tests')

#################
# REST API
#################


@analytics_namespace.route('/canary/check_and_increment')
class CanaryCheckAndIncrement(Resource):

    @api.expect(request_parameters.check_and_increment_parameters,
                validate=True)
    @api.marshal_with(responses.check_and_increment_response)
    def post(self):
        """Assess the canary version and recommend traffic-control actions."""
        log.info('Started processing request to assess the canary using the '
                 '"check_and_increment" strategy')

        payload = request.get_json()
        self.metric_factory = Iter8MetricFactory(
            prom_url)
        self.create_response_object(payload)

        for each_criterion in payload["traffic_control"]["success_criteria"]:
            self.response["baseline"]["metrics"].append(self.get_results(
                each_criterion["metric_name"], payload["baseline"]))
            self.response["canary"]["metrics"].append(self.get_results(
                each_criterion["metric_name"], payload["canary"]))
            self.append_success_criteria(each_criterion)

        self.append_assessment_summary()
        self.append_traffic_decision(payload)
        return self.response

    def append_success_criteria(self, criterion):
        if criterion["type"] == "delta":
            self.response["assessment"]["success_criteria"].append(DeltaCriterion(
                criterion, self.response["baseline"]["metrics"][-1], self.response["canary"]["metrics"][-1]).test())
        else:
            self.response["assessment"]["success_criteria"].append(
                ThresholdCriterion(criterion, self.response["canary"]["metrics"][-1]).test())
        # print(self.response["assessment"]["success_criteria"])

    def append_assessment_summary(self):
        self.response["assessment"]["summary"]["all_success_criteria_met"] = all(
            each_criterion["success_criterion_met"] for each_criterion in self.response["assessment"]["success_criteria"])
        self.response["assessment"]["summary"]["abort_experiment"] = any(
            each_criterion["abort_experiment"] for each_criterion in self.response["assessment"]["success_criteria"])
        self.response["assessment"]["summary"]["conclusions"] = ["All ok"]

    def append_traffic_decision(self, experiment):
        if not experiment["_last_state"]:  # if it is empty
            last_state = {
                "baseline": {
                    "traffic_percentage": 100.0
                },
                "canary": {
                    "traffic_percentage": 0.0
                }
            }
        else:
            last_state = experiment["_last_state"]
        # Compute current decisions below based on increment or hold
        if self.response["assessment"]["summary"]["all_success_criteria_met"]:
            new_canary_traffic_percentage = min(
                last_state["canary"]["traffic_percentage"] +
                experiment["traffic_control"]["step_size"],
                experiment["traffic_control"]["max_traffic_percent"])
        else:
            new_canary_traffic_percentage = last_state["canary"]["traffic_percentage"]
        new_baseline_traffic_percentage = 100.0 - new_canary_traffic_percentage

        self.response["_last_state"] = {
            "baseline": {
                "traffic_percentage": new_baseline_traffic_percentage
            },
            "canary": {
                "traffic_percentage": new_canary_traffic_percentage
            }
        }
        self.response["baseline"]["traffic_percentage"] = new_baseline_traffic_percentage
        self.response["canary"]["traffic_percentage"] = new_canary_traffic_percentage

    def create_response_object(self, payload):
        """Create response object corresponding to payload. This has everything and more."""
        self.response = {
            "metric_backend_url": prom_url,
            "canary": {
                "metrics": [],
                "traffic_percentage": None
            },
            "baseline": {
                "metrics": [],
                "traffic_percentage": None
            },
            "assessment": {
                "summary": {},
                "success_criteria": []
            }
        }

    def get_results(self, metric_name, payload):
        metric_spec = self.metric_factory.create_metric_spec(
            metrics_config, metric_name, payload["tags"])
        metrics_object = self.metric_factory.get_iter8_metric(metric_spec)
        interval_str, offset_str = self.metric_factory.get_interval_and_offset_str(
            payload["start_time"], payload["end_time"])
        statistics = metrics_object.get_stats(interval_str, offset_str)
        return {
            "metric_name": metric_name,
            "metric_type": metrics_config[metric_name]["type"],
            "statistics": statistics
        }
