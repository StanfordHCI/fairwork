from django.shortcuts import render
from django.http import HttpResponse, Http404
from django.views.decorators.csrf import ensure_csrf_cookie, csrf_exempt
from django.conf import settings

from .models import HITType, HIT, Worker, Assignment, AssignmentDuration, Requester

from datetime import timedelta

def index(request):
    return HttpResponse("You're at the timerjerk index. Debug is %s." % settings.DEBUG)

@csrf_exempt
def create_hit(request):
    hit_id = __get_POST_param(request, 'hit_id')
    hit_type_id = __get_POST_param(request, 'hittype_id')
    aws_account = __get_POST_param(request, 'account')

    r = Requester.objects.get(aws_account = aws_account)
    ht, ht_created = HITType.objects.get_or_create(
        id = hit_type_id,
        payment = __get_POST_param(request, 'reward'),
        host = __get_POST_param(request, 'host'),
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
        return request.POST[param]
    except KeyError:
        raise Http404("%s does not exist" % param)
