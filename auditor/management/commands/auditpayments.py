from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from django.db.models import Avg, Sum, F
from django.core.mail import send_mail
from django.utils import timezone
from django.template.defaultfilters import pluralize
from django.core.signing import Signer
from django.urls import reverse


from statistics import median
import decimal
from decimal import Decimal
import math
import itertools
from datetime import timedelta

import boto3

from auditor.models import HITType, HIT, Worker, Assignment, AssignmentDuration, AssignmentAudit, Requester, RequesterFreeze
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
        for is_sandbox in [True, False]:
            self.stdout.write(self.style.WARNING('Sandbox mode: %s' % is_sandbox))
            self.__audit_hits(is_sandbox)
            self.__notify_requesters(is_sandbox)


    def __audit_hits(self, is_sandbox):
        # Gets all assignments that have been accepted but don't have an audit yet

        frozen_workers = set(())

        for freeze_object in RequesterFreeze.objects.all():
            frozen_workers.add(freeze_object.worker_id)

        current_audit_assignment_ids = []
        paid_audits = []

        for assignmentaudit in AssignmentAudit.objects.all():
            current_audit_assignment_ids.append(assignmentaudit.assignment_id)

        for assignmentaudit in AssignmentAudit.objects.filter(status=AssignmentAudit.PAID):
            paid_audits.append(assignmentaudit.assignment_id)

        auditable = Assignment.objects.filter(status=Assignment.APPROVED).exclude(id__in=paid_audits).distinct()
        print("auditable")
        print(auditable)

        if is_sandbox:
            auditable = auditable.filter(hit__hit_type__host__contains = 'sandbox')
        else:
            auditable = auditable.exclude(hit__hit_type__host__contains = 'sandbox')

        hit_type_query = HITType.objects.filter(hit__assignment__in=auditable).distinct()
        print(hit_type_query)

        for hit_type in hit_type_query:
            # Get the HITs that need auditing
            hit_query = HIT.objects.filter(hit_type=hit_type).filter(assignment__in = auditable).distinct()
            print(hit_query)

            hit_durations = list()
            for hit in hit_query:
                duration_query = AssignmentDuration.objects.filter(assignment__hit = hit).exclude(assignment__worker__in=frozen_workers).distinct()
                print("duration query")
                print(duration_query)
                # Take the median report for all assignments in that HIT
                # duration query can be empty if all of the people who submitted this assignment are now frozen
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
                    # first check if there is already assignmentaudit for assignmentid
                    if assignment.id in current_audit_assignment_ids:
                        assignmentaudit = AssignmentAudit.objects.get(assignment_id = assignment.id)
                        assignmentaudit.estimated_time = estimated_time
                        assignmentaudit.estimated_rate = estimated_rate
                        assignmentaudit.message_sent = None
                        assignmentaudit.full_clean()
                        assignmentaudit.save()
                    else:
                        audit = AssignmentAudit(assignment = assignment, estimated_time = estimated_time, estimated_rate = estimated_rate, status = AssignmentAudit.UNPAID)
                        if not audit.is_underpaid():
                            audit.status = AssignmentAudit.NO_PAYMENT_NEEDED
                        audit.full_clean()
                        audit.save()

    def __notify_requesters(self, is_sandbox):
        audits = AssignmentAudit.objects.filter(message_sent = None)
        if is_sandbox:
            audits = audits.filter(assignment__hit__hit_type__host__contains = 'sandbox')
        else:
            audits = audits.exclude(assignment__hit__hit_type__host__contains = 'sandbox')


        requesters = Requester.objects.filter(hittype__hit__assignment__assignmentaudit__in = audits).distinct()
        print("requesters: ")
        print(requesters)
        for requester in requesters:
            requester_audit = audits.filter(assignment__hit__hit_type__requester = requester).order_by('assignment__hit', 'assignment__hit__hit_type', 'assignment__worker')
            self.__notify_requester(requester, requester_audit, is_sandbox)

    def __notify_requester(self, requester, requester_audit, is_sandbox):
        email = requester.email
        self.stdout.write(email)
        plain_message = audit_list_message(requester_audit, requester, False, False, is_sandbox)
        html_message = audit_list_message(requester_audit, requester, False, True, is_sandbox)
        self.stdout.write(plain_message)

        if is_sandbox:
            subject = "Fair Work Sandbox: "
        else:
            subject = "Fair Work: "
        subject += "Mechanical Turk bonuses pending for $%.2f" % get_underpayment(requester_audit)
        send_mail(subject, plain_message, admin_email_address(), [email], fail_silently=False, html_message=html_message)

        sent_time = timezone.now()
        for audit in requester_audit:
            audit.message_sent = sent_time
            audit.save()


# Expose these methods publicly
REQUESTER_GRACE_PERIOD = timedelta(hours = 0) if settings.DEBUG else timedelta(hours = 12)

def audit_list_message(assignments_to_bonus, requester, is_worker, is_html, is_sandbox):
    print(assignments_to_bonus)
    total_unpaid = get_underpayment(assignments_to_bonus)
    signer = Signer(salt=get_salt())

    message = ""

    if is_sandbox:
        message += "<p>" if is_html else ""
        message += "This message represents work that was done in the Amazon Mechanical Turk sandbox, not the live site."
        message += "</p>" if is_html else "\n\n"

    message += "<p>" if is_html else ""

    if is_worker:
        message += "This requester is "
    else:
        message += "You are "
    message += "using the <a href='%s'>Fair Work script</a> " % settings.HOSTNAME if is_html else "using the Fair Work script (%s) " % settings.HOSTNAME
    message += "to ensure pay rates reach a minimum wage of $%.2f/hr. The goal of fair pay is outlined in the Turker-authored " % (settings.MINIMUM_WAGE_PER_HOUR)
    message += "<a href='http://guidelines.wearedynamo.org/'>We Are Dynamo guidelines</a>. " if is_html else "We Are Dynamo guidelines: http://guidelines.wearedynamo.org/. "
    message += "Fair Work does this by asking for completion times and then auto-bonusing workers to meet the desired hourly wage of $%.2f/hr." % (settings.MINIMUM_WAGE_PER_HOUR)
    message += "</p>" if is_html else "\n\n"

    if not is_worker:
        message += "<p>" if is_html else ""
        message += "Bonuses will be sent in %d hours: %s. You can review the pending bonuses below and freeze bonuses if something looks unusual. Please remember to trust the workers' estimates, and only freeze bonuses if absolutely needed." % (REQUESTER_GRACE_PERIOD.total_seconds() / (60*60), timezone.localtime(timezone.now() + REQUESTER_GRACE_PERIOD).strftime("%B %d at %-I:%M%p %Z"))
        message += "</p>" if is_html else "\n\n"

    message += "<p>" if is_html else ""
    message += "The total bonus amount is $%.2f. The tasks being bonused:" % total_unpaid
    message += "</p><ul>" if is_html else "\n\n"

    hit_types = HITType.objects.filter(hit__assignment__assignmentaudit__in = assignments_to_bonus).distinct()
    print("hit types")
    print(hit_types)
    for hit_type in hit_types:
        hittype_assignments = assignments_to_bonus.filter(assignment__hit__hit_type = hit_type)
        print("hit type assignments")
        print(hittype_assignments)
        hits = HIT.objects.filter(assignment__assignmentaudit__in = hittype_assignments).distinct()
        workers = Worker.objects.filter(assignment__assignmentaudit__in = hittype_assignments).distinct()

        s = "<li>" if is_html else ""

        underpayment = hittype_assignments[0].get_underpayment()
        time_nomicroseconds = str(hittype_assignments[0].estimated_time).split(".")[0]
        if underpayment is None:
            summary = "HIT Type {hittype:s} originally paid ${payment:.2f} per task. No workers reported time elapsed for this HIT, so effective rate cannot be estimated. No bonuses will be sent.".format(hittype = hit_type.id, payment = hit_type.payment)
        elif underpayment <= Decimal('0.00'):
            summary = "HIT Type {hittype:s} originally paid ${payment:.2f} per task. Median estimated time across {num_workers:d} worker{workers_plural:s} was {estimated:s}, for an estimated rate of ${paymentrate:.2f}/hr. No bonus necessary.".format(hittype = hit_type.id, payment = hit_type.payment, estimated = time_nomicroseconds, paymentrate = hittype_assignments[0].estimated_rate, num_workers=len(workers), workers_plural=pluralize(len(workers)))
        else:
            paymentrevised = hit_type.payment + hittype_assignments[0].get_underpayment()
            bonus = underpayment.quantize(Decimal('1.000')).normalize() if underpayment >= Decimal(0.01) else underpayment.quantize(Decimal('1.000'))
            paymentrevised = paymentrevised.quantize(Decimal('1.000')).normalize() if paymentrevised >= Decimal(0.01) else paymentrevised.quantize(Decimal('1.000'))

            summary = "HIT Type {hittype:s} originally paid ${payment:.2f} per task. Median estimated time across {num_workers:d} worker{workers_plural:s} was {estimated:s}, for an estimated rate of ${paymentrate:.2f}/hr. Bonus ${bonus:f} for each of {num_assignments:d} assignment{assignment_plural:s} in {num_hits:d} HIT{hits_plural:s} to bring the payment to a suggested ${paymentrevised:f} each. Total: ${totalbonus:.2f} bonus.".format(hittype = hit_type.id, payment = hit_type.payment, estimated = time_nomicroseconds, paymentrate = hittype_assignments[0].estimated_rate, bonus = bonus, num_assignments = len(hittype_assignments), assignment_plural=pluralize(len(hittype_assignments)), num_hits=len(hits), hits_plural=pluralize(len(hits)), num_workers=len(workers), workers_plural=pluralize(len(workers)), paymentrevised = paymentrevised, totalbonus = get_underpayment(hittype_assignments))
        s += summary
        s += "<ul>" if is_html else "\n"

        for worker in workers:
            duration_query = AssignmentDuration.objects.filter(assignment__worker = worker).filter(assignment__hit__hit_type = hit_type).filter(assignment__assignmentaudit__in = assignments_to_bonus)
            print("duration query")
            print(duration_query)
            # find the worker's median report for this HITType
            # uh oh sometimes duration query is empty now...
            median_duration = median(duration_query.values_list('duration', flat=True))
            median_nomicroseconds = str(median_duration).split(".")[0]
            s += "<li>" if is_html else "\t"
            s += "Worker %s: " % worker.id
            s += "{num_reports:d} report{report_plural:s}, median duration {median_duration:s}. ".format(num_reports=len(duration_query), report_plural=pluralize(len(duration_query)), median_duration=median_nomicroseconds)
            if not is_worker:
                worker_signed = signer.sign(worker.id)
                freeze_url = settings.HOSTNAME + reverse('freeze', kwargs={'requester': requester.aws_account, 'worker_signed': worker_signed})

                if is_html:
                    s += "<a href='{freeze_url:s}'>Freeze this worker's payment</a>".format(freeze_url=freeze_url)
                else:
                    s += "Freeze this worker's payment: {freeze_url:s}".format(freeze_url=freeze_url)
            s += "</li>" if is_html else "\n"

        s += "</li>" if is_html else "\n\n"
        message += s
    return message

def is_worker_frozen(worker):
    for freeze_object in RequesterFreeze.objects.all():
        if freeze_object.worker == worker:
            return True;
    return False;

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

def get_salt():
    return 'WORKER FREEZE'
