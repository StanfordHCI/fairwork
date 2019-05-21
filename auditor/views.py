from django.shortcuts import render
from django.http import HttpResponse, Http404, HttpResponseBadRequest, HttpResponseServerError, HttpResponseRedirect, JsonResponse
from django.views.decorators.csrf import ensure_csrf_cookie, csrf_exempt
from django.views.decorators.clickjacking import xframe_options_exempt
from django.conf import settings
from django.core.signing import Signer
from django.core.management import call_command
from django.template import loader
from django.contrib.staticfiles.storage import staticfiles_storage
from django.urls import reverse
from django.db.models import Q


from .models import HITType, HIT, Worker, Assignment, AssignmentDuration, AssignmentAudit, Requester, RequesterFreeze
from .forms import RequesterForm, FreezeForm
from auditor.management.commands.pullnotifications import get_mturk_connection
# from auditor.management.commands.auditpayments import get_salt
from auditor.management.commands import auditpayments


from datetime import timedelta
from collections import defaultdict
import boto3
from statistics import median

@csrf_exempt
@xframe_options_exempt
def index(request):
    context = {
        'MIN_WAGE': settings.MINIMUM_WAGE_PER_HOUR
    }
    return render(request, 'index.html', context)

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
        'hit_type_id': ht.id,
        'worker_id': w.id
    })

@csrf_exempt
def most_recent_report(request):
    hit_id = __get_POST_param(request, 'hit_id')
    hit_type_id = __get_POST_param(request, 'hit_type_id')
    host = __get_POST_param(request, 'host')
    worker_id = __get_POST_param(request, 'worker_id')

    ht = HITType.objects.get(
        id = hit_type_id,
        host = host,
    )
    h = HIT.objects.get(
        id = hit_id,
        hit_type = ht
    )
    w = Worker.objects.get(
        id = worker_id
    )

    most_recent_report = AssignmentDuration.objects.filter(assignment__hit__hit_type = ht).filter(assignment__worker = w).order_by('-timestamp').first()
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

    strTime = __get_POST_param(request, 'duration')
    estTime = __get_POST_param(request, 'estimated_time')
    if (strTime == ""):
        # AssignmentDuration.objects.filter(assignment=assignment).delete()

        # return HttpResponse("Deleted duration for %s" % (assignment))
        try:
            est_minutes = float(estTime)
            measured_time = timedelta(minutes=est_minutes)

            at, created = AssignmentDuration.objects.update_or_create(
                assignment = assignment,
                defaults = {
                    'duration': timedelta(0),
                    'measured_time': measured_time
                }
            )

            return HttpResponse("Submitted %s: %s min." % (assignment, at.duration))
        except ValueError:
            return HttpResponse("Not a valid input")        
    else:
        try:
            minutes = float(strTime)
            duration = timedelta(minutes=minutes)
            print(duration)

            est_minutes = float(estTime)
            measured_time = timedelta(minutes=est_minutes)

            at, created = AssignmentDuration.objects.update_or_create(
                assignment = assignment,
                defaults = {
                    'duration': duration,
                    'measured_time': measured_time
                }
            )

            return HttpResponse("Submitted %s: %s min." % (assignment, at.duration))
        except ValueError:
            return HttpResponse("Not a valid input")

@csrf_exempt
def irb_agreement(request):
    worker_id = __get_POST_param(request, 'worker_id')
    agreement = __get_POST_param(request, 'agreement')

    worker, worker_created = Worker.objects.get_or_create(
        id = worker_id
    )

    if agreement == 'true':
        worker.irb_agreement = True
        worker.save()
    else:
        worker.irb_agreement = False
        worker.save()

    return HttpResponse("IRB agreement value toggled to %s" % agreement)

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
    aws_account = request.GET.get('aws_account')
    context = {
        'AWS_ACCOUNT': aws_account,
        'IFRAME_URL': request.build_absolute_uri('iframe'),
        'FAIRWORK_DOMAIN': request.build_absolute_uri('/'),
    }
    return render(request, 'fairwork.js', context, content_type='application/javascript')

@csrf_exempt
@xframe_options_exempt
def iframe(request):
    worker_id = request.GET.get('workerId')
    context = {
        'DURATION_URL': request.build_absolute_uri('duration'),
        'IRB_URL': request.build_absolute_uri('toggleirb'),
        'HOME_URL': request.build_absolute_uri('/'),
        'CREATE_HIT_URL': request.build_absolute_uri('createhit'),
        'MOST_RECENT_REPORT_URL': request.build_absolute_uri('mostrecent'),
        'FAIRWORK_DOMAIN': request.build_absolute_uri('/'),
        'IRB_AGREEMENT': "False",
        'WORKER_IRB': settings.WORKER_IRB_TEMPLATE,
        'MIN_WAGE': settings.MINIMUM_WAGE_PER_HOUR,
    }
    if worker_id:
        w, w_created = Worker.objects.get_or_create(id = worker_id)
        context['IRB_AGREEMENT'] = w.irb_agreement
                
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
    context = {
        'form': form,
        'REQUESTER_IRB': settings.REQUESTER_IRB_TEMPLATE
    }

    return render(request, 'keys.html', context)

def update_keys(key, secret, email, aws_account):
    try:
        __create_or_update_requester(aws_account, key, secret, email)
    except Exception as e:
        print(e)

def script(request):
    aws_account = request.GET.get('aws_account')
    context = { 'JS_URL': request.build_absolute_uri(reverse('load_js') + '?aws_account=%s' % aws_account) }

    return render(request, 'script.html', context)

def freeze(request, requester, worker_signed):
    signer = Signer(salt=auditpayments.get_salt())
    requester_object = Requester.objects.get(aws_account = requester)
    worker_id = signer.unsign(worker_signed)
    worker = Worker.objects.get(id = worker_id)

    statuses = ['pending', 'completed']
    status_durations = dict()

    for status in statuses:
        audits = AssignmentAudit.objects.filter(assignment__hit__hit_type__requester = requester_object).filter(message_sent__isnull = False)
        if status == 'pending':
            audits = audits.filter(closed=False).filter(needsPayment=True)
        elif status == 'completed':
            audits = audits.filter(closed = True).filter(needsPayment=True)
        else:
            raise Exception("Unknown status: %s" (status))

        hittypes = HITType.objects.filter(hit__assignment__assignmentaudit__in = audits).distinct()

        hittype_durations = dict()
        for hit_type in hittypes:

            duration_query = AssignmentDuration.objects.filter(assignment__hit__hit_type = hit_type).filter(assignment__assignmentaudit__in = audits)
            worker_durations = defaultdict(list)

            # Take the median report for each worker
            for duration in duration_query:
                worker_durations[duration.assignment.worker].append(duration.duration)

            # Now find the median per worker
            worker_median_durations = dict()
            for some_worker in worker_durations.keys():
                worker_median_durations[worker] = median(worker_durations[some_worker])
            hittype_durations[hit_type] = worker_median_durations

        status_durations[status] = hittype_durations

    # if this is a POST request we need to process the freeze form data
    if request.method == 'POST' and 'create' in request.POST.keys():
        # create a form instance and populate it with data from the request:
        form = FreezeForm(request.POST)
        # check whether it's valid:
        if form.is_valid():
            freeze = RequesterFreeze(worker=worker, requester=requester_object, reason=form.cleaned_data['reason'])
            freeze.save()
            # set assignment audit as frozen here
            to_freeze = Assignment.objects.filter(worker=worker).filter(hit__hit_type__requester_id = requester_object)

            for assignmentaudit in AssignmentAudit.objects.filter(closed=False):
                for assignment in to_freeze:
                    if assignment.id == assignmentaudit.assignment_id:
                        assignmentaudit.frozen = True
                        assignmentaudit.save()
                        break

            # show banner to requester saying that you froze worker
            # send email to worker saying you're frozen
            # need to get some sort of Mturk object...

            mturk_clients = get_mturk_connection(requester_object, dict())

            for is_sandbox in [True, False]:
                if is_sandbox:
                    mturk_client = mturk_clients['sandbox']
                else:
                    mturk_client = mturk_clients['production']

                try:
                    subject = "Fair Work Payments Frozen"
                    message = "A requester has frozen your Fair Work bonus payments. The requester gave the following reason for freezing your bonus payments: \n\n"
                    message += "\"" + form.cleaned_data['reason'] + "\"" + "\n\n"
                    message += "We ask requesters to only freeze payments if there is a major issue. If this freeze was done in error, please first try to contact the requester at " + str(requester_object.email) + ". If the requester is not responding or is responding in bad faith, our email is " + settings.ADMIN_EMAIL + "."
                    # If a requester is being unreasonable please email 
                    mturk_client.notify_workers(Subject = subject, MessageText = message, WorkerIds = [worker_id])

                except mturk_client.exceptions.RequestError as e:
                    print(e)

            call_command('auditpayments')

    elif request.method == 'POST' and 'delete' in request.POST.keys():
        form = FreezeForm()

        RequesterFreeze.objects.filter(worker=worker, requester=requester_object).delete()

        to_unfreeze = Assignment.objects.filter(worker=worker).filter(hit__hit_type__requester_id = requester_object)

        for assignmentaudit in AssignmentAudit.objects.filter(closed=False).filter(frozen=True):
            for assignment in to_unfreeze:
                if assignment.id == assignmentaudit.assignment_id:
                    assignmentaudit.frozen = False
                    assignmentaudit.save()
                    break

        call_command('auditpayments')
        # show banner to requester saying that you unfroze worker
        # send email to worker saying you're unfrozen

    else:
        form = FreezeForm()

    frozen = False
    if RequesterFreeze.objects.filter(worker=worker, requester=requester).count() > 0:
        # there's a freeze in place
        frozen = True

    context = {
        'requester': requester,
        'worker': worker,
        'status_durations': status_durations,
        'form': form,
        'frozen': frozen
    }

    return render(request, 'freeze.html', context)

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