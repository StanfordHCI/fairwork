from fairwork_server.settings import *
import django_heroku
import dj_database_url
import os

DEBUG = True

SECURE_SSL_REDIRECT = True
CSRF_COOKIE_SECURE = True

ADMIN_NAME = os.environ['ADMIN_NAME']
ADMIN_EMAIL = os.environ['ADMIN_EMAIL']
ADMINS = [(os.environ['ADMIN_NAME'], os.environ['ADMIN_EMAIL']), ]

HOSTNAME = os.environ['HOSTNAME']

WORKER_IRB_TEMPLATE = os.environ['WORKER_IRB_TEMPLATE']
REQUESTER_IRB_TEMPLATE = os.environ['REQUESTER_IRB_TEMPLATE']

ALLOWED_HOSTS = ['0.0.0.0', '127.0.0.1', 'localhost', 'fairwork.herokuapp.com', 'fairwork.stanford.edu']

TIME_ZONE = 'America/Los_Angeles'

DATABASES['default'] =  dj_database_url.config()

SECRET_KEY = os.environ['SECRET_KEY']

EMAIL_HOST = 'smtp.sendgrid.net'
EMAIL_HOST_USER = os.environ['SENDGRID_USERNAME']
EMAIL_HOST_PASSWORD = os.environ['SENDGRID_PASSWORD']
EMAIL_PORT = 587
EMAIL_USE_TLS = True
DEFAULT_FROM_EMAIL = os.environ['ADMIN_EMAIL']
SERVER_EMAIL = os.environ['ADMIN_EMAIL']

django_heroku.settings(locals())


LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': os.getenv('DJANGO_LOG_LEVEL', 'ERROR'),
        },
    },
}
