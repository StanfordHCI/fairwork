from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from django.core.mail import send_mail
from django.utils import timezone
from django.db.models import Q

import decimal
from decimal import Decimal
import itertools
from datetime import datetime, timedelta

import boto3

from auditor.models import HITType, HIT, Worker, Assignment, AssignmentDuration, AssignmentAudit, Requester
from auditor.management.commands.pullnotifications import get_mturk_connection
from auditor.management.commands import auditpayments

"""
Pays bonuses for audited HITs that underpaid.
"""

class Command(BaseCommand):
    help = 'Bonus underpayment for audited tasks'

    mturk = dict() # maintains the Boto client connections

    def handle(self, *args, **options):
        self.__pay_audited_hits()

    ###
    ### Pay the HITs that need to be paid
    ###
    def __pay_audited_hits(self):
        grace_period_limit = timezone.now() - auditpayments.REQUESTER_GRACE_PERIOD

        self.stdout.write(self.style.WARNING('Grace period has ended for audits notified before %s' % timezone.localtime(grace_period_limit).strftime("%B %d at %-I:%M%p %Z")))
        for is_sandbox in [True, False]:
            self.stdout.write(self.style.WARNING('Sandbox mode: %s' % is_sandbox))

            audits = AssignmentAudit.objects.filter(closed = False).filter(needsPayment = True).filter(message_sent__lte = grace_period_limit)

            if is_sandbox:
                audits = audits.filter(assignment__hit__hit_type__host__contains = 'sandbox')
            else:
                audits = audits.exclude(assignment__hit__hit_type__host__contains = 'sandbox')

            requesters = Requester.objects.filter(hittype__hit__assignment__assignmentaudit__in = audits).distinct()

            for requester in requesters:
                self.stdout.write(self.style.WARNING('Requester: %s %s' % (requester.aws_account, requester.email)))

                requester_to_bonus = audits.filter(assignment__hit__hit_type__requester = requester).order_by('assignment__hit', 'assignment__hit__hit_type', 'assignment__worker')

                workers = Worker.objects.filter(assignment__assignmentaudit__in = requester_to_bonus).distinct()
                for worker in workers:
                    assignments_to_bonus = requester_to_bonus.filter(assignment__worker = worker).distinct()
                    self.__bonus_worker(worker, assignments_to_bonus, requester, is_sandbox)

                # The assignments still listed as unpaid indicate that the requester didn't have sufficient funds
                still_unpaid = requester_to_bonus.filter(needsPayment = True).filter(frozen = False)
                still_unpaid = still_unpaid.all() # refreshes the queryset from the DB, since we just changed payment status of a bunch of items
                if len(still_unpaid) > 0:
                    self.__notify_insufficient_funds_requester(requester, still_unpaid)

    def __bonus_worker(self, worker, assignments_to_bonus, requester, is_sandbox):
        self.stdout.write(self.style.WARNING('Worker: %s' % worker.id))
        total_unpaid = auditpayments.get_underpayment(assignments_to_bonus)

        self.stdout.write(self.style.WARNING('Total bonus for %s: $%.2f\n---------' % (worker.id, total_unpaid)))

        # Send the bonus
        # Construct the message to the worker
        message = auditpayments.audit_list_message(assignments_to_bonus, requester, True, False, is_sandbox)

        # Bonus worker on first assignment in the HITGroup (to avoid being spammy) and keep a record
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
            # Maybe now just turn everything into closed...
            for unpaid_task in assignments_to_bonus:
                unpaid_task.closed = True
                unpaid_task.save()
        except mturk_client.exceptions.RequestError as e:
            if e.response['Error']['Message'].startswith("This Requester has insufficient funds in their account to complete this transaction."):
                self.stderr.write(self.style.ERROR("Requester does not have enough funds. Notifying worker."))
                self.__notify_insufficient_funds_worker(requester, is_sandbox, worker, total_unpaid, assignment_to_bonus)
            elif e.response['Error']['Message'].startswith("The idempotency token"): # has already been processed
                self.stderr.write(self.style.ERROR("Identical bonus has already been paid on this task. Skipping."))
                # They already paid it, mark it as done
                for unpaid_task in assignments_to_bonus:
                    unpaid_task.closed = True
                    unpaid_task.save()
            else:
                self.stderr.write(self.style.ERROR(e))

    def __notify_insufficient_funds_worker(self, requester, is_sandbox, worker, total_unpaid, assignment_to_bonus):
        """
        Tells the worker to tell the requester to deposit more money.
        Then, emails the requester.
        """

        subject = "Fair Work bonus of $%.2f pending, but requester out of funds — please notify requester" % total_unpaid

        message = """This is an automated message from the Fair Work script: this requester is trying to bonus you, but they don't have enough funds in their account to send the bonus. Please reply and let them know that they need to deposit more funds.
This requester is using the Fair Work script to ensure pay rates reach a minimum wage of $%.2f/hr. Fair Work does this by asking for completion times and then auto-bonusing workers to meet the desired hourly wage. Based on worker time reports, your tasks have been underpaid. We are bonusing you to bring you back up to $%.2f/hr. The total bonus will be $%.2f.
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

    def __notify_insufficient_funds_requester(self, requester, unpaid_assignments):
        total_underpaid = auditpayments.get_underpayment(unpaid_assignments)
        total_deposit = total_underpaid * Decimal('1.20') # AMT bonus fee rate
        subject = "Error: Fair Work bonuses are pending but you are out of funds. Please deposit $%.2f." % total_deposit
        message = """This is an automated message from the Fair Work script: you have underpaid workers and need to bonus them, but you don't have enough funds in your account to send the bonus. You need to send bonuses totaling $%.2f, but with Mechanical Turk's fee, you need to deposit $%.2f to have enough funds to send those bonuses. Please deposit more funds, and we will automatically retry in roughly 24 hours.
We are sending you this note because you are using the Fair Work script to ensure Mechanical Turk pay rates reach a minimum wage of $%.2f/hr. Fair Work does this by asking for completion times and then auto-bonusing workers to meet the desired hourly wage. Based on worker time reports, your tasks have been underpaid.
        """ % (total_underpaid, total_deposit, settings.MINIMUM_WAGE_PER_HOUR)

        send_mail(subject, message, auditpayments.admin_email_address(), [requester.email], fail_silently=False)
        self.stdout.write(message)
