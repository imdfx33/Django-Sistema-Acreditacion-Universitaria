import uuid
from django.db import models

def generate_id():
    return uuid.uuid4().hex[:10]

class Form(models.Model):
    form_id = models.CharField(
        primary_key=True,
        max_length=20,
        default=generate_id,
        editable=False,
        null=False,
        blank=False,
        verbose_name='Form ID'
    )
    modification_date = models.DateField(
        auto_now_add=True,
        null=True,
        blank=True,
        verbose_name='Modification Date'
    )
    archivo = models.FileField(
        null=True,
        blank=True,
        verbose_name='Archivo',
        upload_to='formularios_subidos/'  # Los archivos se guardarán aquí dentro de MEDIA_ROOT
    )
    STATUS_CHOICES = [
        ('pendiente', 'Pendiente'),
        ('finalizado', 'Finalizado'),
        ('en curso', 'En curso'),
    ]

    # ... (campos existentes)
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pendiente',
        verbose_name='Status'
    )

    def __str__(self):
        return self.form_id