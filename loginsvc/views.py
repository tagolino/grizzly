import hashlib
import logging
import random
import requests
import string

from django.conf import settings
from django.contrib.auth import authenticate
from django.core.cache import cache
from django.http import JsonResponse
from django.http.request import QueryDict
from django.urls import resolve
from django.utils import timezone
from django.utils.datastructures import MultiValueDictKeyError
from django.utils.translation import ugettext_lazy as _
from django.views.decorators.csrf import csrf_exempt
from oauth2_provider.models import AccessToken, Application, RefreshToken
from rest_framework.decorators import (api_view,
                                       permission_classes,
                                       renderer_classes,
                                       throttle_classes)
from rest_framework.throttling import AnonRateThrottle

from account.models import Staff
from grizzly.lib import constants
from grizzly.utils import (get_user_type,
                           GrizzlyRenderer)


logger = logging.getLogger(__name__)


def random_token_generator(length):
    seq = string.ascii_lowercase + string.digits

    return ''.join(random.choices(seq, k=length))


def generate_token(string_0, string_1):
    """
    @brief
        Returns a random string to serve as an Oauth AccessToken value
    """

    salt = random_token_generator(4)
    token = f'{string_0}.{string_1}.{salt}'

    return hashlib.md5(token.encode('utf-8')).hexdigest()


def generate_response(code, msg=None, data=None):
    response = {'code': code,
                'msg': msg,
                'data': data}

    return JsonResponse(response, status=200)


@csrf_exempt
def logout(request):
    """
    @brief
        Deletes Access Token upon user logout
    """

    if request.method != 'POST':
        return generate_response(constants.NOT_ALLOWED, _('Not Allowed'))

    access_token = (request.META.get('HTTP_AUTHORIZATION') or '').split(' ')
    if access_token and len(access_token) == 2 \
            and access_token[0] == 'Bearer':
        access_token = access_token[1]
    else:
        return generate_response(constants.NOT_OK, _('Request failed.'))

    token_obj = AccessToken.objects.filter(token=access_token).first()
    try:
        user = token_obj.user
        user_type = get_user_type(user)
        # deleting AccessToken will also delete RefreshToken
        token_obj.delete()

        if user_type == 'staff':
            staff = user.staff_user
            staff.is_logged_in = False
            staff.save()

        return generate_response(constants.ALL_OK)
    except Exception as exc:
        logger.error(exc)
        return generate_response(constants.NOT_OK, _('Request failed.'))


@api_view(['POST'])
@permission_classes([])
@csrf_exempt
def refresh_access_token(request):
    # Refresh the access token
    refresh_token = request.data.get('refresh_token') or \
        request.POST.get('refresh_token')

    refresh_token_obj = \
        RefreshToken.objects.filter(token=refresh_token).first()

    # Check whether if the refresh token exists
    if not refresh_token_obj:
        return generate_response(constants.NOT_OK,
                                 _('Please make sure you are logged in'))

    client_id = refresh_token_obj.application.client_id
    client_secret = refresh_token_obj.application.client_secret
    user_obj = refresh_token_obj.user

    if not user_obj.is_active:
        return generate_response(constants.NOT_ALLOWED,
                                 _('This account has been suspended'))

    url = f'{request.scheme}://{request.get_host()}/o/token/'

    data = {'grant_type': 'refresh_token',
            'client_id': client_id,
            'client_secret': client_secret,
            'refresh_token': refresh_token}

    headers = {'Content-Type': 'application/x-www-form-urlencoded'}
    new_access_tk = None
    new_refresh_tk = None
    try:
        response = requests.post(url, data=data, headers=headers)
        tokens = response.json()
        new_access_tk = tokens.get('access_token')
        new_refresh_tk = tokens.get('refresh_token')
    except Exception as exc:
        logger.error(exc)
        return generate_response(constants.NOT_OK, _('Refresh failed'))

    if response.status_code == 200 and new_access_tk and new_refresh_tk:
        expires_in = AccessToken.objects.filter(token=new_access_tk).\
            values('expires').first()
        if not expires_in:
            return generate_response(constants.NOT_OK, _('Refresh failed'))

        expires = timezone.localtime(expires_in['expires'])

        new_token = {
            'access_token': new_access_tk,
            'token_type': 'Bearer',
            'expires_in': expires.strftime('%Y-%m-%d %H:%M:%S'),
            'refresh_token': new_refresh_tk,
        }

        response = generate_response(constants.ALL_OK, data=new_token)
        response.set_cookie(key='access_token', value=new_access_tk)
        response.set_cookie(key='refresh_token', value=new_refresh_tk)
        return response

    return generate_response(constants.NOT_OK, _('Refresh failed'))


@api_view(['POST'])
@throttle_classes([AnonRateThrottle])
@permission_classes([])
@renderer_classes((GrizzlyRenderer,))
@csrf_exempt
def login(request):
    sessionid = request.COOKIES.get('sessionid')

    # create session if cannot find it in cookies or cache
    if not sessionid or cache.get(sessionid) is None:
        try:
            request.session.create()
            sessionid = request.session.session_key
            cache.set(sessionid, 0, 3600)  # 1 hour
        except Exception as e:
            logging.error(str(e))

    data = request.POST or QueryDict(request.body)  # to capture data in IE

    # verify username and password
    try:
        user = authenticate(username=data['username'],
                            password=data['password'])
    except MultiValueDictKeyError:
        return generate_response(constants.NOT_ALLOWED,
                                 _('Not Allowed Login'))


    # get user type (admin, staff, None)
    user_type = get_user_type(user)
    url_name = resolve(request.path).url_name

    # if user login to wrong website or username/password is invalid
    if url_name == 'dashboard_login' and user_type is None:
        msg = _('Invalid username or password')
        return set_auth(sessionid, msg)

    # otp required for staff and admin
    from django_otp.forms import OTPTokenForm
    otp_token = data.get('otp_token', None)
    if user_type is not None:
        if otp_token is None:
            msg = _('Please enter OTP Token')
            return set_auth(sessionid, msg)
        else:  # verify otp token
            totp_devices = user.totpdevice_set.filter(confirmed=True)
            otp_passed = False
            for d in totp_devices:
                if d.verify_token(otp_token):
                    otp_passed = True
                    break
            if not otp_passed:
                msg = _('Invalid OTP Token')
                return set_auth(sessionid, msg)

    # check if user account is active
    is_active = __get_status(user, user_type)

    if is_active:
        cache.delete(sessionid)

        token = create_token(user, user_type)
        # record login
        if user_type == 'staff':
            staff = user.staff_user
            staff.is_logged_in = True
            staff.last_logged_in = timezone.now()
            staff.save()
            # srlzr = StaffPermissionSerializer(staff.perms.all(), many=True)
            # token['perms'] = srlzr.data

        response = generate_response(constants.ALL_OK, data=token)
        response.set_cookie(key='access_token',
                            value=token['access_token'])
        response.set_cookie(key='refresh_token',
                            value=token['refresh_token'])
        response.set_cookie(key='auth_req', value='')

        return response
    else:
        return generate_response(constants.NOT_ALLOWED,
                                 _('This account has been suspended'))


def set_auth(sessionid, message):
    data = {
        'sessionid': sessionid,
    }

    cache.incr(sessionid)

    response = generate_response(constants.FIELD_ERROR,
                                 msg=message,
                                 data=data)

    response.set_cookie(key='sessionid', value=sessionid)

    return response


def create_token(user, user_type):
    """
    @brief
        A more flexible way of handling and creating Oauth AccessTokens
    """

    expire_seconds = settings.OAUTH2_PROVIDER['ACCESS_TOKEN_EXPIRE_SECONDS']
    scopes = settings.OAUTH2_PROVIDER['SCOPES']

    # Get application based on user role
    application = Application.objects.get(name='dashboard')

    # delete old tokens, if any
    AccessToken.objects.filter(user=user, application=application).delete()

    expires = timezone.localtime() + timezone.timedelta(seconds=2592000)

    user_token = generate_token(user.username,
                                user.date_joined.strftime('%Y-%m-%d %H:%M:%S'))

    access_token = AccessToken.objects.create(user=user,
                                              application=application,
                                              token=user_token,
                                              expires=expires,
                                              scope=scopes)

    refresh_token = RefreshToken.objects.create(user=user,
                                                application=application,
                                                token=user_token,
                                                access_token=access_token)

    token = {
        'access_token': access_token.token,
        'token_type': 'Bearer',
        'expires_in': expires.strftime('%Y-%m-%d %H:%M:%S'),
        'refresh_token': refresh_token.token,
        'type': user_type
    }

    return token


def __get_status(user, user_type):
    if user:
        if user_type == 'admin':
            return user.is_active
        else:
            staff = Staff.objects.filter(username=user).first()
            return staff and staff.status == 1

    return False


def force_logout(user):
    # Logout immediately
    token_obj = AccessToken.objects.filter(user=user).first()
    try:
        user = token_obj.user
        user_type = get_user_type(user)
        # deleting AccessToken will also delete RefreshToken
        token_obj.delete()
        if user_type == 'staff':
            staff = user.staff_user
            staff.is_logged_in = False
            staff.save()
        return generate_response(constants.ALL_OK)
    except:
        generate_response(constants.NOT_OK, _('Request failed.'))
