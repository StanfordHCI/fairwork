"""
Django settings for fairwork_server project.
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

ALLOWED_HOSTS = ['0.0.0.0', 'localhost', 'fairwork.stanford.edu', 'fairwork.herokuapp.com', 'fairwork-dev.herokuapp.com']


# Application definition

INSTALLED_APPS = [
    'auditor.apps.AuditorConfig',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'corsheaders',
    'sslserver'
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
    '127.0.0.1:8000',
    'fairwork-dev.herokuapp.com'
)
CORS_ALLOW_CREDENTIALS = True

CSRF_TRUSTED_ORIGINS = [
    'workersandbox.mturkcontent.com',
    'mturkcontent.com',
    'workersandbox.mturk.com',
    'mturk.com',
    'localhost:8000',
    '127.0.0.1:8000',
    'fairwork-dev.herokuapp.com'
]

CORS_ORIGIN_ALLOW_ALL = True

ROOT_URLCONF = 'fairwork_server.urls'

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
                'fairwork_server.context_processor.fairwork_context_processor',
            ],
        },
    },
]

WSGI_APPLICATION = 'fairwork_server.wsgi.application'


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

EMAIL_HOST = 'smtp.gmail.com'
EMAIL_HOST_USER = 'stanford.hci.mturk@gmail.com'
EMAIL_HOST_PASSWORD = 'hc1pr1vat3'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_SUBJECT_PREFIX = "[Fair Work] "


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

MTURK_SANDBOX_ENDPOINT = 'https://mturk-requester-sandbox.us-east-1.amazonaws.com'
MTURK_ENDPOINT = 'https://mturk-requester.us-east-1.amazonaws.com'
MINIMUM_WAGE_PER_HOUR = Decimal(11.00) # CA minimum wage 2018

# Change these settings in your local settings file
WORKER_IRB_TEMPLATE = 'placeholder-irb-worker.html'
REQUESTER_IRB_TEMPLATE = 'placeholder-irb-requester.html'

ADMIN_NAME = "Your Admin Name"
ADMIN_EMAIL = "stanford.hci.mturk@gmail.com"
ADMINS = [(ADMIN_NAME, ADMIN_EMAIL), ]

HOSTNAME = 'https://fairwork-dev.herokuapp.com'
