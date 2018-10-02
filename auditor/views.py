from django.shortcuts import render
from django.http import HttpResponse, Http404, HttpResponseBadRequest, HttpResponseServerError, HttpResponseRedirect, JsonResponse
from django.views.decorators.csrf import ensure_csrf_cookie, csrf_exempt
from django.views.decorators.clickjacking import xframe_options_exempt
from django.conf import settings

from django.template import loader
from django.shortcuts import render
from django.contrib.staticfiles.storage import staticfiles_storage
from django.urls import reverse


from .models import HITType, HIT, Worker, Assignment, AssignmentDuration, Requester
from .forms import RequesterForm
from auditor.management.commands.pullnotifications import get_mturk_connection

from datetime import timedelta
import boto3

@csrf_exempt
@xframe_options_exempt
def index(request):
    return render(request, 'index.html')

@csrf_exempt
def create_hit(request):
    hit_id = __get_POST_param(request, 'hit_id')
    hit_type_id = __get_POST_param(request, 'hit_type_id')
    assignment_id = __get_POST_param(request, 'assignment_id')
    worker_id = __get_POST_param(request, 'worker_id')
    aws_account = __get_POST_param(request, 'aws_account')
    host = __get_POST_param(request, 'host')
    reward = __get_POST_param(request, 'reward')
    r = Requester.objects.get(aws_account = aws_account)

    mturk = get_mturk_connection(r, dict())
    if 'sandbox' in host:
        client = mturk['sandbox']
    else:
        client = mturk['production']

    response = client.get_hit(HITId=hit_id)

    if reward is None:
        reward = response['HIT']['Reward']
    if hit_type_id is None:
        hit_type_id = response['HIT']['HITTypeId']

    ht, ht_created = HITType.objects.get_or_create(
        id = hit_type_id,
        payment = reward,
        host = host,
        requester = r
    )

    h, h_created = HIT.objects.get_or_create(
        id = hit_id,
        hit_type = ht
    )
    w, w_created = Worker.objects.get_or_create(
        id = worker_id
    )
    # AMT will sometimes reuse assignment IDs if an assignment
    # gets returned, so we need to update instead of crashing
    a, a_created = Assignment.objects.update_or_create(
        id = assignment_id,
        defaults = {'hit': h, 'worker': w}
    )

    return JsonResponse({
        'status': 'success',
        'host': host,
        'hit_id': h.id,
        'hit_type_id': ht.id
    })

@csrf_exempt
def most_recent_report(request):
    hit_id = __get_POST_param(request, 'hit_id')
    hit_type_id = __get_POST_param(request, 'hit_type_id')
    host = __get_POST_param(request, 'host')

    ht = HITType.objects.get(
        id = hit_type_id,
        host = host,
    )
    h = HIT.objects.get(
        id = hit_id,
        hit_type = ht
    )

    most_recent_report = AssignmentDuration.objects.filter(assignment__hit__hit_type = ht).order_by('-timestamp').first()
    if most_recent_report is None:
        return JsonResponse( {
            'assignment': None,
            'duration': None
        })
    else:
        return JsonResponse( {
            'assignment': most_recent_report.assignment.id,
            'duration': most_recent_report.duration
        })


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
    email = __get_POST_param(request, 'email')

    __create_or_update_requester(aws_account, key, secret, email)

    return HttpResponse("Requester data received")


@csrf_exempt
def load_js(request):
    aws_account = request.GET['aws_account']
    context = {
        'AWS_ACCOUNT': aws_account,
        'IFRAME_URL': request.build_absolute_uri('iframe'),
        'FAIRWORK_DOMAIN': request.build_absolute_uri('/')
    }
    return render(request, 'fairwork.js', context, content_type='application/javascript')

@csrf_exempt
@xframe_options_exempt
def iframe(request):
    context = {
        'DURATION_URL': request.build_absolute_uri('duration'),
        'HOME_URL': request.build_absolute_uri('/'),
        'CREATE_HIT_URL': request.build_absolute_uri('createhit'),
        'MOST_RECENT_REPORT_URL': request.build_absolute_uri('mostrecent')
    }
    return render(request, 'fairwork.html', context)

def keys(request):
    if request.method == 'POST':
        # create a form instance and populate it with data from the request:
        form = RequesterForm(request.POST)
        # check whether it's valid:
        if form.is_valid():
            update_keys(form.cleaned_data['key'], form.cleaned_data['secret'], form.cleaned_data['email'], form.aws_account)
            return HttpResponseRedirect('/script?aws_account=' + form.aws_account)
    else:
        form = RequesterForm()

    return render(request, 'keys.html', {'form': form})

def update_keys(key, secret, email, aws_account):
    __create_or_update_requester(aws_account, key, secret, email)
    print('updated')

def script(request):
    aws_account = request.GET.get('aws_account')
    context = { 'JS_URL': request.build_absolute_uri(reverse('load_js') + '?aws_account=%s' % aws_account) }

    return render(request, 'script.html', context)

def __get_assignment_info(request):
    hit_id = __get_POST_param(request, 'hit_id')
    worker_id = __get_POST_param(request, 'worker_id')
    assignment_id = __get_POST_param(request, 'assignment_id')

    h = HIT.objects.get(
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

def __create_or_update_requester(aws_account, key, secret, email):
    r, r_created = Requester.objects.get_or_create(
        aws_account = aws_account
    )
    if key != r.key or secret != r.secret:
        # the user has updated or rotated their AWS keys
        r.key = key
        r.secret = secret
        r.save()
    if email != r.email:
        r.email = email
        r.save()
