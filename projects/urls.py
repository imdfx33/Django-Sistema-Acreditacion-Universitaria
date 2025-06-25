# projects/urls.py
from django.urls import path
from . import views

urlpatterns = [
    # Listar todos los proyectos (filtrados por permisos)
    path('', views.ProjectListView.as_view(), name='project_list'),
    
    # Crear un nuevo proyecto (solo superadmin/akadi)
    path('create/', views.ProjectCreateView.as_view(), name='project_create'),
    
    # Detalle de un proyecto específico
    path('<str:pk>/', views.ProjectDetailView.as_view(), name='project_detail'),
    
    # Editar un proyecto específico (solo editor del proyecto o superadmin/akadi)
    path('<str:pk>/edit/', views.ProjectUpdateView.as_view(), name='project_edit'),
    
    # Eliminar un proyecto específico (solo editor del proyecto o superadmin/akadi)
    path('<str:pk>/delete/', views.ProjectDeleteView.as_view(), name='project_delete'),

    # Aprobar un proyecto específico (solo editor del proyecto o superadmin/akadi)
    path('<str:pk>/approve/', views.project_approve, name='project_approve'),
]
