from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from django.db.models import Avg, Sum

from statistics import median
from decimal import Decimal

from timerjerk.models import HITType, HIT, Worker, Assignment, AssignmentDuration, AssignmentAudit

"""
Performs the payment audit on the task. Pseudocode:
- Get accepted assignments that don't have an audit yet. Relies on pullnotifications.py having processed the acceptance notification from SQS.

- Map from assignments to HITs, and get all HITs in that HITGroup that need auditing. Calculate effective rate for each assignment, then median those to get effective rate for each HIT. Take median across all HITs in the HITGroup that were accepted but not audited yet to determine effective rate for the group under consideration. (Could do this by HIT, but too much variation. Could also do across all HITs in the HITGroup, but if the requester improved the HIT, it will still remember all the old low payments and not reflect the new design, which seems bad.) If effective rate >= min rate, then mark it as OK. Otherwise...

- Group unaudited assignemnts by worker_id. calculate num_assignments_accepted * (min_rate - estimated_rate) to figure out bonus amount

- Bonus worker on first assignment in the HITGroup (to avoid being spammy) and keep a record
"""

class Command(BaseCommand):
    help = 'Calculate effective rate for tasks and reimburse underpayment'

    def handle(self, *args, **options):
        self.__audit_hits()
        self.__pay_audited_hits()
        # TODO: add payment logging to server, so we get it in the models


    def __audit_hits(self):
        # Gets all assignments that have been accepted but don't have an audit yet
        auditable = Assignment.objects.filter(status=Assignment.ACCEPTED).filter(assignmentaudit__isnull
    =True)
        hit_type_query = HITType.objects.filter(hit__assignment__in=auditable).distinct()
        for hit_type in hit_type_query:
            self.stdout.write(self.style.NOTICE('HIT Type %s' % hit_type))
            # Get the HITs that need auditing
            hit_query = HIT.objects.filter(hit_type=hit_type).filter(assignment__in = auditable)

            hit_durations = list()
            for hit in hit_query:
                self.stdout.write(self.style.SUCCESS('HIT %s' % hit))
                duration_query = AssignmentDuration.objects.filter(assignment__hit = hit)

                self.stdout.write('%s' % duration_query)

                # Take the median report for all assignments in that HIT
                if len(duration_query) > 0:
                    median_duration = median(duration_query.values_list('duration', flat=True))
                    self.stdout.write(str(median_duration))
                    hit_durations.append(median_duration)

            # now, hit_durations contains the median reported time for each HIT
            # that has at least one assignment needing an audit.
            # next step: take the median of the medians across these HITs to
            # calculate the overall effective time
            if len(hit_durations) == 0:
                # nobody reported anything
                status = AssignmentAudit.NO_PAYMENT_NEEDED
                estimated_time = None
                estimated_rate = None
            else:
                estimated_time = median(hit_durations)
                estimated_rate = hit_type.payment / Decimal(estimated_time.total_seconds() / (60*60))

            hit_assignments = auditable.filter(hit__in = hit_query)
            for assignment in hit_assignments:
                audit = AssignmentAudit(assignment = assignment, estimated_time = estimated_time, estimated_rate = estimated_rate, status = AssignmentAudit.UNPAID)
                if not audit.is_underpaid():
                    audit.status = AssignmentAudit.NO_PAYMENT_NEEDED
                audit.save()
                self.stdout.write(self.style.WARNING(audit))


    def __pay_audited_hits(self):
        to_pay = AssignmentAudit.objects.filter(status = AssignmentAudit.UNPAID).values('assignment__worker').aggregate(Sum('underpayment'))
        print(to_pay)

            # TODO: best to group by worker first, and sum up per worker per hit type, so you can bonus just once
