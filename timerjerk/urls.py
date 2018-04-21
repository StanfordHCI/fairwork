from django.urls import path

from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('createhit', views.create_hit, name='createHIT'),
    path('submitted', views.assignment_submitted, name='submitted'),
    path('duration', views.assignment_duration, name='duration'),
]
