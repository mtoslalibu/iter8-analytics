"""
REST resources related to canary analytics.
"""

import iter8_analytics.api.analytics.request_parameters as request_parameters
import iter8_analytics.api.analytics.responses as responses
from iter8_analytics.api.restplus import api
from iter8_analytics.metrics_backend.iter8metric import Iter8Histogram, Iter8Gauge, Iter8Counter, Iter8MetricFactory
from iter8_analytics.metrics_backend.successcriteria import DeltaCriterion, ThresholdCriterion
from flask_restplus import Resource
from flask import request
import argparse
import json
import logging



argparser = argparse.ArgumentParser(description='Bring up iter8 analytics service.')
argparser.add_argument('-p', '--promconfig', metavar = "<path/to/promconfig.json>", help='prometheus configuration file', required=True)
argparser.add_argument('-m', '--metricsconfig', metavar = "<path/to/promconfig.json>", help='metrics configuration file', required=True)
args = argparser.parse_args()

prom_config = json.load(open(args.promconfig))
metrics_config = json.load(open(args.metricsconfig))

log = logging.getLogger(__name__)

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
        self.metric_factory = Iter8MetricFactory(prom_config["metric_backend_url"])
        self.create_response_object(payload)


        for each_criterion in payload["traffic_control"]["success_criteria"]:
            self.response["baseline"]["metrics"].append(self.get_results(each_criterion["metric_name"], payload["baseline"]))
            self.response["canary"]["metrics"].append(self.get_results(each_criterion["metric_name"], payload["canary"]))
            self.get_success_criteria(each_criterion)
        return self.response

    def get_success_criteria(self, criterion):
        assessment_statistic_name = metrics_config[criterion["metric_name"]]["assessment_statistic_name"]
        if criterion["type"] == "delta":
            self.response["assessment"]["success_criteria"].append(DeltaCriterion(criterion, self.response["baseline"]["metrics"][-1], self.response["canary"]["metrics"][-1], assessment_statistic_name).test())
        else:
            self.response["assessment"]["success_criteria"].append(ThresholdCriterion(criterion, self.response["canary"]["metrics"][-1], assessment_statistic_name).test())
        print(self.response["assessment"]["success_criteria"])

    def create_response_object(self, payload):
        self.response = {
            "metric_backend_url": prom_config["metric_backend_url"],
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
        metric_spec = self.metric_factory.create_metric_spec(metrics_config, metric_name, payload["tags"])
        metrics_object = self.metric_factory.get_iter8_metric(metric_spec)
        interval_str, offset_str = self.metric_factory.get_interval_and_offset_str(payload["start_time"], payload["end_time"])
        statistics =  metrics_object.get_stats(interval_str, offset_str)
        return {
            "metric_name": metric_name,
            "metric_type": metrics_config[metric_name]["type"],
            "statistics": statistics
        }
