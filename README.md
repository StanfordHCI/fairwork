# Fair Work server
You can run this server independently if you'd like to maintain data privacy for the Fair Work script.

Make sure to edit settings, typically by creating a local_settings.py and importing:
```python
from fairwork_server.settings import *
```

## Starting the server
```shell
python manage.py runserver --settings=fairwork_server.local_settings
```

Or using local SSH, assuming that you've already generated a .crt and .key file (here, localhost.crt and localhost.key):
```shell
python manage.py runsslserver --settings=fairwork_server.local_settings --cert
ificate ../localhost.crt --key ../localhost.key
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
