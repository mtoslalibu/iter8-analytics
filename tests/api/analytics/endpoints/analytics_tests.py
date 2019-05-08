"""Tests for the analytics REST API."""

import unittest
import json
from iter8_analytics import app as flask_app
from iter8_analytics.api.analytics import responses as responses
from iter8_analytics.api.analytics import request_parameters as request_parameters
import iter8_analytics.constants as constants
import dateutil.parser as parser

import logging
import os
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

        cls.backend_url = os.getenv(constants.ITER8_ANALYTICS_METRICS_BACKEND_URL_ENV)
        cls.metrics_endpoint = f'{cls.backend_url}/api/v1/query'
        log.info('Completed initialization for all analytics REST API tests.')

    def test_payload_check_and_increment(self):
        """Tests the REST endpoint /analytics/canary/check_and_increment."""

        endpoint = f'http://localhost:5555/api/v1/analytics/canary/check_and_increment'
        log.info('===TESTING ENDPOINT {endpoint}'.format(endpoint=endpoint))

        with requests_mock.mock() as m:
            m.get(self.metrics_endpoint, json=json.load(open("tests/data/sample_prometheus_response.json")))

            ###################
            # Test request with some required parameters
            ###################

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

            self.assertEqual(resp.status_code, 200, resp.data)

            ##################
            # Test request with start_time missing in payload
            ###################
            parameters = {
                "baseline": {
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
            # We should get a BAD REQUEST HTTP error
            self.assertEqual(resp.status_code, 400, 'Missing start_time parameter')
            assert b'\'start_time\' is a required property' in resp.data

            ##################
            # Test request with success_criteria missing in payload
            ###################
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
                },
                "_last_state": {}
            }
            # Call the REST API via the test client
            resp = self.flask_test.post(endpoint, json=parameters)
            # We should get a BAD REQUEST HTTP error
            self.assertEqual(resp.status_code, 400, 'Missing success_criteria missing in payload')

            assert b'\'success_criteria\' is a required property' in resp.data


            ###################
            # Test request with baseline missing in payload
            ###################
            parameters = {
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
            # We should get a BAD REQUEST HTTP error
            self.assertEqual(resp.status_code, 400, 'Baseline missing in payload')

            assert b'\'baseline\' is a required property' in resp.data
            ###################
            # Test request with missing value in success_criteria
            ###################

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
                            "type": "delta"
                        }
                    ]
                },
                "_last_state": {}
            }

            # Call the REST API via the test client
            resp = self.flask_test.post(endpoint, json=parameters)

            self.assertEqual(resp.status_code, 400, 'Missing value in success_criteria')

            assert b'\'value\' is a required property' in resp.data

            ###################
            # Test request with unknown metric_name in success_criteria
            ###################

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
                            "metric_name": "iter8_throughput",
                            "type": "delta",
                            "value": 0.02
                        }
                    ]
                },
                "_last_state": {}
            }

            # Call the REST API via the test client
            resp = self.flask_test.post(endpoint, json=parameters)

            self.assertEqual(resp.status_code, 400, 'Unknown metric_name in success_criteria')

            assert b'Metric name not found' in resp.data

            ###################
            # Test request with unknown type in success_criteria
            ###################

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
                            "type": "normal",
                            "value": 0.02
                        }
                    ]
                },
                "_last_state": {}
            }

            # Call the REST API via the test client
            resp = self.flask_test.post(endpoint, json=parameters)

            self.assertEqual(resp.status_code, 400, 'Unknown type in success_criteria')
            assert b'\'normal\' is not one of [\'delta\', \'threshold\']' in resp.data
