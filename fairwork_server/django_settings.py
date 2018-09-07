from fairwork_server.settings import *
import django_heroku
import dj_database_url
import os

DEBUG = False

SECURE_SSL_REDIRECT = True
CSRF_COOKIE_SECURE = True

ADMINS = [(os.environ['ADMIN_NAME'], os.environ['ADMIN_EMAIL']), ]

ALLOWED_HOSTS = ['0.0.0.0', '127.0.0.1', 'localhost', 'fairwork.herokuapp.com']

TIME_ZONE = 'America/Los_Angeles'

DATABASES['default'] =  dj_database_url.config()

AWS_ACCESS_KEY_ID = os.environ['AWS_ACCESS_KEY_ID']
AWS_SECRET_ACCESS_KEY = os.environ['AWS_SECRET_ACCESS_KEY']
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
