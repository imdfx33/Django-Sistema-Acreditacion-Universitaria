# database/models.py

import uuid
from django.db import models
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager
from django.contrib.auth.models import Group, Permission
from django.db import models
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey
import uuid

from django.conf import settings

def generate_id():
    return uuid.uuid4().hex[:10]

class AccreditationProcess(models.Model):
    id_process = models.CharField(
        primary_key=True,
        max_length=10,
        default=generate_id,
        editable=False,
        null=False,
        blank=False,
    )
    name = models.CharField(max_length=30, null=False, blank=False)
    date_start = models.DateField()
    date_end = models.DateField()

class Calendar(models.Model):
    id_calendar = models.CharField(
        primary_key=True,
        max_length=10,
        default=generate_id,
        editable=False,
        null=False,
        blank=False,
    )

class ActiveAccreditationProcess(models.Model):
    id_user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=False, blank=False)
    id_process = models.ForeignKey('AccreditationProcess', on_delete=models.CASCADE, db_column='id_process', null=False, blank=False)

class Phase(models.Model):
    id_phase = models.CharField(
        primary_key=True,
        max_length=10,
        default=generate_id,
        editable=False,
        null=False,
        blank=False,
    )
    description = models.CharField(max_length=100)
    date_start = models.DateField()
    date_end = models.DateField()
    id_process = models.ForeignKey('AccreditationProcess', on_delete=models.CASCADE, db_column='id_process', null=False, blank=False)

try:
    from calendar_create_event.models import Event
except ImportError:
    Event = None

def generate_id(): # Asegúrate que esta función esté definida si la usas como default
    return uuid.uuid4().hex[:10]

class File(models.Model):
    id_file = models.CharField(
        primary_key=True,
        max_length=10,
        default=generate_id,
        editable=False,
    )
    name = models.CharField(max_length=255, null=False, blank=False) # Aumentado max_length
    type = models.CharField(max_length=10, null=False, blank=False)
    archivo = models.FileField(
        upload_to='archivos_subidos/', # Asegúrate que MEDIA_ROOT esté configurado
        null=True, # Permite nulo si el archivo solo está en Drive
        blank=True
    )
    modification_date = models.DateField(auto_now_add=True, null=True, blank=True)
    STATUS_CHOICES = [('inactivo', 'Inactivo'), ('activo', 'Activo')]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='activo')
    director_programa = models.CharField(max_length=255, null=True, blank=True)

    # --- Campos para relación genérica (con Trait, etc.) ---
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, null=True, blank=True)
    object_id = models.CharField(max_length=50, null=True, blank=True) # Asegúrate que la longitud sea suficiente para tus PKs
    content_object = GenericForeignKey('content_type', 'object_id')

    # --- NUEVOS CAMPOS AÑADIDOS ---
    # Para relación directa con un Evento (si es necesario)
    if Event: # Solo añadir si el modelo Event se pudo importar
        id_event = models.ForeignKey(
            Event,
            on_delete=models.SET_NULL, # O CASCADE, PROTECT según tu lógica
            null=True,
            blank=True,
            related_name='adjuntos', # Nombre para la relación inversa desde Event
            verbose_name='Evento Asociado (FK Directa)'
        )
    
    drive_link = models.URLField(
        max_length=1024, # Los enlaces de Drive pueden ser largos
        blank=True,
        null=True,
        verbose_name='Enlace Google Drive'
    )
    # --- FIN DE NUEVOS CAMPOS ---

    def __str__(self):
        return self.name if self.name else f"Archivo ID: {self.id_file}"

    class Meta:
        verbose_name = "Archivo Adjunto"
        verbose_name_plural = "Archivos Adjuntos"

class Version(models.Model):
    id_version = models.CharField(
        primary_key=True,
        max_length=10,
        default=generate_id,
        editable=False,
        null=False,
        blank=False,
    )
    date = models.DateField()
    id_file = models.ForeignKey('File', on_delete=models.CASCADE, db_column='id_file', null=False, blank=False)

class LoginAttempt(models.Model):
    id = models.AutoField(primary_key=True)
    email = models.EmailField()
    timestamp = models.DateTimeField(auto_now_add=True)
    success = models.BooleanField(default=False)
    
    def __str__(self):
        estado = "Éxito" if self.success else "Fallo"
        return f"{self.email} - {estado} - {self.timestamp}"