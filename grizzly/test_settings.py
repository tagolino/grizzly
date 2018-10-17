SECRET_KEY = 'test'

# CACHES = {
#     'default': {
#         'BACKEND': 'redis_cache.RedisCache',
#         'LOCATION': 'redis://127.0.0.1:6379',
#         'OPTIONS': {
#             'DB': 1,
#         }
#     },
# }
# BROKER_URL = 'amqp://guest:guest@localhost:5672//'
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': 'postgres',
        'USER': 'postgres',
        'PASSWORD': 'postgres',
        'HOST': 'localhost',
        'PORT': '5432'
    }
}
