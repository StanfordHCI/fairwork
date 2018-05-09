from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from timerjerk.models import HITType, HIT, Worker, Assignment

import boto3
import json

class Command(BaseCommand):
    help = 'Pulls SQS notifications and updates the database'

    sqs = boto3.resource('sqs',
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        region_name=settings.SQS_REGION_NAME
    )
    queue = sqs.get_queue_by_name(QueueName=settings.SQS_QUEUE_NAME)
    mturk = boto3.client('mturk',
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        region_name='us-east-1',
        endpoint_url = settings.MTURK_ENDPOINT
    )
    mturk_sandbox = boto3.client('mturk',
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        region_name='us-east-1',
        endpoint_url = settings.MTURK_SANDBOX_ENDPOINT
    )

    def handle(self, *args, **options):
        total_messages = 0
        while True:
            sqs_response = self.queue.receive_messages(MaxNumberOfMessages=10)
            if len(sqs_response) == 0:
                break

            total_messages += len(sqs_response)
            for message in sqs_response:
                body = json.loads(message.body)
                events = body['Events']

                if len(events) > 1:
                    raise Exception("More than one event in SQS notification. There should only be one.")

                try:
                    event = events[0]
                    event_type = event['EventType']
                    event_timestamp = event['EventTimestamp']
                    hit_id = event['HITId']
                    assignment_id = event['AssignmentId']
                    hit_type_id = event['HITTypeId']

                    self.stdout.write("Assignment %s in hit %s of hit type %s" % (assignment_id, hit_id, hit_type_id))

                    ht, ht_created = HITType.objects.get_or_create(
                        id = hit_type_id
                    )
                    h, h_created = HIT.objects.get_or_create(
                        id = hit_id,
                        hit_type = ht
                    )

                    if ht.is_sandbox():
                        mturk_client = self.mturk_sandbox
                    else:
                        mturk_client = self.mturk

                    amt_response = mturk_client.get_assignment(AssignmentId = assignment_id)
                    worker_id = amt_response['Assignment']['WorkerId']
                    w, w_created = Worker.objects.get_or_create(
                        id = worker_id
                    )
                    a, a_created = Assignment.objects.get_or_create(
                        id = assignment_id,
                        hit = h,
                        worker = w
                    )

                    # Since we can't guarantee that the HIT has been approved yet, we need to checklist
                    status = amt_response['Assignment']['AssignmentStatus']
                    if status == 'Submitted':
                        # Submitted means it hasn't been reviewed yet
                        # We get this if the client was using Boto 2, which doesn't have approved/rejected
                        # Ask mturk to get back to us when it's been approved
                        self.stdout.write('\tNot reviewed yet; setting up notification for approval')
                        a.status = Assignment.SUBMITTED

                        if ht.is_sandbox():
                            mturk_client = self.mturk_sandbox
                        else:
                            mturk_client = self.mturk

                        # TODO: it's possible that the assignment gets approved in the moment between
                        # us querying status and us setting up approval notification
                        mturk_client.update_notification_settings(
                            HITTypeId=hit_type_id,
                            Notification={
                                'Destination': settings.SQS_QUEUE,
                                'Transport': 'SQS',
                                'Version': '2014-08-15',
                                'EventTypes': ['AssignmentApproved']
                            },
                            Active=True
                        )
                    elif status == 'Rejected':
                        # if it's been rejected, don't include it in the audit:
                        # presumably there was a good reason
                        self.stdout.write('\tRejected')
                        a.status = Assignment.REJECTED
                    elif status == 'Approved':
                        self.stdout.write('\tApproved')
                        a.status = Assignment.APPROVED

                    a.save()
                    message.delete()

                except self.mturk.exceptions.RequestError as e:
                    self.stderr.write(self.style.ERROR(e))


        self.stdout.write(self.style.SUCCESS('Pulled %d messages' % total_messages))
