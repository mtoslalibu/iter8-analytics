import os
import requests_mock
import logging
import json

from fastapi.testclient import TestClient

import iter8_analytics.constants as constants
from iter8_analytics import fastapi_app

from iter8_analytics.api.analytics.experiment_iteration_request import ExperimentIterationParameters
from iter8_analytics.api.analytics.endpoints.examples import eip_example
from iter8_analytics.api.analytics.experiment_iteration_response import Iter8AssessmentAndRecommendation

env_config = fastapi_app.get_env_config()
fastapi_app.config_logger(env_config[constants.ITER8_ANALYTICS_LOG_LEVEL_ENV])
logger = logging.getLogger('iter8_analytics')

test_client = TestClient(fastapi_app.app)
metrics_backend_url = os.getenv(constants.ITER8_ANALYTICS_METRICS_BACKEND_URL_ENV)
metrics_endpoint = f'{metrics_backend_url}/api/v1/query'

# class TestUnifiedAnalyticsAPI:
#     def test_fastapi(self):
#         # fastapi endpoint
#         with requests_mock.mock(real_http=True) as m:
#             m.get(metrics_endpoint, json=json.load(open("tests/data/prometheus_sample_response.json")))

#             endpoint = "/assessment"

#             # fastapi post data
#             eip = ExperimentIterationParameters(** eip_example)

#             logger.info("\n\n\n")
#             logger.info('===TESTING FASTAPI ENDPOINT')
#             logger.info("Test request with some required parameters")

#             # Call the FastAPI endpoint via the test client
#             resp = test_client.post(endpoint, json = eip_example)
#             it8_ar_example = Iter8AssessmentAndRecommendation(** resp.json())
#             assert resp.status_code == 200
