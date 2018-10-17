from django.utils.translation import ugettext_lazy as _


# COMMON CODES
ALL_OK = 2000
EXPIRED_TOKEN = 9006
AUTH_CREDENTIALS_NOT_FOUND = 9007
NOT_OK_UNKNOWN = 9008
NOT_OK = 9009
MULTIPLE_ERRORS = 9010
FIELD_ERROR = 9011
REQUIRED_FIELD = 9012


# PERMISSION RELATED
NOT_ALLOWED = 7001


# ACCOUNT RELATED
USERNAME_IN_USED = 1004
INVALID_USERNAME = 1011


# MESSAGES from DRF
# (RESPONSE_CODE, SPECIFIC MESSAGE, Commonalised?)
DRF_MESSAGES = {
    (9011, _('staff with this username already exists.'), True),
    (9012, _('this field is required.'), False),
    (9012, _('this field is required'), False),
    (7001, _('permission denied.'), False),
    (7001, 'method "post" not allowed.', False),
    (7001, 'method "put" not allowed.', False),
    (7001, 'method "get" not allowed.', False)
}


# CORRESPONDING MESSAGES
REGISTRATION_OK = _('Registration successful')
ERROR_CODES = {
    1001: _('Member not found.'),
    1003: _('The format of the email is not correct'),
    1009: _('Passwords did not match'),
    1011: _('Username must consist of 6-15 alphanumeric characters'),
    2000: 'OK',
    7001: _('Not Allowed'),
    9008: _('Unknown error has occurred. Please contact support.'),
    9006: _('Token has already expired'),
    9007: _('Authentication credentials were not provided.'),
    9009: _('Request failed.'),
    9011: _('Invalid field value'),
    9012: _('This field is required'),
}
