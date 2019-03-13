from fairwork_server.settings import *

DEBUG = True
SECRET_KEY = 'createarandomstringandputithere'
TIME_ZONE = 'America/Los_Angeles' # or your timezone

ALLOWED_HOSTS = []

EMAIL_HOST = 'smtp@gmail.com' # email server so you can send notifications from the platform, e.g., SendGrid
EMAIL_HOST_USER = 'stanford.hci.mturk@gmail.com' # username
EMAIL_HOST_PASSWORD = 'hc1pr1vat3' # password
EMAIL_PORT = 587
EMAIL_USE_TLS = True

ADMIN_NAME = "Fair Work Debug"
ADMIN_EMAIL = "youremailaddress@domain.com"
ADMINS = [(ADMIN_NAME, ADMIN_EMAIL), ]

WORKER_IRB_TEMPLATE = 'placeholder-irb-worker.html' # for your IRB agreement
REQUESTER_IRB_TEMPLATE = 'placeholder-irb-requester.html' # for your IRB agreement

HOSTNAME = 'https://fairwork.yourdomain.com'

# DATABASES = {
# 	# 'default': {
#     #     'ENGINE': 'django.db.backends.postgresql_psycopg2',
#     #     'NAME': 'd62chgbkskemfl',
#     #     'USER': 'mvbbtlmsbzmcux',
#     #     'PASSWORD': '53657128339b3d2cbdb0347b7908fac3375d52053d18d5c4ab2fc92866f3e14b',
#     #     'HOST': 'ec2-54-235-240-126.compute-1.amazonaws.com',
#     #     'PORT': '5432',
#     # }
# }

