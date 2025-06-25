from django.urls import path
from . import views


urlpatterns = [
    path('obtener-directores/', views.obtener_directores_programa, name='obtener_directores_programa'),
    path('guardar-archivos/',    views.guardar_archivos_adjuntos,  name='guardar_archivos_adjuntos'),
    path('',                     views.attachGeneric,             name='attach_generic'),
    # URL para adjuntar a una Característica
    path('trait/<str:pk>/',     views.attach_generic_trait,       name='attach_generic_trait'),

    path('delete-attachment/<str:file_pk>/', views.delete_attachment, name='delete_attachment'),

]