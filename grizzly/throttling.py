import logging

from rest_framework.throttling import AnonRateThrottle
from configsetting.models import GlobalPreference
from grizzly.settings import DEFAULT_REQUEST_RATE_LIMIT


logger = logging.getLogger(__name__)


class CustomAnonThrottle(AnonRateThrottle):
    def get_rate(self):
        throttling_rate = \
            GlobalPreference.objects.filter(key='throttling_rate').first()
        if throttling_rate:
            t_rate = throttling_rate.value
        return t_rate or DEFAULT_REQUEST_RATE_LIMIT

    def get_cache_key(self, request, view):
        if request.user.is_authenticated:
            return None  # Only throttle unauthenticated requests.
        view_name = view.__class__.__name__ if view else ''

        username = request.GET.get('username')
        promotion = request.GET.get('promotion')

        return self.cache_format % {
            'scope': f'{self.scope}{view_name}',
            'ident': f'{username}_{promotion}'
        }

    def parse_rate(self, rate):
        """
        Given the request rate string, return a two tuple of:
        <allowed number of requests>, <period of time in seconds>
        """
        if rate is None:
            return (None, None)
        num, periods = rate.split('/')
        num_requests = int(num)
        periods = periods.split('.')
        durations = {'s': 1, 'm': 60, 'h': 3600, 'd': 86400}
        if len(periods) == 1:
            duration = durations.get(periods[0][0])
        elif len(periods) == 2:
            duration = int(periods[0]) * durations.get(periods[1][0])
        else:
            logger.error('Invalid throttle rate.')
            return (None, None)
        return (num_requests, duration)

    def allow_request(self, request, view):
        if request.method == 'GET':  # allow for GET request
            return True

        return super().allow_request(request, view)
