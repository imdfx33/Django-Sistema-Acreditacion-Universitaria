from django.urls import path
from .views import create_event, guardar_evento, edit_event

urlpatterns = [
    path('',              create_event,    name='create_event'),
    path('guardar_evento/', guardar_evento, name='guardar_evento'),
    # Event.id is IntegerField, so use <int:…>
    path('edit/<int:event_id>/', edit_event, name='edit_event'),
]