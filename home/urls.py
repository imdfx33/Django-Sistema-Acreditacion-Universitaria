# home/urls.py
from django.urls import path, include 
from . import views 

urlpatterns = [
    # Home url
    path('', views.homeView, name='home'),
    path('etapa3/', views.etapa_3_view, name='etapa_3'),
    
    # URLs de las apps específicas de la etapa 3
    path('etapa3/projects/', include('projects.urls')),
    
    path('etapa3/factorList/', include('factorList.urls')), # Para listar y ver detalles de factores
    path('etapa3/factorManager/', include('factorManager.urls')), # Para CRUD de factores (AHORA SEPARADO)

    path('etapa3/traitList/', include('traitList.urls')),
    path('etapa3/traitManager/', include('traitManager.urls')),

    path('etapa3/aspectList/', include('aspectList.urls')),
    path('etapa3/aspectManager/', include('aspectManager.urls')), # 

    path('etapa3/asignaciones/', include('assignments.urls')),

    path('etapa4/', views.etapa4_view, name='etapa_4'),
    path('etapa4/strategicAnalysis/', include('strategicAnalysis.urls')),
]
