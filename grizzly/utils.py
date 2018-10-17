import logging

from django_otp.plugins.otp_totp.models import TOTPDevice
from django.utils.translation import ugettext as _
from oauth2_provider.models import AccessToken
from rest_framework import renderers
from rest_framework.views import exception_handler
from rest_framework.exceptions import Throttled

from grizzly.lib import constants


logger = logging.getLogger(__name__)


def custom_exception_handler(exc, context):
    """
    Call REST framework's default exception handler first,
    to get the standard error response.

    This overriden handler should standardize the error response
    format for ghost:
    response.data = {key: [list of errors]}
    """

    response = exception_handler(exc, context)
    request = context.get('request', None)
    if isinstance(exc, Throttled):
        throttled_data = {'error': [f'支付请求太频繁，请{exc.wait}s后再来']}
        response.data = throttled_data
        return response
    if request and request.META.get('HTTP_AUTHORIZATION'):
        try:
            token = request.META.get('HTTP_AUTHORIZATION').split(' ')
            access_token = token[1]
            token_obj = AccessToken.objects.get(token=access_token)
            if token_obj.is_expired():
                response.data['error'] = 'Token has already expired'
        except Exception as exc:
            logger.error(exc)
            pass
    try:
        if response.status_code in [400, 401, 404, 403, 405, 429]:
            data_cpy = response.data.copy()
            error_list = []
            if isinstance(data_cpy, dict):
                for key, msg in data_cpy.items():
                    error_msg = msg
                    if isinstance(key, int) and isinstance(msg, list):
                        error_msg = msg[0]
                    if key == 'error' or key == 'detail':
                        error_list.append(error_msg)
                        continue
                    error_list.append({key: error_msg})
            elif isinstance(data_cpy, list):
                error_list = response.data
            response.data = {'error': error_list}
    except Exception as exc:
        logger.error(exc)

    return response


def get_user_type(user):
    if user:
        if hasattr(user, 'staff_user'):
            return 'staff'
        else:
            return 'admin'
    return None


def parse_request_for_token(request):
    token = (request.META.get('HTTP_AUTHORIZATION') or '').split(' ')

    if len(token) < 2 or token[0] != 'Bearer':
        return None, None

    access_token = token[1]
    token_obj = AccessToken.objects.filter(token=access_token). \
        select_related('user').first()

    if not token_obj:
        return None, None

    # Note: AccessToken.user is nullable
    user = token_obj.user
    if user:
        user_type = get_user_type(user)
        return user, user_type

    return None, None


def get_valid_token(request, try_cookies=False, select_related_user=True):
    # get access token string
    auth_str = request.META.get('HTTP_AUTHORIZATION') or ''
    auth_segments = auth_str.split(' ')
    if len(auth_segments) >= 2 and auth_segments[0] == 'Bearer':
        access_token_str = auth_segments[1]
    elif try_cookies:
        access_token_str = request.COOKIES.get('access_token')
    else:
        return None

    # get access token object
    # Note:
    # AccessToken.token has no unique constraint.
    # Using get could raise MultipleObjectsReturned exception.
    # Use filter().first() instead.
    if select_related_user:
        access_token = AccessToken.objects.select_related('user') \
            .filter(token=access_token_str) \
            .first()
    else:
        access_token = AccessToken.objects.filter(token=access_token_str) \
            .first()
    if not access_token or access_token.is_expired():
        return None
    return access_token


def create_otp_device(user, device_name=None):
    dname = device_name or f'{user.username}-otp'
    otp_device = TOTPDevice(user=user, name=dname)
    otp_device.save()


def get_request_data(request):
    if not hasattr(request, 'data'):
        return request.GET

    # first assume through POST
    try:
        data = request.data.dict()
    except Exception as exc:
        logger.info(exc)
        data = request.data.copy()

    if not data:
        data = request.GET.dict()

    return data


class GrizzlyRenderer(renderers.JSONRenderer):
    """
    @brief
        Override JSONRenderer to create a custom payload struct.
        There will be 3 sources of data for this render
        1. raised error which will go through the exception handler
        2. returned response without raising error
        3. has error but directly return a response
            3.1 data can be int
            3.2 data can be string
    """

    def __parse_error_list(self, data):
        # data should be list
        error_codes = []
        if not isinstance(data, list):
            return error_codes
        for error in data:
            # error can be a dict or string
            if error == _('Authentication credentials were not provided.'):
                error_code = [(constants.AUTH_CREDENTIALS_NOT_FOUND, None)]
            elif error == _('Token has already expired'):
                error_code = [(constants.EXPIRED_TOKEN, None)]
            elif error == _('permission denied.'):
                error_code = [(constants.NOT_ALLOWED, None)]
            elif error == _('You do not have permission to perform this action.'):
                error_code = [(constants.NOT_ALLOWED, None)]
            elif isinstance(error, dict):
                error_code = self.__get_errors_dict(error)
            elif error.isnumeric():
                error_code = [(int(error), None)]
            elif isinstance(error, str):
                error_code = self.__get_error_from_string(None, error)
            else:  # not handled
                error_code = [(constants.NOT_OK_UNKNOWN, None)]
            error_codes.extend(error_code)
        return error_codes

    def __get_error_from_string(self, key, val):
        for item in constants.DRF_MESSAGES:
            if isinstance(val, list) and len(val) == 1:
                val = val[0]
            elif isinstance(val, str) and item[1] == val.lower():
                msg = item[1] if item[2] or key is None else key
                return [(item[0], msg)]
            elif isinstance(val, dict):
                key = list(val.keys())[0]
        # error is likely to be not specific
        return [(constants.FIELD_ERROR, key)]

    def __set_error_message(self, error_codes):
        msg = []
        code_set = set(error_codes)
        content = None
        for code in error_codes:
            status = code[0]
            try:
                code_msg = constants.ERROR_CODES.get(int(code[1]), None) or \
                    code[1]
            except (ValueError, TypeError):
                code_msg = code[1]
            const_msg = constants.ERROR_CODES.get(status, None)
            if code_msg and const_msg:
                msg.append(f'{const_msg}: {code_msg}')
            elif code_msg:
                msg.append(code_msg)
            elif const_msg:
                msg.append(const_msg)
            else:  # both are not found
                msg.append('Unknown error')
            try:
                if status == constants.AUTH_CREDENTIALS_NOT_FOUND:
                    return status, msg, content
            except:
                pass
        if len(code_set) > 1:
            status = constants.MULTIPLE_ERRORS
        return status, msg, content

    def __get_errors_dict(self, data):
        error_codes = []
        for key, val in data.items():
            if key == 'error' or key == 'error_code':
                error_codes.extend(self.__parse_error_list(val))
            elif isinstance(key, int):
                # val should be a string for additional msg
                error_codes.append((key, val))
            elif isinstance(key, str):  # case for drf validation errors
                error_codes.extend(self.__get_error_from_string(key, val))
        return error_codes

    def get_response_content(self, data, status_code):
        if 200 <= status_code < 300:
            # for success response, there still need to check partial success
            status = constants.ALL_OK
            msg = None
            content = data
        elif status_code in {400, 401, 404, 403, 405}:
            if isinstance(data, dict):
                error_codes = self.__get_errors_dict(data)
                status, msg, content = self.__set_error_message(error_codes)
            elif isinstance(data, str):  # eventually should be removed
                status = constants.NOT_OK
                msg = [data]
                content = None
            elif isinstance(data, int):  # directly returning of Response()
                status = data
                msg = [constants.ERROR_CODES.get(status, 'code not found')]
                content = None
        else:  # unknown error
            logger.error(data)
            status = constants.NOT_OK_UNKNOWN
            msg = constants.ERROR_CODES.get(status)
            content = None
        response_content = {'code': status,
                            'msg': msg,
                            'data': content}
        return response_content

    def render(self, data, accepted_media_type=None, render_context=None):
        status_code = render_context['response'].status_code
        # if status code is not 200, this means the request has failed,
        # process it with corresponding custom payload
        response_content = self.get_response_content(data, status_code)
        # always set the response object's status code to 200
        render_context['response'].status_code = 200
        return super().\
            render(response_content, accepted_media_type, render_context)
