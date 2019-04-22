"""
REST resource related to the health of the server.
"""

from iter8_analytics.api.restplus import api
from flask_restplus import Resource

import logging
log = logging.getLogger(__name__)

health_namespace = api.namespace(
    'health', description='Operations to check the server health')


@health_namespace.route('/health_check')
class HealthCheck(Resource):

    @api.response(200, 'iter8 analytics server is responsive')
    def get(self):
        '''Checks the server health'''
        log.debug('Checking server status')
        return {'status': 'OK'}
