from django.shortcuts import render
from django.http import HttpResponse, Http404, HttpResponseBadRequest, HttpResponseServerError
from django.views.decorators.csrf import ensure_csrf_cookie, csrf_exempt
from django.views.decorators.clickjacking import xframe_options_exempt
from django.conf import settings

from django.template import loader
from django.shortcuts import render
from django.contrib.staticfiles.storage import staticfiles_storage
from django.urls import reverse


from .models import HITType, HIT, Worker, Assignment, AssignmentDuration, Requester
from auditor.management.commands.pullnotifications import get_mturk_connection

from datetime import timedelta
import boto3

@csrf_exempt
def index(request):
    return render(request, 'index.html')

@csrf_exempt
def create_hit(request):
    hit_id = __get_POST_param(request, 'hit_id')
    hit_type_id = __get_POST_param(request, 'hittype_id')
    aws_account = __get_POST_param(request, 'aws_account')
    host = __get_POST_param(request, 'host')
    reward = __get_POST_param(request, 'reward')
    aws_account = settings.TEMP_ACCOUNT_ID
    r = Requester.objects.get(aws_account = aws_account)

    mturk = get_mturk_connection(r, dict())
    if 'sandbox' in host:
        client = mturk['sandbox']
    else:
        client = mturk['production']

    if reward is None:
        reward = __get_POST_param(request, 'reward')
    else:
        response = client.get_hit(HITId=hit_id)
        reward = response['HIT']['Reward']

    if hit_type_id is None:
        response = client.get_hit(HITId=hit_id)
        ht = HITType(
            id = response['HIT']['HITTypeId'],
            payment = response['HIT']['Reward'],
            host = host,
            requester = r
        )
        ht.save()
    else:
        ht, ht_created = HITType.objects.get_or_create(
            id = hit_type_id,
            payment = reward,
            host = host,
            requester = r
        )

    client.update_notification_settings(
        HITTypeId=ht.id,
        Notification={
            'Destination': settings.SQS_QUEUE,
            'Transport': 'SQS',
            'Version': '2014-08-15',
            'EventTypes': [ 'AssignmentApproved' ]
        }
    )

    h, h_created = HIT.objects.get_or_create(
        id = hit_id,
        hit_type = ht
    )
    return HttpResponse("Created HIT %s" % h.id)

@csrf_exempt
def assignment_duration(request):
    hit, hit_type, worker, assignment = __get_assignment_info(request)
    if 'aws_account' in request.POST: # this is coming from JS, where we won't have called create_hit
        aws_account = __get_POST_param(request, 'aws_account')
        r = Requester.objects.get(aws_account = aws_account)
    else:
        r = hit_type.requester

    minutes = float(__get_POST_param(request, 'duration'))
    duration = timedelta(minutes=minutes)

    at, created = AssignmentDuration.objects.update_or_create(
        assignment = assignment,
        defaults = {
            'duration': duration
        }
    )
    return HttpResponse("Submitted %s: %s min." % (assignment, at.duration))


@csrf_exempt
def requester(request):
    aws_account = __get_POST_param(request, 'aws_account')
    key = __get_POST_param(request, 'key')
    secret = __get_POST_param(request, 'secret')

    __create_or_update_requester(aws_account, key, secret)

    return HttpResponse("Requester data received")


@csrf_exempt
def load_js(request):
    aws_account = request.GET['aws_account']
    context = {
        'AWS_ACCOUNT': aws_account,
    }
    return render(request, 'fairwork.js', context, content_type='application/javascript')

@csrf_exempt
@xframe_options_exempt
def iframe(request):
    context = {
        'DURATION_URL': request.build_absolute_uri('duration'),
        'HOME_URL': request.build_absolute_uri('/'),
        'CREATE_HIT_URL': request.build_absolute_uri('createhit')
    }
    return render(request, 'fairwork.html', context)

def keys(request):
    return render(request, 'keys.html')

def update_keys(request):
    key = __get_POST_param(request, 'key')
    secret = __get_POST_param(request, 'secret')

    try:
        client = boto3.client("sts", aws_access_key_id=key, aws_secret_access_key=secret)
        aws_account = client.get_caller_identity()["Account"]
        __create_or_update_requester(aws_account, key, secret)
    except:
        context = { 'error_message': 'Your AWS keys are incorrect. Please check them and try again.' }
        return render(request, 'keys.html', context)

    context = { 'JS_URL': request.build_absolute_uri(reverse('load_js') + '?aws_account=%s' % aws_account) }

    return render(request, 'update_keys.html', context)

def __get_assignment_info(request):
    hit_id = __get_POST_param(request, 'hit_id')
    worker_id = __get_POST_param(request, 'worker_id')
    assignment_id = __get_POST_param(request, 'assignment_id')

    h, h_created = HIT.objects.get_or_create(
        id = hit_id
    )
    ht = h.hit_type
    w, w_created = Worker.objects.get_or_create(
        id = worker_id
    )
    a, a_created = Assignment.objects.get_or_create(
        id = assignment_id,
        hit = h,
        worker = w
    )
    return h, ht, w, a

def __get_POST_param(request, param):
    try:
        return request.POST.get(param)
    except KeyError:
        raise HttpResponseBadRequest("%s does not exist" % param)

def __create_or_update_requester(aws_account, key, secret):
    r, r_created = Requester.objects.get_or_create(
        aws_account = aws_account
    )
    if key != r.key or secret != r.secret:
        # the user has updated or rotated their AWS keys
        r.key = key
        r.secret = secret
        r.save()
