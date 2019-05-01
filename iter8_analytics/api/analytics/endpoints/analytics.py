"""
REST resources related to canary analytics.
"""

import iter8_analytics.api.analytics.request_parameters as request_parameters
import iter8_analytics.api.analytics.responses as responses
from iter8_analytics.api.restplus import api
from iter8_analytics.metrics_backend.iter8metric import Iter8MetricFactory
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
            self.append_success_criteria(each_criterion)

        self.append_assessment_summary()
        self.append_traffic_decision(payload["_last_state"])
        return self.response

    def append_success_criteria(self, criterion):
        if criterion["type"] == "delta":
            self.response["assessment"]["success_criteria"].append(DeltaCriterion(criterion, self.response["baseline"]["metrics"][-1], self.response["canary"]["metrics"][-1]).test())
        else:
            self.response["assessment"]["success_criteria"].append(ThresholdCriterion(criterion, self.response["canary"]["metrics"][-1]).test())
        #print(self.response["assessment"]["success_criteria"])

    def append_assessment_summary(self):
        self.response["assessment"]["summary"]["all_success_criteria_met"] = all(each_criterion["success_criterion_met"] for each_criterion in self.response["assessment"]["success_criteria"])
        self.response["assessment"]["summary"]["abort_experiment"] = any(each_criterion["abort_experiment"] for each_criterion in self.response["assessment"]["success_criteria"])
        self.response["assessment"]["summary"]["conclusions"] = ["All ok"]

    def append_traffic_decision(self, experiment):
        if not experiment["_last_state"]: # if it is empty
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
        ### Compute current decisions below based on increment or hold
        if self.response["assessment"]["summary"]["all_success_criteria_met"]:
            new_canary_traffic_percentage = min(
                last_state["canary"]["traffic_percentage"] + 
                experiment["traffic_control"]["step_size"], 
                experiment["traffic_control"]["max_traffic_percent"])
        else:
            new_canary_traffic_percentage = last_state["canary"]["traffic_percentage"]
        new_baseline_traffic_percentage = 100.0 - new_canary_traffic_percentage

        self.response["_last_state"] = last_state
        self.response["baseline"]["traffic_percentage"] = new_baseline_traffic_percentage
        self.response["canary"]["traffic_percentage"] = new_canary_traffic_percentage
        

    def create_response_object(self, payload):
        """Create response object corresponding to payload. This has everything and more."""
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
