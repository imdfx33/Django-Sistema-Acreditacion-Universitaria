import uuid
from django.db import models
from django.conf import settings
import json

def generate_id():
    return uuid.uuid4().hex[:10]

class Dofa(models.Model):
    dofa_id = models.CharField(
        primary_key=True,
        max_length=20,
        default=generate_id,
        editable=False,
        verbose_name='DOFA ID'
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='dofas',
        verbose_name="Usuario"
    )
    fortalezas = models.JSONField(
        "Fortalezas",
        default=dict,
        blank=True,
        null=True
    )
    debilidades = models.JSONField(
        "Debilidades",
        default=dict,
        blank=True,
        null=True
    )
    oportunidades = models.JSONField(
        "Oportunidades",
        default=dict,
        blank=True,
        null=True
    )
    amenazas = models.JSONField(
        "Amenazas",
        default=dict,
        blank=True,
        null=True
    )
    created_at = models.DateTimeField("Fecha de creación", auto_now_add=True)
    updated_at = models.DateTimeField("Última actualización", auto_now=True)

    def __str__(self):
        # Ensure user object and username exist before trying to access them
        username = "N/A"
        if hasattr(self, 'user') and self.user and hasattr(self.user, 'username'):
            username = self.user.username
        return f"Análisis DOFA ({self.dofa_id}) de {username} ({self.created_at.strftime('%Y-%m-%d')})"

    class Meta:
        verbose_name = "Análisis DOFA"
        verbose_name_plural = "Análisis DOFA"
        ordering = ['-created_at']

class PlanMejoramiento(models.Model):
    plan_id = models.CharField( # Este es el primary key
        primary_key=True,
        max_length=20, # Asegúrate que sea suficiente para generate_id
        default=generate_id,
        editable=False,
        verbose_name='Plan ID'
    )
    title = models.CharField(max_length=255, default="Plan de Mejoramiento") # Nombre del campo consistente
    contenido_json = models.JSONField(
        default=dict,
        blank=True,
        help_text="Contenido del plan y notas en formato JSON. Ejemplo: {'plan_texto': '...', 'notas_texto': '...'}"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    update_at = models.DateTimeField(auto_now=True) # Corregido de 'update_at'

    def __str__(self):
        return f"{self.title} - ID: {self.plan_id}"

    class Meta:
        verbose_name = "Plan de Mejoramiento"
        verbose_name_plural = "Planes de Mejoramiento"
        ordering = ['-update_at'] # Corregido de 'update_at'

    @property
    def plan_texto(self):
        return self.contenido_json.get('plan_texto', '')

    @plan_texto.setter
    def plan_texto(self, value):
        # Asegura que contenido_json sea un diccionario si aún no lo es
        if not isinstance(self.contenido_json, dict):
            self.contenido_json = {}
        self.contenido_json['plan_texto'] = value

    @property
    def notas_texto(self):
        return self.contenido_json.get('notas_texto', '')

    @notas_texto.setter
    def notas_texto(self, value):
        if not isinstance(self.contenido_json, dict):
            self.contenido_json = {}
        self.contenido_json['notas_texto'] = value

