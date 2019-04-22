from flask_restplus import Api
from jsonschema import FormatChecker

import logging
log = logging.getLogger(__name__)

#  Instantiate a Flask-RESTPlus API
api = Api(version='1.0', title='iter8 analytics REST API',
          description='API to perform analytics to support canary releases and A/B tests',
          format_checker=FormatChecker(formats=("date-time",)))


def build_http_error(msg, http_code):
    '''Returns a specific error message and HTTP code pip that can be used by the REST API'''
    return {'message': msg}, http_code


@api.errorhandler
def default_error_handler(e):
    '''Error handler for uncaught exceptions'''
    message = 'An unexpected error occurred'
    log.exception(message)
    return {'message': message}, 500
