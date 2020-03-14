# Fair Work server
You can run this server independently if you'd like to maintain data privacy for the Fair Work script.

Make sure to edit settings, typically by creating a local_settings.py and importing `settings`. A sample starter might include:
```python
from fairwork_server.settings import *

DEBUG = True
SECRET_KEY = 'createarandomstringandputithere'
TIME_ZONE = 'America/Los_Angeles' # or your timezone

ALLOWED_HOSTS = []

EMAIL_HOST = '' # email server so you can send notifications from the platform, e.g., SendGrid
EMAIL_HOST_USER = '' # username
EMAIL_HOST_PASSWORD = '' # password
EMAIL_PORT = 587
EMAIL_USE_TLS = True

ADMIN_NAME = "Fair Work Debug"
ADMIN_EMAIL = "youremailaddress@domain.com"
ADMINS = [(ADMIN_NAME, ADMIN_EMAIL), ]

WORKER_IRB_TEMPLATE = 'placeholder-irb-worker.html' # for your IRB agreement
REQUESTER_IRB_TEMPLATE = 'placeholder-irb-requester.html' # for your IRB agreement

HOSTNAME = 'https://fairwork.yourdomain.com' # used as the hostname in emails sent by the system, since Django management commands do not know the server's hostname

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

Check for underpayments and send requesters a notification of pending payments --- run this daily:
```shell
python manage.py auditpayments --settings=fairwork_server.local_settings
```

Send the payments to workers after requesters have had time to read the email --- run this daily, 12hr after the auditpayments command:
```shell
python manage.py payaudits --settings=fairwork_server.local_settings
```

## Citing Fair Work
[Download the paper here](https://hci.stanford.edu/publications/2019/fairwork/fairwork-hcomp2019.pdf), and cite this work as:

>Whiting, Mark E., Grant Hugh, and Michael S. Bernstein. "Fair Work: Crowd Work Minimum Wage with One Line of Code." Proceedings of the AAAI Conference on Human Computation and Crowdsourcing. Vol. 7. No. 1. 2019.

Or with BibTeX:
```BibTeX
@inproceedings{whiting2019fair,
  title={Fair Work: Crowd Work Minimum Wage with One Line of Code},
  author={Whiting, Mark E and Hugh, Grant and Bernstein, Michael S},
  booktitle={Proceedings of the AAAI Conference on Human Computation and Crowdsourcing},
  volume={7},
  number={1},
  pages={197--206},
  year={2019}
}
```
