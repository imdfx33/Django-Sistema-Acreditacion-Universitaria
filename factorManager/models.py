#{factorManager/models.py}#
import uuid
from django.db import models
from django.conf import settings
from django.contrib.auth import get_user_model
from google.oauth2 import service_account
from googleapiclient.discovery import build

from aspectManager.models import Aspect
from projects.models import Project
from login.models import Rol

# ——— Service Account Credentials y Scopes ———
SERVICE_ACCOUNT_FILE = settings.GOOGLE_SERVICE_ACCOUNT_FILE
SCOPES = (
    settings.GOOGLE_DRIVE_SCOPES
    + getattr(settings, 'GOOGLE_DOCS_SCOPES', [])
)

def _get_service_credentials():
    """Obtiene credentials de Service Account para Drive/Docs."""
    return service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE,
        scopes=SCOPES
    )


def _drive_service():
    """Inicializa cliente de Google Drive."""
    creds = _get_service_credentials()
    return build('drive', 'v3', credentials=creds, cache_discovery=False)


def _docs_service():
    """Inicializa cliente de Google Docs."""
    creds = _get_service_credentials()
    return build('docs', 'v1', credentials=creds, cache_discovery=False)


def _set_permissions(file_id: str):
    """Comparte recurso con todos los usuarios según rol."""
    drive = _drive_service()
    User = get_user_model()
    for user in User.objects.all():
        role = 'writer' if user.rol in (Rol.SUPERADMIN, Rol.MINIADMIN) else 'reader'
        perm = {
            'type': 'user',
            'role': role,
            'emailAddress': user.email,
        }
        drive.permissions().create(
            fileId=file_id,
            body=perm,
            sendNotificationEmail=False
        ).execute()


def generate_id_factor() -> str:
    """Genera un ID aleatorio de 10 caracteres para Factor."""
    return uuid.uuid4().hex[:10]


class Factor(models.Model):
    STATUS_CHOICES = [
        ('pending',  'Pendiente'),
        ('approved', 'Aprobado'),
        ('rejected', 'Rechazado'),
    ]

    id_factor    = models.CharField(
        primary_key=True,
        max_length=10,
        default=generate_id_factor,
        editable=False
    )
    project      = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name='factors'
    )
    name         = models.CharField(max_length=60, unique=True)
    description  = models.TextField(blank=True)
    start_date   = models.DateField()
    end_date     = models.DateField()
    ponderation  = models.PositiveIntegerField(null=True, blank=True)

    # Campos de Google Docs
    document_id   = models.CharField(max_length=80, blank=True, null=True)
    document_link = models.URLField(blank=True, null=True)

    status         = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default='pending'
    )
    is_completed   = models.BooleanField(default=False)
    responsables   = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        blank=True,
        related_name='responsible_factors',
        verbose_name='Responsables'
    )

    class Meta:
        ordering = ['project__name', 'start_date', 'name']

    @property
    def approved_percentage(self) -> int:
        total = Aspect.objects.filter(trait__factor=self).count()
        if not total:
            return 0
        ok = Aspect.objects.filter(trait__factor=self, approved=True).count()
        return int(ok * 100 / total)

    def clean(self):
        """Valida que las fechas estén dentro del rango del proyecto."""
        errors = {}
        if self.start_date < self.project.start_date:
            errors['start_date'] = 'No puede iniciar antes que el proyecto.'
        if self.end_date > self.project.end_date:
            errors['end_date']   = 'No puede terminar después que el proyecto.'
        if errors:
            from django.core.exceptions import ValidationError
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        """Cuando se crea un factor, genera y comparte su Docs sólo con el creador."""
        is_new = self._state.adding and not self.document_id

        # 1) Validación y estado de completitud
        self.full_clean()
        self.is_completed = (self.approved_percentage == 100)
        super().save(*args, **kwargs)

        if is_new:
            # 2) Crear el Google Doc
            docs = _docs_service()
            doc = docs.documents().create(body={'title': self.name}).execute()
            doc_id = doc['documentId']

            # 3) Moverlo a la carpeta del proyecto
            drive = _drive_service()
            drive.files().update(
                fileId=doc_id,
                addParents=self.project.folder_id,
                removeParents='root',
                fields='id, parents'
            ).execute()

            # 4) Compartir *sólo* con el creador si se inyectó el email;
            #    si no, por compatibilidad, se usa el método anterior.
            if hasattr(self, '_creator_email'):
                perm = {
                    'type':         'user',
                    'role':         'writer',
                    'emailAddress': self._creator_email,
                }
                drive.permissions().create(
                    fileId=doc_id,
                    body=perm,
                    sendNotificationEmail=False
                ).execute()
            else:
                _set_permissions(doc_id)

            # 5) Guardar referencias en BD
            self.document_id   = doc_id
            self.document_link = f'https://docs.google.com/document/d/{doc_id}/edit'
            super().save(update_fields=['document_id', 'document_link'])

        # 6) Actualizar progreso del proyecto
        self.project.update_progress(save_instance=True)


    def __str__(self):
        return self.name
