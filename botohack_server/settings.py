"""
Django settings for botohack_server project.
"""

import os
from decimal import Decimal

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))



# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/2.0/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = '123456789'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = False

ALLOWED_HOSTS = ['0.0.0.0', 'localhost', 'mechanicaljerk.herokuapp.com']


# Application definition

INSTALLED_APPS = [
    'timerjerk.apps.TimerjerkConfig',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'corsheaders',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    # Simplified static file serving.
    # https://warehouse.python.org/project/whitenoise/
    'whitenoise.middleware.WhiteNoiseMiddleware'
]

CORS_ORIGIN_WHITELIST = (
    'workersandbox.mturkcontent.com',
    'mturkcontent.com',
    'workersandbox.mturk.com',
    'mturk.com',
    'localhost:8000',
    '127.0.0.1:8000'
)
CORS_ALLOW_CREDENTIALS = True

CSRF_TRUSTED_ORIGINS = [
    'workersandbox.mturkcontent.com',
    'mturkcontent.com',
    'workersandbox.mturk.com',
    'mturk.com',
    'localhost:8000',
    '127.0.0.1:8000'
]

ROOT_URLCONF = 'botohack_server.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
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

WSGI_APPLICATION = 'botohack_server.wsgi.application'


# Database
# https://docs.djangoproject.com/en/2.0/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(BASE_DIR, 'db.sqlite3'),
    }
}


# Password validation
# https://docs.djangoproject.com/en/2.0/ref/settings/#auth-password-validators

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
# https://docs.djangoproject.com/en/2.0/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'America/Los_Angeles'

USE_I18N = True

USE_L10N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/2.0/howto/static-files/

STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
ADMIN_MEDIA_PREFIX = '/static/admin/'
# Simplified static file serving.
# https://warehouse.python.org/project/whitenoise/
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# Extra places for collectstatic to find static files.
STATICFILES_DIRS = (
    os.path.join(BASE_DIR, 'static'),
)

# App-specific settings
MINIMUM_WAGE_PER_HOUR = Decimal(11.00)

AWS_ACCESS_KEY_ID = ''
AWS_SECRET_ACCESS_KEY = ''
USE_SANDBOX = True
if USE_SANDBOX:
    MTURK_ENDPOINT = 'https://mturk-requester-sandbox.us-east-1.amazonaws.com'
else:
    MTURK_ENDPOINT = 'https://mturk-requester.us-east-1.amazonaws.com'
SQS_QUEUE = ''
SQS_QUEUE_NAME = ''
SQS_REGION_NAME = ''


# Activate Django-Heroku.
#django_heroku.settings(locals())
