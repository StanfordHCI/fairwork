# mjerk-server
More ethical server

Make sure to edit settings, typically by creating a local_settings.py and importing:
```python
from botohack_server.settings import *
```

## Starting the server
```shell
python manage.py runserver
```

## Auditing HIT payment
```shell
python manage.py pullnotifications --settings=botohack_server.local_settings

python manage.py auditpayment --settings=botohack_server.local_settings
```
