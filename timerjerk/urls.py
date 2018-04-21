from django.urls import path

from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('createhit', views.create_hit, name='createHIT'),
    path('duration', views.assignment_duration, name='duration'),
]
