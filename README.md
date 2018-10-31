# Fair Work server
You can run this server independently if you'd like to maintain data privacy for the Fair Work script.

Make sure to edit settings, typically by creating a local_settings.py and importing `settings`. A sample starter might include:
```python
from fairwork_server.settings import *

DEBUG = True
SECRET_KEY = 'createarandomstringandputithere'
ADMINS = [("Fair Work (Debug)", "youremailaddress@domain.com"), ]
TIME_ZONE = 'America/Los_Angeles' # or your timezone

ALLOWED_HOSTS = ['127.0.0.1']

EMAIL_HOST = '' # email server so you can send notifications from the platform, e.g., SendGrid
EMAIL_HOST_USER = '' # username
EMAIL_HOST_PASSWORD = '' # password
EMAIL_PORT = 587
EMAIL_USE_TLS = True

```

## Starting the server
```shell
python manage.py runserver --settings=fairwork_server.local_settings
```

Or using localhost HTTPS, assuming that you've already generated a self-signed .crt and .key file (here, localhost.crt and localhost.key):
```shell
python manage.py runsslserver --settings=fairwork_server.local_settings --certificate ../localhost.crt --key ../localhost.key
```

## Auditing HIT payment
Collect completed HITs --- run this hourly:
```shell
python manage.py pullnotifications --settings=fairwork_server.local_settings
```

Bonus any underpaid HITs to bring them up to minimum wage --- run this daily:
```shell
python manage.py auditpayments --settings=fairwork_server.local_settings
```
