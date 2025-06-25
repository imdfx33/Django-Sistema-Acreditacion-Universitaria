# aspectList/urls.py
from django.urls import path
# No necesitamos 'include' aquí para aspectManager si se maneja en home/urls.py
# No necesitamos importar 'toggle_approval' directamente si usamos la URL namespaced
from . import views

app_name = 'aspectList' # Es buena práctica definir app_name para todas las apps con URLs

urlpatterns = [
    # Rutas para la app aspectList (visualización)
    path('', views.AspectListView.as_view(), name='aspect_list'),
    path('<str:pk>/', views.AspectDetailView.as_view(), name='aspect_detail'),
    
    # La URL para 'toggle_approval' ahora se accederá a través del namespace 'aspectManager'
    # path('<str:pk>/toggle/', toggle_approval, name='aspect_toggle'), # <-- ELIMINAR O COMENTAR ESTA LÍNEA
    
    # La siguiente línea se elimina de aquí, ya que aspectManager ahora se incluye desde home/urls.py
    # path('aspectManager/', include('aspectManager.urls')), # <-- ELIMINAR ESTA LÍNEA
]
