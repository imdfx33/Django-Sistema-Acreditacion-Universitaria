# aspectManager/urls.py
from django.urls import path
from . import views

app_name = 'aspectManager' # <--- AÑADIDO: Espacio de nombres para la app

urlpatterns = [
    # Crear un nuevo aspecto.
    # Puede recibir ?trait=<trait_pk> para preseleccionar la característica.
    path("create/", views.AspectCreateView.as_view(), name="aspect_create"),
    
    # Editar un aspecto existente
    path("<str:pk>/update/", views.AspectUpdateView.as_view(), name="aspect_edit"),
    
    # Eliminar un aspecto existente
    path("<str:pk>/delete/", views.AspectDeleteView.as_view(), name="aspect_delete"),
    
    # Marcar/desmarcar un aspecto como aprobado
    path("<str:pk>/toggle-approval/", views.toggle_approval, name="aspect_toggle_approval"),
]
