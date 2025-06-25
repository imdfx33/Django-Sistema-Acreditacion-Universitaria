# traitList/urls.py
from django.urls import path, include # include para las URLs de traitManager
from . import views
# Importar la vista de attachGeneric si se va a usar directamente aquí
# from attachGeneric.views import attach_generic_trait # Ya no es necesaria aquí si se maneja en traitManager

urlpatterns = [
    # Lista todas las características (filtradas por permisos)
    path('', views.TraitListView.as_view(), name='trait_list'),
    
    # Detalle de una característica específica
    # Se mantiene el 'detail' en la URL para consistencia, aunque el nombre de la vista sea TraitDetailView
    path('<str:pk>/', views.TraitDetailView.as_view(), name='trait_detail'), 
    
    # Las URLs de creación, edición, eliminación ahora están en traitManager.urls
    # Se podría incluir traitManager.urls aquí si se desea un prefijo como /traits/manage/...
    # Pero según la estructura actual, es mejor que home/urls.py incluya traitManager directamente.
    # path('manage/', include('traitManager.urls')), # Ejemplo si se quisiera anidar

    # La URL para adjuntar archivos a una característica ahora podría estar en traitManager o attachGeneric.
    # Si se quiere acceder como /traits/<pk>/attach/, se define aquí o se referencia desde traitManager.
    # Por simplicidad, la vista attach_generic_trait de attachGeneric puede ser llamada directamente
    # desde un template si el contexto (trait.pk) está disponible.
    # Si se quiere una URL específica en traitList para esto:
    # path('<str:pk>/attach/', attach_generic_trait, name='trait_attach_file'),
]
