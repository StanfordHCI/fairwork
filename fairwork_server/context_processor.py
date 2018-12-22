from django.conf import settings

def fairwork_context_processor(request):
    # add the relevant user info to the dictionary
    # for use in base.html
    return {
        'fairwork_name': settings.ADMIN_NAME,
        'fairwork_email': settings.ADMIN_EMAIL
    }
