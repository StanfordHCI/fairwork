from django.shortcuts import render
from django.http import HttpResponse, Http404, HttpResponseBadRequest
from django.views.decorators.csrf import ensure_csrf_cookie, csrf_exempt
from django.conf import settings
from django.shortcuts import render
from django.contrib.staticfiles.storage import staticfiles_storage


from .models import HITType, HIT, Worker, Assignment, AssignmentDuration, Requester
from auditor.management.commands.pullnotifications import get_mturk_connection

from datetime import timedelta

def index(request):
    return HttpResponse("You're at the Fair Work server home. Debug is %s." % settings.DEBUG)

@csrf_exempt
def create_hit(request):
    hit_id = __get_POST_param(request, 'hit_id')
    hit_type_id = __get_POST_param(request, 'hittype_id')
    aws_account = __get_POST_param(request, 'account')
    host = __get_POST_param(request, 'host')
    r = Requester.objects.get(aws_account = aws_account)

    if 'reward' in request.POST:
        reward = __get_POST_param(request, 'reward')
    else:
        mturk = get_mturk_connection(r, dict())
        if 'sandbox' in host:
            client = mturk['sandbox']
        else:
            client = mturk['production']
        response = client.get_hit(HITId=hit_id)
        reward = response['HIT']['Reward']

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
    return HttpResponse("Created HIT %s" % h.id)

@csrf_exempt
def assignment_duration(request):
    hit, hit_type, worker, assignment = __get_assignment_info(request)
    if 'aws_account' in request.POST: # this is coming from JS, where we won't have called create_hit
        aws_account = __get_POST_param(request, 'aws_account')
        r = Requester.objects.get(aws_account = aws_account)
    else:
        r = hit_type.requester
    if hit_type is None:
        mturk = get_mturk_connection(r, dict())
        host = __get_POST_param(request, 'host')
        if 'sandbox' in host:
            client = mturk['sandbox']
        else:
            client = mturk['production']
        response = client.get_hit(HITId=hit.id)
        ht = HITType(
            id = response['HIT']['HITTypeId'],
            payment = response['HIT']['Reward'],
            host = host,
            requester = r
        )
        ht.save()
        hit.hit_type = ht
        hit.save()

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
    aws_account = __get_POST_param(request, 'account')
    key = __get_POST_param(request, 'key')
    secret = __get_POST_param(request, 'secret')

    r, r_created = Requester.objects.get_or_create(
        aws_account = aws_account
    )
    if key != r.key or secret != r.secret:
        # the user has updated or rotated their AWS keys
        r.key = key
        r.secret = secret
        r.save()

    return HttpResponse("Requester data received")

@csrf_exempt
def load_js(request):
    # get the HTML that we want the JS to insert
    #url = staticfiles_storage.url('fairwork.html')
    with staticfiles_storage.open('fairwork.html', 'r') as myfile:
        data = url.read()

    aws_account = request.GET['account']
    context = {
        'AWS_ACCOUNT': aws_account,
        'DURATION_URL': request.build_absolute_uri('duration'),
        'HOME_URL': request.build_absolute_uri('/'),
        'DIV_HTML': data
    }
    return render(request, 'fairwork.js', context, content_type='application/javascript')



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
