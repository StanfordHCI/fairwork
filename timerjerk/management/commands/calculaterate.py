from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from django.db.models import Q

from timerjerk.models import HITType, HIT, Worker, Assignment

"""
Performs the payment audit on the task. Pseudocode:
- Get accepted assignments that don't have an audit yet. Relies on pullnotifications.py having processed the acceptance notification from SQS.

- Map from assignments to HITs, and get all HITs in that HITGroup that need auditing. Calculate effective rate for each assignment, then median those to get effective rate for each HIT. Take median across all HITs in the HITGroup that were submitted but not audited yet to determine effective rate for the group under consideration. (Could do this by HIT, but too much variation.) If effective rate >= min rate, then mark it as OK. Otherwise...

- Group unaudited assignemnts by worker_id. calculate num_assignments_accepted * (min_rate - effective_rate) to figure out bonus amount

- Bonus worker on first assignment in the HITGroup (to avoid being spammy) and keep a record
"""

class Command(BaseCommand):
    help = 'Calculate effective rate for tasks and reimburse underpayment'

    def handle(self, *args, **options):
        query = Assignment.objects.filter(Q(status = Assignment.SUBMITTED) | Q(status = Assignment.ACCEPTED))
        for submitted in query:
            self.stdout.write('Assignment: %s' % submitted.id)


        self.stdout.write(self.style.SUCCESS('Task paid %d' % 2))
