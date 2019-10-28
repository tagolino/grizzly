import os
import json
from google.oauth2 import service_account

# STATICFILES_STORAGE = 'storages.backends.gcloud.GoogleCloudStorage'  # static
STATICFILES_STORAGE = 'grizzly.lib.storages.GoogleStaticFilesStorage'  # static
DEFAULT_FILE_STORAGE = 'grizzly.lib.storages.GoogleMediaFilesStorage'  # media
GS_AUTO_CREATE_BUCKET = True
GS_DEFAULT_ACL = 'publicRead'
GS_CREDENTIALS = service_account.Credentials.from_service_account_file(
    '/usr/src/app/storage-buckets-key.json'
)

with open('/usr/src/app/secrets.json') as data_file:  # required in cloud
    data = json.load(data_file)
    GS_BUCKET_NAME = data['GS_BUCKET_NAME']
    # Database
    # https://docs.djangoproject.com/en/1.11/ref/settings/#databases
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'HOST': f'/cloudsql/{data["CLOUDSQL_HOST"]}',
            'NAME': data['CLOUDSQL_NAME'],
            'PASSWORD': data['CLOUDSQL_PASSWORD'],
            'PORT': 5432,
            'USER': data['CLOUDSQL_USER'],
        }
    }

with open('/usr/src/app/django_email.json') as data_file:  # required for error notification
    data = json.load(data_file)
    EMAIL_HOST = data['EMAIL_HOST']
    EMAIL_HOST_USER = data['EMAIL_HOST_USER']
    SERVER_EMAIL = EMAIL_HOST_USER
    EMAIL_HOST_PASSWORD = data['EMAIL_HOST_PASSWORD']
    EMAIL_PORT = int(data['EMAIL_PORT'])
    EMAIL_USE_TLS = True
    DEFAULT_TO_EMAIL = data['DEFAULT_TO_EMAIL'].split(',')
    DEFAULT_DEBUG_EMAIL = os.environ.get('DEFAULT_DEBUG_EMAIL',
                                         'manila@unnotech.com')
    ADMINS = [('DEFAULT_DEBUG_EMAIL', DEFAULT_DEBUG_EMAIL)]
