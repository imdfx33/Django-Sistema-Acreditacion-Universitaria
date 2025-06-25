# factorList/urls.py
from django.urls import path
# Ya no necesitamos include aquí para factorManager
from . import views

urlpatterns = [
    # Rutas para la app factorList (visualización)
    path('',                 views.FactorListView.as_view(), name='factor_list'),
    path('<str:pk>/',        views.factor_detail,            name='factor_detail'),
    path('<str:pk>/approve', views.approve_factor,           name='factor_approve'),
    path('<str:pk>/reject',  views.reject_factor,            name='factor_reject'),
    
    # La siguiente línea se elimina de aquí, ya que factorManager ahora se incluye desde home/urls.py
    # path('factorManager/', include('factorManager.urls')), # <-- ELIMINAR ESTA LÍNEA
]
