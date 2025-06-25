from django.urls import path
from . import views

urlpatterns = [
    path('', views.gestion_formularios, name='gestion-formularios'),
    path('crear-formulario/', views.crear_formulario, name='crear-formulario'),
    path('actualizar-estado/<str:form_id>/', views.actualizar_estado, name='actualizar-estado'),
    path('adjuntar-pdf/<str:form_id>/', views.adjuntar_pdf, name='adjuntar-pdf'),
]