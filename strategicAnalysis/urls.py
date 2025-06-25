from django.urls import path, include
from . import views

urlpatterns = [

    path('home/etapa4/submit_request/', views.submit_request, name= "submit_request"),
    path('home/etapa4/matrixDOFA/', views.matrix_DOFA, name= "matrixDOFA"),
    path('home/etapa4/matrixDOFA/saveDOFA', views.save_dofa_data_view, name= "saveDOFA"),
    path('home/etapa4/plan_mejoramiento', views.plan_mejoramiento_view, name= "plan_mejoramiento"),
    path('home/etapa4/plan_mejoramiento/save_plan', views.save_plan, name= "save_plan"),
    path('home/etapa4/revision_plan', views.revision_plan_view, name= "revision_plan")
]
