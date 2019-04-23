"""
REST resources related to canary analytics.
"""

import iter8_analytics.api.analytics.request_parameters as request_parameters
import iter8_analytics.api.analytics.responses as responses
from iter8_analytics.api.restplus import api
from flask_restplus import Resource
from flask import request
import argparse
import json
import logging

parser = argparse.ArgumentParser(description='Bring up iter8 analytics service.')
parser.add_argument('-p', '--promconfig', metavar = "<path/to/promconfig.json>", help='prometheus configuration file', required=True)
args = parser.parse_args()

prom_config = json.load(open(args.promconfig))

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
        log.info(f"{request.get_json()}")
        return {
            "metric_backend_url": prom_config["metric_backend_url"]
        }
