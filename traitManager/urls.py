# traitManager/urls.py
from django.urls import path
from . import views

urlpatterns = [
    # Crear una nueva característica (puede o no tener un factor preseleccionado por URL GET param)
    path("create/", views.TraitCreateView.as_view(), name="trait_create"), 
    # Ejemplo de URL para crear una característica para un factor específico:
    # path("factor/<str:factor_pk>/trait/create/", views.TraitCreateView.as_view(), name="trait_create_for_factor"),
    # La TraitCreateView actual ya maneja ?factor=<id> en la URL.

    # Editar una característica existente
    path("<str:pk>/update/", views.TraitUpdateView.as_view(), name="trait_edit"),
    
    # Eliminar una característica existente
    path("<str:pk>/delete/", views.TraitDeleteView.as_view(), name="trait_delete"),
]
