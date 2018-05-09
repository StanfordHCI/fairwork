from django.shortcuts import render
from django.http import HttpResponse, Http404
from django.views.decorators.csrf import ensure_csrf_cookie, csrf_exempt
from django.conf import settings

from .models import HITType, HIT, Worker, Assignment, AssignmentDuration

from datetime import timedelta

def index(request):
    return HttpResponse("Hello, world. You're at the timerjerk index. Sandbox is %s" % settings.USE_SANDBOX)

@csrf_exempt
def create_hit(request):
    hit_id = __get_POST_param(request, 'hit_id')
    hit_type_id = __get_POST_param(request, 'hittype_id')

    ht, ht_created = HITType.objects.get_or_create(
        id = hit_type_id,
        payment = __get_POST_param(request, 'reward')
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
