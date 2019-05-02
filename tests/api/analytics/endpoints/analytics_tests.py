"""Tests for the analytics REST API."""

import unittest
import json
from iter8_analytics import app as flask_app
from iter8_analytics.api.analytics import responses as responses
from iter8_analytics.api.analytics import request_parameters as request_parameters
import dateutil.parser as parser

import logging
import requests_mock
log = logging.getLogger(__name__)


class TestAnalyticsAPI(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        """Setup common to all tests."""

        # Initialize the Flask app for testing
        flask_app.app.testing = True
        flask_app.config_logger()
        flask_app.initialize(flask_app.app)

        # Get an internal Flask test client
        cls.flask_test = flask_app.app.test_client()

        log.info('Completed initialization for all analytics REST API tests.')

    def test_check_and_increment(self):
        """Tests the REST endpoint /analytics/canary/check_and_increment."""

        endpoint = '/api/v1/analytics/canary/check_and_increment'
        log.info('===TESTING ENDPOINT {endpoint}'.format(endpoint=endpoint))

        #####
        # Test request with an empty body
        #####

        log.info('======= Testing request with an empty body')

        # Call the REST API via the test client
        resp = self.flask_test.post(endpoint, json={})

        # We should get a BAD REQUEST HTTP error
        self.assertEqual(resp.status_code, 400,
                         'Expected a 400 HTTP code, but received a {0}'
                         .format(resp.status_code))

        #####
        # Test request with some optional parameters
        #####

        parameters = {
            "baseline": {
                "start_time": "2019-04-24T19:40:32.017Z",
                "tags": {
                    "destination_service_name": "reviews-v2"
                }
            },
            "canary": {
                "start_time": "2019-04-24T19:40:32.017Z",
                "tags": {
                    "destination_service_name": "reviews-v2"
                }
            },
            "traffic_control": {
                "success_criteria": [
                    {
                        "metric_name": "iter8_latency",
                        "type": "delta",
                        "value": 0.02
                    }
                ]
            },
            "_last_state": {}
        }

        # Call the REST API via the test client
        resp = self.flask_test.post(endpoint, json=parameters)

        self.assertEqual(resp.status_code, 200,
                         'Expected a 200 HTTP code, but received a {0}'
                         .format(resp.status_code))

        expected_response = {
            responses.METRIC_BACKEND_URL_STR: None,
            request_parameters.BASELINE_STR: {
                responses.METRICS_STR: None,
                responses.TRAFFIC_PERCENTAGE_STR: None
            },
            request_parameters.CANARY_STR: {
                responses.METRICS_STR: None,
                responses.TRAFFIC_PERCENTAGE_STR: None
            },
            responses.ASSESSMENT_STR: {
                responses.SUMMARY_STR: {
                    responses.CONCLUSIONS_STR: None,
                    responses.ALL_SUCCESS_CRITERIA_MET: False,
                    responses.ABORT_EXPERIMENT_STR: False
                },
                responses.SUCCESS_CRITERIA_STR: None
            },
            request_parameters.LAST_STATE_STR: None
        }

        assert resp.is_json
        self.assertEquals(json.loads(resp.get_data()), expected_response)

    def test_start_and_end_time(self):
        """Tests the REST endpoint /analytics/canary/check_and_increment."""

        endpoint = '/api/v1/analytics/canary/check_and_increment'
        log.info('===TESTING ENDPOINT {endpoint}'.format(endpoint=endpoint))

        #####
        # Test request with start time less than end time

        parameters = {
            "baseline": {
                "start_time": "2019-04-24T19:40:32.017Z",
                "end_time": "2019-04-24T19:40:32.017Z",
                "tags": {
                    "destination_service_name": "reviews-v2"
                }
            },
            "canary": {
                "start_time": "2019-04-24T19:40:32.017Z",
                "end_time": "2019-04-24T19:40:32.017Z",
                "tags": {
                    "destination_service_name": "reviews-v2"
                }
            },
            "traffic_control": {
                "success_criteria": [
                    {
                        "metric_name": "iter8_latency",
                        "type": "delta",
                        "value": 0.02
                    }
                ]
            },
            "_last_state": {}
        }
        resp = self.flask_test.post(endpoint, json=parameters)
        self.assertEqual(resp.status_code, 400,
                         f'Expected a 400 HTTP code, but received a {resp.status_code}')
