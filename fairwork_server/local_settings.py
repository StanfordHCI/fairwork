from fairwork_server.settings import *

DEBUG = True
SECRET_KEY = 'abc'
ADMINS = [("Fair Work (Debug)", "a@a.com"), ]
TIME_ZONE = 'America/Los_Angeles' # or your timezone

EMAIL_HOST = 'smtp.gmail.com' # email server so you can send notifications from the platform, e.g., SendGrid
EMAIL_HOST_USER = 'ghugh2018@gmail.com' # username
EMAIL_HOST_PASSWORD = 'Catmeow311' # password
EMAIL_PORT = 587
EMAIL_USE_TLS = True

ALLOWED_HOSTS = []

HOSTNAME = 'https://fairwork-dev.herokuapp.com'
