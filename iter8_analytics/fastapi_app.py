"""Fast API based iter8 analytics service.
"""
# core python dependencies
import logging
import os
import sys

# external dependencies
from fastapi import FastAPI, Body
import uvicorn
from django.core.validators import URLValidator
from django.core.exceptions import ValidationError

# iter8 dependencies
from iter8_analytics.api.analytics.types import ExperimentIterationParameters, Iter8AssessmentAndRecommendation
from iter8_analytics.api.analytics.experiment import Experiment
from iter8_analytics.api.analytics.endpoints.examples import eip_example
import iter8_analytics.constants as constants

# main FastAPI app
app = FastAPI()

@app.post("/assessment", response_model=Iter8AssessmentAndRecommendation)
def provide_assessment_for_this_experiment_iteration(eip: ExperimentIterationParameters = Body(..., example=eip_example)):
    """
    POST iter8 experiment iteration data and obtain assessment of how the versions are performing and recommendations on how to split traffic based on multiple strategies.
    \f
    :body eip: ExperimentIterationParameters
    """
    return Experiment(eip).run()


@app.get("/health_check")
def provide_iter8_analytics_health():
    """Get iter8 analytics health status"""
    return {"status": "Ok"}


def config_logger(log_level = "debug"):
    """Configures the global logger

    Args:
        log_level (str): log level ('debug', 'info', ...)
    """
    logger = logging.getLogger('iter8_analytics')
    handler = logging.StreamHandler()

    if str.lower(log_level) == 'info':
        logger.setLevel(logging.INFO)
        handler.setLevel(logging.INFO)
    elif str.lower(log_level) == 'warning':
        logger.setLevel(logging.WARNING)
        handler.setLevel(logging.WARNING)
    elif str.lower(log_level) == 'error':
        logger.setLevel(logging.ERROR)
        handler.setLevel(logging.ERROR)
    elif str.lower(log_level) == 'critical':
        logger.setLevel(logging.CRITICAL)
        handler.setLevel(logging.CRITICAL)
    else:
        logger.setLevel(logging.DEBUG)
        handler.setLevel(logging.DEBUG)

    formatter = logging.Formatter(
        fmt='%(asctime)s - %(name)s - %(levelname)s'
            ' - %(filename)s:%(lineno)d - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logging.getLogger('iter8_analytics').info("Configured logger")

def get_env_config():
    """
      Read the environment variables that control the server behavior and populate the config dictionary

      Returns:
        config (Dict): config dictionary
      """

    prom_url = os.getenv(constants.ITER8_ANALYTICS_METRICS_BACKEND_URL_ENV)
    if prom_url is None:
        logging.getLogger('iter8_analytics').critical(
            u'The environment variable {0} was not set. '
            'Example of a valid value: "http://localhost:9090". '
            'Aborting!'.format(constants.ITER8_ANALYTICS_METRICS_BACKEND_URL_ENV))
        sys.exit(1)

    val = URLValidator()
    try:
        val(prom_url)
    except ValidationError as e:
        logging.getLogger('iter8_analytics').critical(f'Prometheus URL {prom_url} is invalid')
        sys.exit(1)

    logging.getLogger('iter8_analytics').info('Configuring iter8 analytics server')

    config = {}
    config[constants.ITER8_ANALYTICS_LOG_LEVEL_ENV] = os.getenv(
        constants.ITER8_ANALYTICS_LOG_LEVEL_ENV, 'debug')

    config[constants.ITER8_ANALYTICS_SERVER_PORT_ENV] = os.getenv(
        constants.ITER8_ANALYTICS_SERVER_PORT_ENV, 5555)

    logging.getLogger('iter8_analytics').info(
        u'The iter8 analytics server will listen on port {0}. '
        'This value can be set by the environment variable {1}'.format(config[constants.ITER8_ANALYTICS_SERVER_PORT_ENV], constants.ITER8_ANALYTICS_SERVER_PORT_ENV))

    return config

if __name__ == '__main__':
    env_config = get_env_config()
    config_logger(env_config[constants.ITER8_ANALYTICS_LOG_LEVEL_ENV])
    uvicorn.run('fastapi_app:app', host='0.0.0.0', port=int(env_config[constants.ITER8_ANALYTICS_SERVER_PORT_ENV]), log_level=env_config[constants.ITER8_ANALYTICS_LOG_LEVEL_ENV])
