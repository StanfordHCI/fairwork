from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from django.db.models import Q
from auditor.models import HITType, HIT, Worker, Assignment, Requester

import boto3
import json

class Command(BaseCommand):
    help = 'Checks for completed HITs and updates the database'

    mturk = dict() # maintains the Boto client connections

    def handle(self, *args, **options):
        # get all Assignments in Open or Submitted status, and update them to Accepted/Rejected so that we can audit
        assignments = Assignment.objects.filter(Q(status = Assignment.OPEN) | Q(status = Assignment.SUBMITTED))

        for assignment in assignments:
            self.stdout.write(assignment.id)
            hit_type = assignment.hit.hit_type
            mturk_clients = get_mturk_connection(hit_type.requester, self.mturk)
            if hit_type.is_sandbox():
                mturk_client = mturk_clients['sandbox']
            else:
                mturk_client = mturk_clients['production']

            try:
                amt_response = mturk_client.get_assignment(AssignmentId = assignment.id)
                # Since we can't guarantee that the HIT has been approved yet, we need to check
                status = amt_response['Assignment']['AssignmentStatus']
                if status == 'Submitted':
                    # Submitted means it hasn't been reviewed yet
                    assignment.status = Assignment.SUBMITTED
                elif status == 'Rejected':
                    # if it's been rejected, don't include it in the audit:
                    # if this requester is trustable, there should be a good reason
                    # a future version should try to intercede on rejections and prevent wage theft
                    assignment.status = Assignment.REJECTED
                elif status == 'Approved':
                    assignment.status = Assignment.APPROVED
                self.stdout.write('\t%s' % assignment.get_status_display())

                assignment.save()

            except mturk_client.exceptions.RequestError as e:
                if e.response['Error']['Message'].startswith('This operation can be called with a status of: Reviewable,Approved,Rejected'):
                    # it's either still checked out, or returned
                    # keep it in the queue unless the HIT is done
                    try:
                        hit_response = mturk_client.get_hit(HITId = assignment.hit.id)
                        assignments_remaining = int(hit_response['HIT']['NumberOfAssignmentsPending']) + int(hit_response['HIT']['NumberOfAssignmentsAvailable'])
                        if assignments_remaining == 0:
                            # the HIT is done, this assignment was likely a return
                            self.stderr.write(self.style.ERROR('Assignment %s is not known but also no longer viable --- HIT %s is complete. Likely a returned assignment. Disabling polling for it.' % (assignment.id, assignment.hit.id)))
                            assignment.status = Assignment.ERROR
                            assignment.save()
                    except mturk_client.exceptions.RequestError as e2:
                        self.stderr.write(self.style.ERROR(e2))
                elif e.response['Error']['Message'].startswith('Assignment %s does not exist.' % assignment.id):
                    self.stderr.write(self.style.ERROR('%s is not a known assignment. Disabling polling for it.' % assignment.id))
                    assignment.status = Assignment.ERROR
                    assignment.save()


def get_mturk_connection(requester, mturk):
    if requester.aws_account in mturk:
        return mturk[requester.aws_account]
    else:
        connection = boto3.client('mturk',
            aws_access_key_id=requester.key,
            aws_secret_access_key=requester.secret,
            region_name='us-east-1',
            endpoint_url = settings.MTURK_ENDPOINT
        )
        connection_sandbox = boto3.client('mturk',
            aws_access_key_id=requester.key,
            aws_secret_access_key=requester.secret,
            region_name='us-east-1',
            endpoint_url = settings.MTURK_SANDBOX_ENDPOINT
        )
        mturk[requester.aws_account] = {
            'production': connection,
            'sandbox': connection_sandbox
        }
        return mturk[requester.aws_account]
