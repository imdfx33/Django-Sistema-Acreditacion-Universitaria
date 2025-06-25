from django.urls import path
from .views import list_events, calendar

urlpatterns = [
    path('', calendar, name='calendar'),
    path('list/', list_events, name='list_events'),
]

