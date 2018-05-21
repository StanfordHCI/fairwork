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

## Auditing HIT payment
```shell
python manage.py pullnotifications --settings=fairwork_server.local_settings

python manage.py auditpayments --settings=fairwork_server.local_settings
```
