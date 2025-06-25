# factorManager/urls.py
from django.urls import path
from . import views

urlpatterns = [
    # Listar todos los factores (filtrados por permisos)
    path('', views.FactorListView.as_view(), name='factor_list'),
    
    # Crear un nuevo factor (requiere ser SuperAdmin/Akadi o MiniAdmin EDITOR del proyecto)
    # Se puede pasar ?project=<project_pk> para preseleccionar el proyecto
    path('create/', views.FactorCreateView.as_view(), name='factor_create'),
    
    # Detalle de un factor específico
    path('<str:pk>/', views.FactorDetailView.as_view(), name='factor_detail'),
    
    # Editar un factor específico (solo editor del factor/proyecto)
    path('<str:pk>/edit/', views.FactorUpdateView.as_view(), name='factor_edit'),
    
    # Eliminar un factor específico (solo editor del factor/proyecto)
    path('<str:pk>/delete/', views.FactorDeleteView.as_view(), name='factor_delete'),

    # Aprobar un factor específico (solo editor del factor/proyecto)
    path('<str:pk>/approve/', views.approve_factor, name='factor_approve'),

    # Rechazar un factor específico (solo editor del factor/proyecto)
    path('<str:pk>/reject/', views.reject_factor, name='factor_reject'),
]
