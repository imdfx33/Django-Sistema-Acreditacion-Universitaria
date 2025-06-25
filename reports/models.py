# reports/models.py
from django.db import models
from django.conf import settings
from django.utils import timezone

class FinalReport(models.Model):
    """
    Almacena la información de cada Informe Final generado.
    Se crea un nuevo registro cada vez que se genera un informe.
    """
    pdf_url = models.URLField(
        "URL pública del PDF del Informe Final",
        max_length=512, # Aumentado por si las URLs de Drive son muy largas
        help_text="Enlace compartible al PDF generado en Google Drive."
    )
    generated_at = models.DateTimeField(
        "Fecha de Generación",
        default=timezone.now,
        help_text="Fecha y hora en que se generó el informe."
    )
    generated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="generated_final_reports", # Cambiado related_name para evitar conflictos
        verbose_name="Generado por",
        help_text="Usuario que solicitó la generación del informe."
    )
    # Podríamos añadir más campos si es necesario, como:
    # num_projects_included = models.PositiveIntegerField(null=True, blank=True)
    # generation_status = models.CharField(max_length=20, choices=[('pending', 'Pendiente'), ('success', 'Exitoso'), ('failed', 'Fallido')], default='pending')
    # error_message = models.TextField(blank=True, null=True)


    class Meta:
        ordering = ["-generated_at"] # Mostrar los más recientes primero
        verbose_name = "Informe Final"
        verbose_name_plural = "Informes Finales"

    def __str__(self):
        return f"Informe Final generado el {self.generated_at.strftime('%Y-%m-%d %H:%M')} por {self.generated_by.get_full_name() if self.generated_by else 'Sistema'}"

