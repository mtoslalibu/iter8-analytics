"""Tests for the analytics REST API."""

import unittest
from unittest.mock import Mock
from unittest.mock import patch
from requests.models import Response

import json
from iter8_analytics import app as flask_app
from iter8_analytics.api.analytics import responses as responses
from iter8_analytics.api.analytics import request_parameters as request_parameters
import iter8_analytics.constants as constants
import dateutil.parser as parser

import logging
import os
import requests_mock
import requests
log = logging.getLogger(__name__)

import re

from urllib.parse import urlencode

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
        cls.endpoint = f'http://localhost:5555/api/v1/analytics/canary/check_and_increment'
        log.info('Completed initialization for all analytics REST API tests.')


    def conduct_experiment(self,experiment_data):
        for iteration in experiment_data:
            with patch('requests.get') as mock_get:
                response_list = []
                for each_dict in iteration["prometheus_responses"]:
                    the_response = Response()
                    the_response._content=bytes(json.dumps(each_dict), 'utf-8')
                    response_list.append(the_response)

                log.info(iteration["prometheus_responses"])

                mock_get.side_effect = response_list

                payload = iteration["request_payload"]

                resp = self.flask_test.post(self.endpoint, json=payload)
                bytecode_response = resp.data
                json_response = json.loads(bytecode_response.decode('utf8').replace("'", '"'))

                self.assertEqual(json_response["_last_state"], iteration["service_response"]["_last_state"])
                self.assertEqual(json_response["assessment"]["summary"]["all_success_criteria_met"], iteration["service_response"]["assessment"]["summary"]["all_success_criteria_met"])
                self.assertEqual(json_response["assessment"]["summary"]["abort_experiment"], iteration["service_response"]["assessment"]["summary"]["abort_experiment"])
                conclusion_check = True if set(iteration["service_response"]["assessment"]["summary"]["conclusions"]).issubset(json_response["assessment"]["summary"]["conclusions"]) else False
                self.assertTrue(conclusion_check)


    def test_rollforward_rollforward(self):
        all_files = os.listdir("tests/data/rf_rf")

        for each_file in all_files:
            if each_file == ".DS_Store":
                continue
            with open("tests/data/rf_rf/"+each_file) as f:
                experiment_data = json.load(f)
                self.conduct_experiment(experiment_data)

    def test_payload_check_and_increment(self):
        """Tests the REST endpoint /analytics/canary/check_and_increment."""

        endpoint = f'http://localhost:5555/api/v1/analytics/canary/check_and_increment'

        with requests_mock.mock() as m:
            m.get(self.metrics_endpoint, json=json.load(open("tests/data/prometheus_sample_response.json")))

            ###################
            # Test request with some required parameters
            ###################
            log.info("\n\n\n")
            log.info('===TESTING ENDPOINT {endpoint}'.format(endpoint=endpoint))
            log.info("Test request with some required parameters")

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
            log.info("\n\n\n")
            log.info('===TESTING ENDPOINT {endpoint}'.format(endpoint=endpoint))
            log.info("Test request with start_time missing in payload")

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
            log.info("\n\n\n")
            log.info('===TESTING ENDPOINT {endpoint}'.format(endpoint=endpoint))
            log.info("Test request with success_criteria missing in payload")

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
            log.info("\n\n\n")
            log.info('===TESTING ENDPOINT {endpoint}'.format(endpoint=endpoint))
            log.info("Test request with baseline missing in payload")

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
            log.info("\n\n\n")
            log.info('===TESTING ENDPOINT {endpoint}'.format(endpoint=endpoint))
            log.info("Test request with missing value in success_criteria")


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
            log.info("\n\n\n")
            log.info('===TESTING ENDPOINT {endpoint}'.format(endpoint=endpoint))
            log.info("Test request with unknown metric_name in success_criteria")

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
            log.info("\n\n\n")
            log.info('===TESTING ENDPOINT {endpoint}'.format(endpoint=endpoint))
            log.info("Test request with unknown type in success_criteria")

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

    def test_no_data_from_prometheus(self):
        """Tests the REST endpoint /analytics/canary/check_and_increment."""

        endpoint = f'http://localhost:5555/api/v1/analytics/canary/check_and_increment'

        with requests_mock.mock() as m:
            m.get(self.metrics_endpoint, json=json.load(open("tests/data/prometheus_no_data_response.json")))

            ###################
            # Test request with no data from prometheus
            ###################
            log.info("\n\n\n")
            log.info('===TESTING ENDPOINT {endpoint}'.format(endpoint=endpoint))
            log.info("Test request with no data from prometheus")

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


    def test_rollforward_rollback(self):
        pass

    def test_rollback_rollforward(self):
        pass

    def test_rollback_rollback(self):
        pass
