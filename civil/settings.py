"""
Django settings for civil project.

Generated by 'django-admin startproject' using Django 2.1.7.

For more information on this file, see
https://docs.djangoproject.com/en/2.1/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/2.1/ref/settings/
"""
import locale
import os
from celery.schedules import crontab




# Build paths inside the project like this: os.path.join(BASE_DIR, ...)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/2.1/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'e4(^948$d-9)r)c)ofo$v%$h^=fgxx50&(c91)tm))p2ik%#rr'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True



ALLOWED_HOSTS = ['localhost','127.0.0.1','185.211.57.73','dna-h.ir']

AUTH_USER_MODEL = 'meeting.Peoples'

# Application definition

INSTALLED_APPS = (
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django_jalali',
    'jdatetime',
    'rest_framework',
    'rest_framework.authtoken',
    'drfpasswordless',
    'bootstrap4',
    'debug_toolbar',
    'celery',
    'django_celery_results',
    # 'django_celery_beat',
    'redis',
    'constance',
    'multiselectfield',
    'celery_sandbox',
    'django_filters',
    'meeting',
    'mptt',
    'api',
    # 'rangefilter',

)

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'debug_toolbar.middleware.DebugToolbarMiddleware',

]

ROOT_URLCONF = 'civil.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'templates')]
        ,
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'civil.wsgi.application'


# Database
# https://docs.djangoproject.com/en/2.1/ref/settings/#databases

# sudo -u postgres psql ---- for connect to db

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'civildb',
        'USER': 'postgres',
        'PASSWORD': 'zaq1@wsx',
        'HOST': 'localhost',
        'PORT': '5432',
    }
}


# Password validation
# https://docs.djangoproject.com/en/2.1/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
# https://docs.djangoproject.com/en/2.1/topics/i18n/

LANGUAGE_CODE = 'fa-ir'
locale.setlocale(locale.LC_ALL, "fa_IR")

TIME_ZONE = 'Asia/Tehran'

USE_I18N = True

USE_L10N = True

# USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/2.1/howto/static-files/

STATIC_URL = '/static/'
# STATIC_ROOT = os.path.join(BASE_DIR,'static/')
STATICFILES_DIRS = (os.path.join('static'), )


REST_FRAMEWORK = {
    # Use Django's standard `django.contrib.auth` permissions,
    # or allow read-only access for unauthenticated users.
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.LimitOffsetPagination',
    'PAGE_SIZE': 10,
    'DEFAULT_FILTER_BACKENDS': ('django_filters.rest_framework.DjangoFilterBackend',),
    # 'DEFAULT_PERMISSION_CLASSES': [
    #     # 'rest_framework.permissions.IsAuthenticated',
    #     'rest_framework.permissions.DjangoModelPermissionsOrAnonReadOnly',
    # ],
    'DEFAULT_AUTHENTICATION_CLASSES':
        ('rest_framework.authentication.BasicAuthentication',
         'rest_framework.authentication.SessionAuthentication',
         'rest_framework.authentication.TokenAuthentication',)
}

PASSWORDLESS_AUTH = {
    'PASSWORDLESS_AUTH_TYPES': ['MOBILE'],
    'PASSWORDLESS_USER_MOBILE_FIELD_NAME': 'mobile',
    'PASSWORDLESS_TOKEN_EXPIRE_TIME': 2 * 60,
    'PASSWORDLESS_USER_MARK_MOBILE_VERIFIED': True,
    'PASSWORDLESS_REGISTER_NEW_USERS': True,
    'PASSWORDLESS_TEST_SUPPRESSION': False
}


SMS_IR = {
    'SECRET_KEY': 'bigblackb3@r',
    'USER_API_KEY': '8cd5d8a0dd31254b5ce1e32d',
    'TOKEN_KEY_URL': 'http://RestfulSms.com/api/Token/',
    'ACTIVE_TOKEN_KEY': 'K2tjYjVmZEdLeVhyRlRxbUUvQ0o0YUM5b3JyQ0tNWmV0SDJYUjM2eEpSVDhiVlVCalRTQWtiSVlsMm4rTFA5SktkRUtwZW53MXgvRnhadlI0VHVqbkpoU1hPWDM1bm9MaGEyUGRyUmlYdnRhNkhGVTBSbVhOWWVqMHA4eW9MT05jcllOR2lRZDlqQ3kvQUc4Y080Z1BkTUdxWWg3RitrWmFtU1N5MHFiY2ordVAwd0dJQy9sNUE5eDlZbnlIcVhJ',
    'VERIFICATION_URL': 'http://RestfulSms.com/api/VerificationCode',
    'FAST_SEND_URL': 'http://RestfulSms.com/api/UltraFastSend',
}


CONSTANCE_BACKEND = 'constance.backends.redisd.RedisBackend'

CONSTANCE_CONFIG_FIELDSETS = {
    'SMS_IR': ('ACTIVE_TOKEN_KEY',
               'LAST_UPDATE',
               ),
}

CONSTANCE_CONFIG = {
    'ACTIVE_TOKEN_KEY': ('None',
                         'Active SMS.ir token key. Refreshed every 30 minutes.'),
    'LAST_UPDATE': ('None',
                    'Last token key update timestamp'),
}

CONSTANCE_REDIS_CONNECTION = {
    'host': 'localhost',
    'port': 6379,
    'db': 0,
}



INTERNAL_IPS = ['127.0.0.1']

# REDIS related settings
REDIS_HOST = 'localhost'
REDIS_PORT = '6379'
BROKER_URL = 'redis://' + REDIS_HOST + ':' + REDIS_PORT + '/0'
BROKER_TRANSPORT_OPTIONS = {'visibility_timeout': 3600}
CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": "redis://" + REDIS_HOST + ':' + REDIS_PORT + "/1",
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient"
        },
        "KEY_PREFIX": "civil"
    }
}

# celery flower -A civil --address=127.0.0.1 --port=8000
# celery -A civil worker -l info
# celery -A civil worker -l debug
# Celery settings

# CELERY_BROKER_URL = 'redis://' + REDIS_HOST + ':' + REDIS_PORT + '/0'
# CELERY_RESULT_BACKEND = 'redis://' + REDIS_HOST + ':' + REDIS_PORT + '/0'
CELERY_BROKER_URL = 'redis://' + REDIS_HOST + ':' + REDIS_PORT
CELERY_RESULT_BACKEND = 'redis://' + REDIS_HOST + ':' + REDIS_PORT
CELERY_ACCEPT_CONTENT = ['application/json']
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TASK_SERIALIZER = 'json'
CELERY_TIMEZONE = 'Asia/Tehran'

CELERY_BEAT_SCHEDULE = {
    'refresh-sms-token-every-30-minutes': {
        'task': 'drfpasswordless.tasks.refresh_sms_token',
        'schedule': crontab(minute ='*/15')  # refresh every 20 minutes
    },

}
CELERY_IMPORTS = ['drfpasswordless']

CELERY_RESULT_BACKEND = 'django-db'
CELERY_CACHE_BACKEND = 'django-cache'