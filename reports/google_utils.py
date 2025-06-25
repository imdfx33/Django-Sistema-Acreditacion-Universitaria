# reports/google_utils.py
# Este archivo contendrá funciones de utilidad para interactuar con las APIs de Google.
# El comando de gestión lo importará.

import io
import logging
from django.conf import settings
from google.oauth2 import service_account
from googleapiclient.discovery import build, Resource
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaIoBaseDownload, MediaIoBaseUpload # CORREGIDO: MediaFileUpload no se usa directamente para BytesIO

logger = logging.getLogger(__name__)

SCOPES_DRIVE = settings.GOOGLE_DRIVE_SCOPES
SCOPES_DOCS = getattr(settings, 'GOOGLE_DOCS_SCOPES', ['https://www.googleapis.com/auth/documents'])
SERVICE_ACCOUNT_FILE = settings.GOOGLE_SERVICE_ACCOUNT_FILE

def get_google_service(api_name: str, api_version: str, scopes: list) -> Resource | None:
    """
    Crea y devuelve un cliente de servicio de Google API.
    """
    try:
        creds = service_account.Credentials.from_service_account_file(
            SERVICE_ACCOUNT_FILE, scopes=scopes
        )
        service = build(api_name, api_version, credentials=creds, cache_discovery=False)
        return service
    except Exception as e:
        logger.error(f"Error al inicializar el servicio de Google {api_name.capitalize()}: {e}", exc_info=True)
        return None

def get_drive_service() -> Resource | None:
    """Devuelve el servicio de Google Drive."""
    return get_google_service('drive', 'v3', SCOPES_DRIVE)

def get_docs_service() -> Resource | None:
    """Devuelve el servicio de Google Docs."""
    return get_google_service('docs', 'v1', SCOPES_DOCS)

def list_files_in_folder(drive_service: Resource, folder_id: str, mime_type: str = None) -> list:
    """
    Lista archivos en una carpeta de Google Drive, opcionalmente filtrando por mimeType.
    """
    query = f"'{folder_id}' in parents and trashed = false"
    if mime_type:
        query += f" and mimeType = '{mime_type}'"
    
    files = []
    page_token = None
    try:
        while True:
            response = drive_service.files().list(
                q=query,
                spaces='drive',
                fields='nextPageToken, files(id, name, webViewLink, mimeType)',
                pageToken=page_token
            ).execute()
            files.extend(response.get('files', []))
            page_token = response.get('nextPageToken', None)
            if page_token is None:
                break
    except HttpError as error:
        logger.error(f"Error listando archivos en la carpeta {folder_id}: {error}", exc_info=True)
    return files

def download_google_doc_content(docs_service: Resource, document_id: str) -> str:
    """
    Descarga el contenido de un Google Doc como texto plano.
    Retorna el texto del documento o una cadena vacía si hay error.
    """
    content_text = ""
    try:
        document = docs_service.documents().get(documentId=document_id).execute()
        doc_content = document.get('body').get('content')
        for element in doc_content:
            if 'paragraph' in element:
                for pe in element.get('paragraph').get('elements'):
                    if 'textRun' in pe:
                        content_text += pe.get('textRun').get('content')
            # Podríamos añadir manejo para tablas, listas, etc. si es necesario.
            # Por ahora, solo texto plano de párrafos.
    except HttpError as error:
        logger.error(f"Error descargando contenido del Google Doc ID {document_id}: {error}", exc_info=True)
    except Exception as e:
        logger.error(f"Excepción inesperada descargando Google Doc ID {document_id}: {e}", exc_info=True)
    return content_text

def create_google_doc(docs_service: Resource, title: str, parent_folder_id: str = None) -> dict | None:
    """
    Crea un nuevo Google Doc.
    Si se proporciona parent_folder_id, el documento se crea en esa carpeta.
    """
    try:
        body = {'title': title}
        doc = docs_service.documents().create(body=body).execute()
        logger.info(f"Google Doc '{title}' creado con ID: {doc.get('documentId')}")
        
        if parent_folder_id:
            drive_service = get_drive_service()
            if drive_service:
                file_id = doc.get('documentId')
                # El archivo se crea en la raíz, necesitamos moverlo.
                file = drive_service.files().get(fileId=file_id, fields='parents').execute()
                previous_parents = ",".join(file.get('parents'))
                drive_service.files().update(
                    fileId=file_id,
                    addParents=parent_folder_id,
                    removeParents=previous_parents, # Quitar de la raíz si es necesario
                    fields='id, parents'
                ).execute()
                logger.info(f"Documento {file_id} movido a la carpeta {parent_folder_id}.")
        return doc
    except HttpError as error:
        logger.error(f"Error creando Google Doc '{title}': {error}", exc_info=True)
        return None

def batch_update_google_doc(docs_service: Resource, document_id: str, requests: list) -> bool:
    """
    Aplica una lista de requests de actualización a un Google Doc.
    """
    if not requests:
        return True
    try:
        docs_service.documents().batchUpdate(
            documentId=document_id, body={'requests': requests}
        ).execute()
        logger.info(f"Batch update aplicado al Google Doc ID {document_id}.")
        return True
    except HttpError as error:
        logger.error(f"Error en batchUpdate para Google Doc ID {document_id}: {error}", exc_info=True)
        return False

def export_doc_as_pdf(drive_service: Resource, document_id: str) -> bytes | None:
    """
    Exporta un Google Doc a formato PDF y devuelve los bytes del PDF.
    """
    try:
        request = drive_service.files().export_media(fileId=document_id, mimeType='application/pdf')
        fh = io.BytesIO()
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while not done:
            status, done = downloader.next_chunk()
            logger.debug(f"Descarga de PDF para Doc ID {document_id}: {int(status.progress() * 100)}%.")
        fh.seek(0)
        return fh.getvalue()
    except HttpError as error:
        logger.error(f"Error exportando Google Doc ID {document_id} a PDF: {error}", exc_info=True)
        return None

def upload_file_to_drive(drive_service: Resource, file_name: str, mime_type: str, file_bytes: bytes, folder_id: str) -> dict | None:
    """
    Sube un archivo (en bytes) a una carpeta específica en Google Drive.
    """
    try:
        file_metadata = {
            'name': file_name,
            'parents': [folder_id]
        }
        # --- INICIO DE LA CORRECCIÓN ---
        # Usar MediaIoBaseUpload para subir desde un objeto io.BytesIO
        fh = io.BytesIO(file_bytes)
        media = MediaIoBaseUpload(fd=fh, mimetype=mime_type, resumable=True)
        # --- FIN DE LA CORRECCIÓN ---
        
        file = drive_service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id, webViewLink, webContentLink' # webViewLink es para ver, webContentLink es para descarga directa si está habilitado
        ).execute()
        logger.info(f"Archivo '{file_name}' subido a Drive con ID: {file.get('id')}")
        return file
    except HttpError as error:
        logger.error(f"Error subiendo archivo '{file_name}' a Drive: {error}", exc_info=True)
        return None
    except Exception as e: # Captura general para otros posibles errores con BytesIO o MediaIoBaseUpload
        logger.error(f"Error inesperado subiendo archivo '{file_name}': {e}", exc_info=True)
        return None


def set_file_public_readable(drive_service: Resource, file_id: str) -> bool:
    """
    Hace un archivo en Google Drive públicamente legible (cualquiera con el enlace puede ver).
    """
    try:
        permission = {'type': 'anyone', 'role': 'reader'}
        drive_service.permissions().create(fileId=file_id, body=permission).execute()
        logger.info(f"Permisos públicos de lectura establecidos para el archivo ID {file_id}.")
        return True
    except HttpError as error:
        logger.error(f"Error estableciendo permisos públicos para el archivo ID {file_id}: {error}", exc_info=True)
        return False
