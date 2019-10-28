import os

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ.get('SECRET_KEY', 'secret_key')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = False

REDIS_HOST = os.environ.get('REDIS_HOST', 'redis')
REDIS_CACHE_LOCATION = '{}://{}:6379'.format(REDIS_HOST, REDIS_HOST)

# Database
# https://docs.djangoproject.com/en/1.11/ref/settings/#databases
if os.environ.get('DOCKERIZED'):  # To avoid error in makemigrations during build
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'HOST': os.environ.get('POSTGRES_SERVICE', 'postgres'),
            'NAME': os.environ.get('POSTGRES_DB', 'postgres'),
            'PASSWORD': os.environ.get('POSTGRES_PASSWORD', 'postgres'),
            'PORT': os.environ.get('POSTGRES_PORT', 5432),
            'USER': os.environ.get('POSTGRES_USER', 'postgres')
        }
    }

CACHES = {
    'default': {
        "BACKEND": 'django_redis.cache.RedisCache',
        'LOCATION': REDIS_CACHE_LOCATION,
        'TIMEOUT': 259200,
        'OPTIONS': {
            'COMPRESSOR': 'django_redis.compressors.zlib.ZlibCompressor',
            'IGNORE_EXCEPTIONS': True,
        }
    },
}
