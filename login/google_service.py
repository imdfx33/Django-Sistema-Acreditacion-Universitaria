# login/google_service.py

from django.conf import settings
from google.oauth2 import service_account
from googleapiclient.discovery import build

def _drive_service():
    """
    Construye y devuelve el cliente de Google Drive usando la Service Account.
    """
    creds = service_account.Credentials.from_service_account_file(
        settings.GOOGLE_SERVICE_ACCOUNT_FILE,
        scopes=settings.GOOGLE_DRIVE_SCOPES
    )
    return build('drive', 'v3', credentials=creds, cache_discovery=False)
