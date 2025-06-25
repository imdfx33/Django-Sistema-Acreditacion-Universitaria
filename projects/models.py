import uuid
from django.db import models
from django.conf import settings
from google.oauth2 import service_account
from googleapiclient.discovery import build

# Google Drive credentials
SCOPES = settings.GOOGLE_DRIVE_SCOPES + getattr(settings, 'GOOGLE_DOCS_SCOPES', [])
SERVICE_ACCOUNT_FILE = settings.GOOGLE_SERVICE_ACCOUNT_FILE

def _drive_service():
    creds = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE,
        scopes=SCOPES
    )
    return build('drive', 'v3', credentials=creds, cache_discovery=False)

def _set_initial_permissions_for_creator(file_id: str, creator_email: str):
    drive = _drive_service()
    perm = {
        'type': 'user',
        'role': 'writer',
        'emailAddress': creator_email,
    }
    try:
        drive.permissions().create(
            fileId=file_id,
            body=perm,
            sendNotificationEmail=False
        ).execute()
    except Exception as e:
        print(f"Error setting initial permission for {creator_email} on {file_id}: {e}")

def _gen_id(n=10):
    return uuid.uuid4().hex[:n]

class Project(models.Model):
    id_project = models.CharField(
        primary_key=True,
        max_length=10,
        default=_gen_id,
        editable=False
    )
    name        = models.CharField(max_length=80, unique=True)
    description = models.TextField("Descripción", blank=True, null=True)
    start_date  = models.DateField()
    end_date    = models.DateField()
    progress    = models.PositiveSmallIntegerField(default=0)
    folder_id   = models.CharField(max_length=100, blank=True, null=True)
    approved    = models.BooleanField("Aprobado", default=False)
    created_by  = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='created_projects'
    )

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name

    def _ensure_folder(self):
        if not self.folder_id and self.created_by:
            drive = _drive_service()
            meta = {
                'name':     self.name,
                'mimeType': 'application/vnd.google-apps.folder',
                'parents':  [settings.GOOGLE_DRIVE_PARENT_FOLDER_ID],
            }
            try:
                folder = drive.files().create(body=meta, fields='id').execute()
                self.folder_id = folder.get('id')
                super().save(update_fields=['folder_id'])
                _set_initial_permissions_for_creator(self.folder_id, self.created_by.email)
            except Exception as e:
                print(f"Error creating Google Drive folder for project {self.name}: {e}")

    def _calc_progress(self) -> int:
        total = self.factors.count()
        if not total:
            return 0
        completed = self.factors.filter(is_completed=True).count()
        return int(completed * 100 / total)

    def update_progress(self, save_instance=False):
        new = self._calc_progress()
        if new != self.progress:
            self.progress = new
            if save_instance:
                super().save(update_fields=['progress'])

    def save(self, *args, **kwargs):
        is_new = self._state.adding
        super().save(*args, **kwargs)
        if is_new and self.created_by:
            self._ensure_folder()