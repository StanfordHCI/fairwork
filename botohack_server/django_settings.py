from botohack_server.settings import *
import django_heroku
import dj_database_url

DEBUG = False

ALLOWED_HOSTS = ['0.0.0.0', '127.0.0.1', 'localhost', 'mechanicaljerk.herokuapp.com']

TIME_ZONE = 'America/Los_Angeles'

USE_SANDBOX = False
if USE_SANDBOX:
    MTURK_ENDPOINT = 'https://mturk-requester-sandbox.us-east-1.amazonaws.com'
else:
    MTURK_ENDPOINT = 'https://mturk-requester.us-east-1.amazonaws.com'

DATABASES['default'] =  dj_database_url.config()

django_heroku.settings(locals())
