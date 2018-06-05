from django.urls import path

from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('createhit', views.create_hit, name='createHIT'),
    path('duration', views.assignment_duration, name='duration'),
    path('requester', views.requester, name='requester'),
    path('fairwork.js', views.load_js, name='load_js'),
    path('iframe', views.iframe, name='iframe'),
    path('keys', views.keys, name='keys'),
    path('update_keys', views.update_keys, name='update_keys'),
]
