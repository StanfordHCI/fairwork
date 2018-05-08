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
                for event in events:
                    event_type = event['EventType']
                    event_timestamp = event['EventTimestamp']
                    hit_id = event['HITId']
                    assignment_id = event['AssignmentId']
                    hit_type_id = event['HITTypeId']

                    amt_response = self.mturk.get_assignment(AssignmentId = assignment_id)
                    worker_id = amt_response['Assignment']['WorkerId']

                    print("Assignment %s from worker %s in hit %s of hit type %s" % (assignment_id, worker_id, hit_id, hit_type_id))

                    ht, ht_created = HITType.objects.get_or_create(
                        id = hit_type_id
                    )
                    h, h_created = HIT.objects.get_or_create(
                        id = hit_id,
                        hit_type = ht
                    )
                    w, w_created = Worker.objects.get_or_create(
                        id = worker_id
                    )
                    a, a_created = Assignment.objects.get_or_create(
                        id = assignment_id,
                        hit = h,
                        worker = w
                    )
                    a.status = Assignment.ACCEPTED
                    a.save()

                # Delete received message from queue
                message.delete()


        self.stdout.write(self.style.SUCCESS('Pulled %d messages' % total_messages))
