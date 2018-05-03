from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from django.db.models import Avg

from timerjerk.models import HITType, HIT, Worker, Assignment

"""
Performs the payment audit on the task. Pseudocode:
- Get accepted assignments that don't have an audit yet. Relies on pullnotifications.py having processed the acceptance notification from SQS.

- Map from assignments to HITs, and get all HITs in that HITGroup that need auditing. Calculate effective rate for each assignment, then median those to get effective rate for each HIT. Take median across all HITs in the HITGroup that were submitted but not audited yet to determine effective rate for the group under consideration. (Could do this by HIT, but too much variation. Could also do across all HITs in the HITGroup, but if the requester improved the HIT, it will still remember all the old low payments and not reflect the new design, which seems bad.) If effective rate >= min rate, then mark it as OK. Otherwise...

- Group unaudited assignemnts by worker_id. calculate num_assignments_accepted * (min_rate - effective_rate) to figure out bonus amount

- Bonus worker on first assignment in the HITGroup (to avoid being spammy) and keep a record
"""

class Command(BaseCommand):
    help = 'Calculate effective rate for tasks and reimburse underpayment'

    def handle(self, *args, **options):
        # Gets all assignments that have been accepted but don't have an audit yet
        auditable = Assignment.objects.filter(status=Assignment.ACCEPTED).filter(assignmentaudit__isnull
=True)
        hit_type_query = HITType.objects.filter(hit__assignment__in=auditable).distinct()
        for hit_type in hit_type_query:
            # Get the HITs that need auditing
            hit_query = HIT.objects.filter(hit_type=hit_type)
            # Average the reports for all assignments in that HIT
            durations = hit_query.aggregate(Avg('assignment__assignmentduration__duration'))

            self.stdout.write(str(durations['assignment__assignmentduration__duration__avg']))

            # self.stdout.write('HIT Type: %s' % accepted.id)
            # try:
            #     AssignmentAudit.objects.get(assignment = accepted)
            # except ObjectDoesNotExist:
            #     print("Needs audit")
            #     __calculate_effective_rate(accepted)


        self.stdout.write(self.style.SUCCESS('Task paid %d' % 2))

    def __calculate_effective_rate(hit_type):
        return None
