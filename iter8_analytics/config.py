# core python dependencies
import logging
import os
import sys

from django.core.validators import URLValidator
from django.core.exceptions import ValidationError

import iter8_analytics.constants as constants

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
        logging.getLogger('iter8_analytics').critical(f'Prometheus URL {prom_url} is invalid', e)
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

env_config = get_env_config()