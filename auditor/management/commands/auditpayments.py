from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from django.db.models import Avg, Sum, F
from django.core.mail import send_mail

from statistics import median
from decimal import Decimal
import itertools

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
    help = 'Calculate effective rate for tasks and bonus any underpayment'

    mturk = dict() # maintains the Boto client connections

    def handle(self, *args, **options):
        self.__audit_hits()
        self.__pay_audited_hits()


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



    def __pay_audited_hits(self):
        for is_sandbox in [True, False]:
            self.stdout.write(self.style.WARNING('Sandbox mode: %s' % is_sandbox))
            audits = AssignmentAudit.objects.filter(status = AssignmentAudit.UNPAID)
            if is_sandbox:
                audits = audits.filter(assignment__hit__hit_type__host__contains = 'sandbox')
            else:
                audits = audits.exclude(assignment__hit__hit_type__host__contains = 'sandbox')

            requesters = Requester.objects.filter(hittype__hit__assignment__assignmentaudit__in = audits).distinct()
            for requester in requesters:
                self.stdout.write(self.style.WARNING('Requester: %s %s' % (requester.aws_account, requester.email)))

                requester_to_bonus = audits.filter(assignment__hit__hit_type__requester = requester).order_by('assignment__hit', 'assignment__hit__hit_type', 'assignment__worker')

                self.__notify_requester(requester, requester_to_bonus)

                workers = Worker.objects.filter(assignment__assignmentaudit__in = requester_to_bonus).distinct()
                for worker in workers:
                    assignments_to_bonus = requester_to_bonus.filter(assignment__worker = worker).distinct()
                    self.__bonus_worker(worker, assignments_to_bonus, requester, is_sandbox)

    def __bonus_worker(self, worker, assignments_to_bonus, requester, is_sandbox):
        # How much do we owe them?
        self.stdout.write(self.style.WARNING('Worker: %s' % worker.id))
        total_unpaid = self.__get_underpayment(assignments_to_bonus)
        self.stdout.write(self.style.WARNING('Total bonus for %s: $%.2f\n---------' % (worker.id, total_unpaid)))

        # Send the bonus
        # Construct the message to the worker
        message = self.__audit_list_message(assignments_to_bonus, True, False)
        assignment_to_bonus = assignments_to_bonus[0] # Arbitrarily attach it to the first one
        token = '%s: %.2f' % (assignment_to_bonus.assignment.id, total_unpaid) # sending the same token prevents AMT from sending the same bonus twice

        mturk_clients = get_mturk_connection(requester, self.mturk)
        if is_sandbox:
            mturk_client = mturk_clients['sandbox']
        else:
            mturk_client = mturk_clients['production']

        try:
            response = mturk_client.send_bonus(WorkerId = worker.id, BonusAmount = '%.2f' % (total_unpaid), AssignmentId = assignment_to_bonus.assignment.id, Reason = message, UniqueRequestToken = token)

            # Once the bonus is sent, mark the audits as paid
            for unpaid_task in assignments_to_bonus:
                unpaid_task.status = AssignmentAudit.PAID
                unpaid_task.save()
        except mturk_client.exceptions.RequestError as e:
            if e.response['Error']['Message'].startswith("This Requester has insufficient funds in their account to complete this transaction."):
                self.stderr.write(self.style.ERROR("Requester does not have enough funds. Notifying worker."))
                self.__notify_insufficient_funds(requester, is_sandbox, worker, total_unpaid, assignment_to_bonus)
            else:
                self.stderr.write(self.style.ERROR(e))


    def __get_underpayment(self, assignments_to_bonus):
        total_unpaid = Decimal(0)
        for unpaid_task in assignments_to_bonus:
            total_unpaid += unpaid_task.get_underpayment()
        return total_unpaid

    def __audit_list_message(self, assignments_to_bonus, is_worker, is_html):
        total_unpaid = self.__get_underpayment(assignments_to_bonus)
        message = ""

        message += "<p>" if is_html else ""

        if is_worker:
            message = "This requester is "
        else:
            message = "You are "
        message += "using the Fair Work script to ensure pay rates reach a minimum wage of $%.2f/hr. The goal of fair pay is outlined in the Turker-authored We Are Dynamo guidelines: http://guidelines.wearedynamo.org/. Fair Work does this by asking for completion times and then auto-bonusing workers to meet the desired hourly wage. Based on worker time reports, some of your tasks have been underpaid. The Fair Work system is bonusing workers to bring payment back up to $%.2f/hr." % (settings.MINIMUM_WAGE_PER_HOUR, settings.MINIMUM_WAGE_PER_HOUR)
        message += "</p>" if is_html else "\n\n"

        message += "<p>" if is_html else ""
        message += "The total amount paid is $%.2f. The tasks being reimbursed:" % total_unpaid
        message += "</p><ul>" if is_html else "\n\n"

        hit_types = HITType.objects.filter(hit__assignment__assignmentaudit__in = assignments_to_bonus).distinct()
        for hit_type in hit_types:
            hittype_assignments = assignments_to_bonus.filter(assignment__hit__hit_type = hit_type)
            s = "<li>" if is_html else ""
            s += "HIT Type %s originally paid $%.2f per task. Median estimated time across workers was %s, for an estimated rate of $%.2f/hr. Bonus $%.2f for each of %d assignments to bring the payment to $%.2f each. Total: $%.2f bonus." % (hit_type.id, hit_type.payment, hittype_assignments[0].estimated_time, hittype_assignments[0].estimated_rate, hittype_assignments[0].get_underpayment(), len(hittype_assignments), (hit_type.payment + hittype_assignments[0].get_underpayment()),  sum([x.get_underpayment() for x in hittype_assignments]))
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

    def __notify_requester(self, requester, assignments_to_bonus):
        email = requester.email
        self.stdout.write(email)
        plain_message = self.__audit_list_message(assignments_to_bonus, False, False)
        html_message = self.__audit_list_message(assignments_to_bonus, False, True)
        self.stdout.write(plain_message)

        subject = "Fair Work: Mechanical Turk bonuses sent for $%.2f" % self.__get_underpayment(assignments_to_bonus)
        send_mail(subject, plain_message, 'fairwork@cs.stanford.edu', [email], fail_silently=False, html_message=html_message)


    def __notify_insufficient_funds(self, requester, is_sandbox, worker, total_unpaid, assignment_to_bonus):
        """
        Tells the worker to tell the requester to deposit more money.
        We don't have a way to directly notify the requester.
        """

        subject = "Fair Work bonus of $%.2f pending, but requester out of funds — please notify requester" % total_unpaid

        message = """This is an automated message from the Fair Work script: this requester is trying to bonus you, but they don't have enough funds in their account to send the bonus. Please reply and let them know that they need to deposit more funds.

This requester is using the Fair Work script to ensure pay rates reach a minimum wage of $%.2f/hr, as described in the Turker-authored We Are Dynamo guidelines: http://guidelines.wearedynamo.org/. Fair Work does this by asking for completion times and then auto-bonusing workers to meet the desired hourly wage. Based on worker time reports, your tasks have been underpaid. We are bonusing you to bring you back up to $%.2f/hr. The total bonus will be $%.2f.

We will try to send the bonus again periodically, so you will get paid after they deposit more funds.
        """ % (settings.MINIMUM_WAGE_PER_HOUR, settings.MINIMUM_WAGE_PER_HOUR, total_unpaid)

        mturk_clients = get_mturk_connection(requester, self.mturk)
        if is_sandbox:
            mturk_client = mturk_clients['sandbox']
        else:
            mturk_client = mturk_clients['production']

        try:
            response = mturk_client.notify_workers(Subject = subject, MessageText = message, WorkerIds = [worker.id])

        except mturk_client.exceptions.RequestError as e:
            self.stderr.write(self.style.ERROR(e))
