from botohack_server.settings import *
import django_heroku
import dj_database_url
import os

DEBUG = False

SECURE_SSL_REDIRECT = True
CSRF_COOKIE_SECURE = True

ALLOWED_HOSTS = ['0.0.0.0', '127.0.0.1', 'localhost', 'mechanicaljerk.herokuapp.com']

TIME_ZONE = 'America/Los_Angeles'

DATABASES['default'] =  dj_database_url.config()

AWS_ACCESS_KEY_ID = os.environ['AWS_ACCESS_KEY_ID']
AWS_SECRET_ACCESS_KEY = os.environ['AWS_SECRET_ACCESS_KEY']
SQS_QUEUE = os.environ['SQS_QUEUE']
SQS_QUEUE_NAME = os.environ['SQS_QUEUE_NAME']
SQS_REGION_NAME = os.environ['SQS_REGION_NAME']
SECRET_KEY = os.environ['SECRET_KEY']

django_heroku.settings(locals())
