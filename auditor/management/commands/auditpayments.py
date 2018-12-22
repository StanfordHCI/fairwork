from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from django.db.models import Avg, Sum, F
from django.core.mail import send_mail
from django.utils import timezone

from statistics import median
import decimal
from decimal import Decimal
import math
import itertools
from datetime import timedelta

import boto3

from auditor.models import HITType, HIT, Worker, Assignment, AssignmentDuration, AssignmentAudit, Requester
from auditor.management.commands.pullnotifications import get_mturk_connection

"""
Performs the payment audit on the task. Pseudocode:
- Get accepted assignments that don't have an audit yet. Relies on pullnotifications.py having processed accepted HITs.

- Map from assignments to HITs, and get all HITs in that HITGroup that need auditing. Calculate effective rate for each assignment, then median those to get effective rate for each HIT. Take median across all HITs in the HITGroup that were accepted but not audited yet to determine effective rate for the group under consideration. (Could do this by HIT, but too much variation. Could also do across all HITs in the HITGroup, but if the requester improved the HIT, it will still remember all the old low payments and not reflect the new design, which seems bad.) If effective rate >= min rate, then mark it as OK. Otherwise...

- Group unaudited assignemnts by worker_id. calculate num_assignments_accepted * (min_rate - estimated_rate) to figure out bonus amount

- Bonus worker on first assignment in the HITGroup (to avoid being spammy) and keep a record
"""

class Command(BaseCommand):
    help = 'Calculate effective rate for tasks and audit any underpayment'

    mturk = dict() # maintains the Boto client connections

    def handle(self, *args, **options):
        self.__audit_hits()
        self.__notify_requesters()


    def __audit_hits(self):
        # Gets all assignments that have been accepted but don't have an audit yet
        auditable = Assignment.objects.filter(status=Assignment.APPROVED).filter(assignmentaudit__isnull
    =True)
        hit_type_query = HITType.objects.filter(hit__assignment__in=auditable).distinct()
        for hit_type in hit_type_query:

            # Get the HITs that need auditing
            hit_query = HIT.objects.filter(hit_type=hit_type).filter(assignment__in = auditable)

            hit_durations = list()
            for hit in hit_query:
                duration_query = AssignmentDuration.objects.filter(assignment__hit = hit)

                # Take the median report for all assignments in that HIT
                if len(duration_query) > 0:
                    median_duration = median(duration_query.values_list('duration', flat=True))
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
                estimated_rate = Decimal(hit_type.payment / Decimal(estimated_time.total_seconds() / (60*60))).quantize(Decimal('.01'))
                if estimated_rate == 0:
                    estimated_rate = Decimal('0.01') # minimum accepted Decimal value, $0.01 per hour

            hit_assignments = auditable.filter(hit__in = hit_query)
            for assignment in hit_assignments:
                audit = AssignmentAudit(assignment = assignment, estimated_time = estimated_time, estimated_rate = estimated_rate, status = AssignmentAudit.UNPAID)
                if not audit.is_underpaid():
                    audit.status = AssignmentAudit.NO_PAYMENT_NEEDED
                audit.full_clean()
                audit.save()

            return auditable

    def __notify_requesters(self):
        audits = AssignmentAudit.objects.filter(message_sent = None)
        requesters = Requester.objects.filter(hittype__hit__assignment__assignmentaudit__in = audits).distinct()
        for requester in requesters:
            requester_audit = audits.filter(assignment__hit__hit_type__requester = requester).order_by('assignment__hit', 'assignment__hit__hit_type', 'assignment__worker')
            self.__notify_requester(requester, requester_audit)

    def __notify_requester(self, requester, requester_audit):
        email = requester.email
        self.stdout.write(email)
        plain_message = audit_list_message(requester_audit, False, False)
        html_message = audit_list_message(requester_audit, False, True)
        self.stdout.write(plain_message)

        subject = "Fair Work: Mechanical Turk bonuses pending for $%.2f" % get_underpayment(requester_audit)
        send_mail(subject, plain_message, admin_email_address(), [email], fail_silently=False, html_message=html_message)

        sent_time = timezone.now()
        for audit in requester_audit:
            audit.message_sent = sent_time
            audit.save()


# Expose these methods publicly
REQUESTER_GRACE_PERIOD = timedelta(hours = 0) if settings.DEBUG else timedelta(hours = 12)

def audit_list_message(assignments_to_bonus, is_worker, is_html):
    total_unpaid = get_underpayment(assignments_to_bonus)
    message = ""

    message += "<p>" if is_html else ""

    if is_worker:
        message = "This requester is "
    else:
        message = "You are "
    message += "using the Fair Work script to ensure pay rates reach a minimum wage of $%.2f/hr. The goal of fair pay is outlined in the Turker-authored We Are Dynamo guidelines: http://guidelines.wearedynamo.org/. Fair Work does this by asking for completion times and then auto-bonusing workers to meet the desired hourly wage of $%.2f/hr." % (settings.MINIMUM_WAGE_PER_HOUR, settings.MINIMUM_WAGE_PER_HOUR)
    message += "</p>" if is_html else "\n\n"

    if not is_worker:
        message += "<p>" if is_html else ""
        message += "Bonuses will be sent in %d hours: %s. You can review the pending bonuses below and freeze bonuses if something looks unusual. Please remember to trust the workers' estimates, and only freeze bonuses if absolutely needed." % (REQUESTER_GRACE_PERIOD.total_seconds() / (60*60), timezone.localtime(timezone.now() + REQUESTER_GRACE_PERIOD).strftime("%B %d at %-I:%M%p %Z"))
        message += "</p>" if is_html else "\n\n"

    message += "<p>" if is_html else ""
    message += "The total bonus amount is $%.2f. The tasks being bonused:" % total_unpaid
    message += "</p><ul>" if is_html else "\n\n"

    hit_types = HITType.objects.filter(hit__assignment__assignmentaudit__in = assignments_to_bonus).distinct()
    for hit_type in hit_types:
        hittype_assignments = assignments_to_bonus.filter(assignment__hit__hit_type = hit_type)
        s = "<li>" if is_html else ""

        underpayment = hittype_assignments[0].get_underpayment()
        time_nomicroseconds = str(hittype_assignments[0].estimated_time).split(".")[0]
        if underpayment is None:
            summary = "HIT Type {hittype:s} originally paid ${payment:.2f} per task. No workers reported time elapsed for this HIT, so effective rate cannot be estimated. No bonuses will be sent.".format(hittype = hit_type.id, payment = hit_type.payment)
        elif underpayment <= Decimal('0.00'):
            summary = "HIT Type {hittype:s} originally paid ${payment:.2f} per task. Median estimated time across workers was {estimated:s}, for an estimated rate of ${paymentrate:.2f}/hr. No bonus necessary.".format(hittype = hit_type.id, payment = hit_type.payment, estimated = time_nomicroseconds, paymentrate = hittype_assignments[0].estimated_rate)
        else:
            paymentrevised = hit_type.payment + hittype_assignments[0].get_underpayment()
            bonus = underpayment.quantize(Decimal('1.000')).normalize() if underpayment >= Decimal(0.01) else underpayment.quantize(Decimal('1.000'))
            paymentrevised = paymentrevised.quantize(Decimal('1.000')).normalize() if paymentrevised >= Decimal(0.01) else paymentrevised.quantize(Decimal('1.000'))

            summary = "HIT Type {hittype:s} originally paid ${payment:.2f} per task. Median estimated time across workers was {estimated:s}, for an estimated rate of ${paymentrate:.2f}/hr. Bonus ${bonus:f} for each of {num_assignments:d} assignments to bring the payment to a suggested ${paymentrevised:f} each. Total: ${totalbonus:.2f} bonus.".format(hittype = hit_type.id, payment = hit_type.payment, estimated = time_nomicroseconds, paymentrate = hittype_assignments[0].estimated_rate, bonus = bonus, num_assignments = len(hittype_assignments), paymentrevised = paymentrevised, totalbonus = get_underpayment(hittype_assignments))
            if not is_worker:
                summary += " [FREEZE LINK]"
        s += summary
        s += "<ul>" if is_html else "\n"

        hits = HIT.objects.filter(assignment__assignmentaudit__in = hittype_assignments).distinct()
        for hit in hits:
            s += "<li>" if is_html else "\t"
            s += "HIT %s: " % hit.id
            hit_assignments = hittype_assignments.filter(assignment__hit = hit)
            assignment_ids = [x.assignment.id for x in hit_assignments]
            if len(assignment_ids) == 1:
                s += "assignment %s" % ", ".join(assignment_ids)
            else:
                s += "assignments %s" % ", ".join(assignment_ids)
            s += "</li>" if is_html else "\n"
        s += "</li>" if is_html else "\n\n"
        message += s
    return message

def get_underpayment(assignments_to_bonus):
    total_unpaid = Decimal('0.00')
    for unpaid_task in assignments_to_bonus:
        underpayment = unpaid_task.get_underpayment()
        if underpayment is not None:
            total_unpaid += underpayment
    # don't shortchange workers --- round up to the nearest cent
    total_unpaid = math.ceil(total_unpaid * Decimal('100.0')) / Decimal('100.0')
    return total_unpaid

def admin_email_address():
    return "%s <%s>" % (settings.ADMINS[0][0], settings.ADMINS[0][1])
