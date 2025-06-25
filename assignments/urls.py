# assignments/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('', views.assignments_page, name='assignments_page'), # Vista principal de la página de asignaciones
    path('assignments/', views.assignments_page, name='assignments'), # Alias por si se usa en algún lado

    # APIs para obtener datos para los selects y tablas
    path('api/projects-for-assignment/', views.api_projects_for_assignment, name='api_projects_for_assignment'), # SuperAdmin asignando Proyectos
    path('api/projects-for-miniadmin-factor-assignment/', views.api_projects_for_mini_admin_factor_assignment, name='api_projects_for_mini_admin_factor_assignment'), # MiniAdmin seleccionando proyecto para asignar factores
    
    path('api/mini-admin-users/', views.api_mini_admin_users, name='api_mini_admin_users'), # Lista de MiniAdmins
    path('api/assignable-users-for-factor/', views.api_assignable_users_for_factor, name='api_assignable_users_for_factor'), # Lista de usuarios para asignar factores

    path('api/factors-for-assignment/<str:project_id>/', views.api_factors_for_assignment, name='api_factors_for_assignment'), # Factores de un proyecto

    # APIs para obtener las asignaciones actuales
    path('api/project-assignments/<str:project_id>/', views.api_project_assignments_for_project, name='api_project_assignments_for_project'),
    path('api/factor-assignments/<str:factor_id>/', views.api_factor_assignments_for_factor, name='api_factor_assignments_for_factor'),

    # Endpoints POST para guardar asignaciones
    path('assign/project-to-miniadmin/', views.assign_project_to_mini_admin, name='assign_project_to_mini_admin'),
    path('assign/factor-to-user/', views.assign_factor_to_user, name='assign_factor_to_user'),
]
