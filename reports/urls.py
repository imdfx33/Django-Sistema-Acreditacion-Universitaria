from django.urls import path
from . import views

app_name = "reports"

urlpatterns = [
    path(
        "generate-final-report/", # Asegúrate de que esta ruta termine en slash
        views.generate_final_report,
        name="generate_final_report"
    ),
]