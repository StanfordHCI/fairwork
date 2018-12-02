from django.urls import path

from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('createhit', views.create_hit, name='createHIT'),
    path('duration', views.assignment_duration, name='duration'),
    path('toggleirb', views.irb_agreement, name='toggleirb'),
    path('requester', views.requester, name='requester'),
    path('mostrecent', views.most_recent_report, name='mostrecent'),
    path('fairwork.js', views.load_js, name='load_js'),
    path('iframe', views.iframe, name='iframe'),
    path('keys', views.keys, name='keys'),
    path('script', views.script, name='script'),
]
