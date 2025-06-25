# attachGeneric/views.py
import io
import os
import logging
from pyexpat.errors import messages 

from django.contrib.auth import get_user_model
from django.http import JsonResponse
from django.shortcuts import redirect, render, get_object_or_404
from django.contrib.contenttypes.models import ContentType
from django.conf import settings
from django.db import transaction
from django.urls import reverse

try:
    from calendar_create_event.models import Event
except ImportError:
    Event = None
    logging.info("Modelo Event de calendar_create_event no encontrado.")

from core.permissions import can_edit, get_trait_permission
from database.models import File 
from traitManager.models import Trait 

try:
    from factorManager.models import _drive_service, _set_permissions 
    from googleapiclient.http import MediaIoBaseUpload
    GOOGLE_DRIVE_ENABLED = True
except ImportError:
    _drive_service = None
    _set_permissions = None
    MediaIoBaseUpload = None
    GOOGLE_DRIVE_ENABLED = False
    logging.warning("Utilidades de Google Drive no pudieron ser importadas. Funcionalidad de Drive desactivada.")

logger = logging.getLogger(__name__)
User = get_user_model()

def get_or_create_drive_folder(drive, parent_folder_id: str, sub_folder_name: str) -> str:
    if not GOOGLE_DRIVE_ENABLED or not drive:
        logger.error("Google Drive no está habilitado o el servicio no está disponible.")
        raise Exception("Servicio de Google Drive no disponible.")
    q = (
        f"name = '{sub_folder_name}' and "
        f"mimeType = 'application/vnd.google-apps.folder' and "
        f"'{parent_folder_id}' in parents and trashed = false"
    )
    try:
        results = drive.files().list(q=q, spaces='drive', fields='files(id)').execute()
        existing_folders = results.get('files', [])
        if existing_folders:
            return existing_folders[0]['id']
        folder_metadata = {
            'name': sub_folder_name,
            'mimeType': 'application/vnd.google-apps.folder',
            'parents': [parent_folder_id]
        }
        folder = drive.files().create(body=folder_metadata, fields='id').execute()
        logger.info(f"Subcarpeta '{sub_folder_name}' creada en Drive con ID: {folder.get('id')}")
        return folder.get('id')
    except Exception as e:
        logger.error(f"Error al buscar/crear subcarpeta '{sub_folder_name}' en Drive: {str(e)}", exc_info=True)
        raise 

def attachGeneric(request):
    return render(request, 'attachGeneric/attach.html')

def attach_generic_trait(request, pk):
    trait = get_object_or_404(Trait, pk=pk)
    return render(request, 'attachGeneric/attach.html', {
        'evento': trait,
        'trait':  trait,
    })

def obtener_directores_programa(request):
    try:
        directores = User.objects.filter(rol='superadmin', is_active=True).order_by('first_name', 'last_name')
        if not directores.exists():
            logger.warning("OBTENER_DIRECTORES: No se encontraron directores activos con rol 'superadmin'.")
            return JsonResponse([], safe=False) 
        data = []
        for director in directores:
            if director.cedula and director.first_name and director.last_name:
                data.append({'id': director.cedula, 'nombre': f'{director.first_name} {director.last_name}'.strip()})
            else:
                logger.warning(f"OBTENER_DIRECTORES: Director {director.cedula} omitido por datos incompletos.")
        logger.info(f"OBTENER_DIRECTORES: Se encontraron {len(data)} directores.")
        return JsonResponse(data, safe=False)
    except Exception as e:
        logger.error(f"OBTENER_DIRECTORES: Error crítico: {str(e)}", exc_info=True)
        return JsonResponse({'error': 'Error interno al obtener directores.'}, status=500)

@transaction.atomic 
def guardar_archivos_adjuntos(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Método no permitido.'}, status=405)

    try:
        logger.info("GUARDAR_ARCHIVOS: Iniciando proceso de guardado.")
        archivos_recibidos = request.FILES.getlist('archivos')
        if not archivos_recibidos:
            logger.warning("GUARDAR_ARCHIVOS: No se recibieron archivos.")
            return JsonResponse({'error': 'No se recibieron archivos.'}, status=400)

        MAX_SIZE = 10 * 1024 * 1024
        for f in archivos_recibidos:
            if f.size > MAX_SIZE:
                size_mb = round(f.size / (1024*1024), 2)
                logger.warning(f"GUARDAR_ARCHIVOS: Archivo '{f.name}' excede tamaño. Tamaño: {size_mb}MB.")
                return JsonResponse({'error': f"ERROR: El archivo '{f.name}' pesa {size_mb} MB — el límite es 10 MB."}, status=400)

        director_programa_id = request.POST.get('directorPrograma')
        if not director_programa_id or director_programa_id == 'Seleccionar...':
            logger.warning("GUARDAR_ARCHIVOS: Director de programa no seleccionado.")
            return JsonResponse({'error': 'Por favor, seleccione un director de programa.'}, status=400)

        try:
            director_user = User.objects.get(cedula=director_programa_id)
            director_programa_nombre_completo = f"{director_user.first_name} {director_user.last_name}".strip()
            if not director_programa_nombre_completo:
                 logger.error(f"GUARDAR_ARCHIVOS: Director {director_programa_id} no tiene nombre.")
                 return JsonResponse({'error': 'El director de programa seleccionado tiene datos incompletos.'}, status=400)
        except User.DoesNotExist:
            logger.error(f"GUARDAR_ARCHIVOS: Director con cédula '{director_programa_id}' no encontrado.")
            return JsonResponse({'error': 'El director de programa seleccionado no es válido.'}, status=400)
        logger.info(f"GUARDAR_ARCHIVOS: Director seleccionado: {director_programa_nombre_completo} ({director_programa_id})")

        origen_id = request.POST.get('id_evento') 
        logger.info(f"GUARDAR_ARCHIVOS: ID de origen (evento/trait): {origen_id}")
        content_type_for_file = None
        object_id_for_file = None
        event_fk_instance = None

        if origen_id:
            try:
                trait_instance = Trait.objects.get(pk=origen_id)
                content_type_for_file = ContentType.objects.get_for_model(Trait)
                object_id_for_file = trait_instance.pk
                logger.info(f"GUARDAR_ARCHIVOS: Vinculado a Trait ID: {object_id_for_file}")
            except (Trait.DoesNotExist, ValueError): 
                if Event: 
                    try:
                        event_instance = Event.objects.get(id_event=origen_id) 
                        event_fk_instance = event_instance 
                        logger.info(f"GUARDAR_ARCHIVOS: Vinculado a Event ID: {event_instance.pk if hasattr(event_instance, 'pk') else 'N/A'}")
                    except (Event.DoesNotExist, ValueError):
                        logger.warning(f"GUARDAR_ARCHIVOS: ID de origen '{origen_id}' no es Trait ni Event válido.")
                        return JsonResponse({'error': f'El objeto asociado con ID "{origen_id}" no existe o el ID es inválido.'}, status=400)
                else: 
                    logger.warning(f"GUARDAR_ARCHIVOS: ID de origen '{origen_id}' no es Trait y Event model no disponible.")
                    return JsonResponse({'error': f'El objeto Trait asociado con ID "{origen_id}" no existe o el ID es inválido.'}, status=400)
        
        drive_service = None
        target_drive_folder_id = None 

        if GOOGLE_DRIVE_ENABLED and _drive_service and hasattr(settings, 'GOOGLE_DRIVE_ATTACHGENERIC_FOLDER_ID') and settings.GOOGLE_DRIVE_ATTACHGENERIC_FOLDER_ID:
            try:
                drive_service = _drive_service()
                target_drive_folder_id = get_or_create_drive_folder(drive_service, settings.GOOGLE_DRIVE_ATTACHGENERIC_FOLDER_ID, 'archivos')
                logger.info(f"GUARDAR_ARCHIVOS: Carpeta de Drive para adjuntos ('archivos'): {target_drive_folder_id}")
            except Exception as e_drive_setup:
                logger.error(f"GUARDAR_ARCHIVOS: Error configurando Google Drive: {str(e_drive_setup)}", exc_info=True)
                drive_service = None 
        elif GOOGLE_DRIVE_ENABLED:
            logger.warning("GUARDAR_ARCHIVOS: Drive habilitado pero _drive_service o GOOGLE_DRIVE_ATTACHGENERIC_FOLDER_ID faltan.")

        files_saved_details = []
        for archivo_subido in archivos_recibidos:
            nombre_original = archivo_subido.name
            nombre_sin_extension, extension = os.path.splitext(nombre_original)
            tipo_archivo = extension[1:].lower()
            logger.info(f"GUARDAR_ARCHIVOS: Procesando archivo '{nombre_original}' tipo '{tipo_archivo}'.")

            if tipo_archivo not in ['pdf', 'zip']:
                logger.warning(f"GUARDAR_ARCHIVOS: Tipo de archivo no permitido: {nombre_original}")
                return JsonResponse({'error': f'Tipo de archivo no permitido: {nombre_original}'}, status=400)

            drive_link = None 
            if drive_service and target_drive_folder_id and MediaIoBaseUpload:
                try:
                    logger.info(f"GUARDAR_ARCHIVOS: Intentando subir '{nombre_original}' a Drive.")
                    file_metadata_drive = {'name': nombre_original, 'parents': [target_drive_folder_id]}
                    archivo_subido.seek(0) 
                    media_drive = MediaIoBaseUpload(io.BytesIO(archivo_subido.read()), mimetype=archivo_subido.content_type, resumable=True)
                    gfile = drive_service.files().create(body=file_metadata_drive, media_body=media_drive, fields='id, webViewLink').execute()
                    file_id_on_drive = gfile.get('id')
                    drive_link = gfile.get('webViewLink') 
                    if _set_permissions:
                        _set_permissions(file_id_on_drive)
                    logger.info(f"GUARDAR_ARCHIVOS: Archivo '{nombre_original}' subido a Drive. Link: {drive_link}")
                except Exception as e_drive_upload:
                    logger.error(f"GUARDAR_ARCHIVOS: Error al subir '{nombre_original}' a Drive: {str(e_drive_upload)}", exc_info=True)
            
            archivo_subido.seek(0) # Rebobinar para guardado local

            logger.info(f"GUARDAR_ARCHIVOS: Preparando para guardar '{nombre_original}' en la base de datos.")
            file_instance_data = {
                'name': nombre_sin_extension,
                'type': tipo_archivo,
                'director_programa': director_programa_nombre_completo,
                'status': 'activo',
                'content_type': content_type_for_file, 
                'object_id': object_id_for_file,       
                'id_event': event_fk_instance,         
                'drive_link': drive_link               
            }
            logger.debug(f"GUARDAR_ARCHIVOS: Datos para File model: {file_instance_data}")
            
            file_instance = File(
                #archivo=archivo_subido, # El campo FileField se pasa al crear la instancia
                **file_instance_data
            )
            
            try:
                file_instance.save()
                logger.info(f"GUARDAR_ARCHIVOS: Archivo '{nombre_original}' guardado en BD con PK: {file_instance.pk}")
                files_saved_details.append({'name': nombre_original, 'status': 'guardado', 'drive_link': drive_link})
            except Exception as db_error:
                logger.error(f"GUARDAR_ARCHIVOS: Error al guardar '{nombre_original}' en BD: {str(db_error)}", exc_info=True)
                # Si un archivo falla al guardar en BD, la transacción se revierte.
                # Podrías devolver un error específico aquí o dejar que el try/except general lo capture.
                # Por ahora, para depurar, es mejor que el error específico se registre y se lance.
                raise # Re-lanzar para que el try/except general lo capture y devuelva un 500 claro.


        logger.info("GUARDAR_ARCHIVOS: Proceso completado exitosamente.")
        return JsonResponse({'mensaje': 'Archivos guardados exitosamente.', 'files': files_saved_details})

    except Exception as e:
        logger.error(f"GUARDAR_ARCHIVOS: Error GENERAL no capturado previamente: {str(e)}", exc_info=True)
        # Este JsonResponse es el que debería ver el frontend si todo lo demás falla.
        return JsonResponse({'error': 'Ocurrió un error inesperado y grave en el servidor al procesar los archivos.'}, status=500)


def delete_attachment(request, file_pk):
    file_instance = get_object_or_404(File, pk=file_pk)
    trait_instance = None
    redirect_url = 'home' # URL de fallback

    # Verificar que el archivo está correctamente asociado a un Trait
    if file_instance.content_type == ContentType.objects.get_for_model(Trait) and file_instance.object_id:
        try:
            trait_instance = Trait.objects.get(pk=file_instance.object_id)
            redirect_url = reverse('trait_detail', kwargs={'pk': trait_instance.pk})
        except Trait.DoesNotExist:
            messages.error(request, "La característica asociada a este archivo no fue encontrada.")
            return redirect(redirect_url)
    else:
        messages.error(request, "Este archivo no está correctamente asociado a una característica.")
        return redirect(redirect_url)

    # Verificar permisos del usuario sobre el Trait
    user_trait_role = get_trait_permission(request.user, trait_instance)
    if not can_edit(user_trait_role): # can_edit implica rol de Editor
        messages.error(request, "No tienes permiso para eliminar archivos de esta característica.")
        return redirect(redirect_url)

    if request.method == 'POST':
        file_name_display = f"{file_instance.name}.{file_instance.type}"
        
        # 1. Eliminar de Google Drive si existe el enlace
        if file_instance.drive_link and file_instance.drive_link.strip():
            try:
                drive_file_id = None
                # Intenta extraer el ID del archivo de Drive del webViewLink
                # Formato típico: https://docs.google.com/document/d/FILE_ID/edit
                # O para otros archivos: https://drive.google.com/file/d/FILE_ID/view
                parts = file_instance.drive_link.split('/')
                if 'd' in parts:
                    id_index = parts.index('d') + 1
                    if id_index < len(parts):
                        drive_file_id = parts[id_index]
                
                if drive_file_id:
                    drive = _drive_service() # Asumiendo que _drive_service() está disponible aquí [cite: 277]
                    drive.files().delete(fileId=drive_file_id).execute()
                    logger.info(f"DELETE_ATTACHMENT: Archivo '{drive_file_id}' (parte de {file_name_display}) eliminado de Google Drive.")
                else:
                    logger.warning(f"DELETE_ATTACHMENT: No se pudo extraer el ID de Drive del enlace: {file_instance.drive_link} para el archivo {file_name_display}")
            except Exception as e:
                logger.error(f"DELETE_ATTACHMENT: Error al eliminar de Drive el archivo '{file_name_display}' con enlace {file_instance.drive_link}: {str(e)}")
                messages.warning(request, f"No se pudo eliminar completamente el archivo '{file_name_display}' de Google Drive. Puede requerir eliminación manual en Drive.")

        # 2. Eliminar el archivo local si existe (ya no debería crearse para nuevas subidas via attachGeneric)
        if file_instance.archivo and hasattr(file_instance.archivo, 'path'):
            try:
                if os.path.exists(file_instance.archivo.path): # Verificar si el archivo realmente existe
                    file_instance.archivo.delete(save=False) # save=False porque el modelo se elimina después
                    logger.info(f"DELETE_ATTACHMENT: Archivo local '{file_instance.archivo.name}' eliminado para {file_name_display}.")
            except Exception as e:
                logger.error(f"DELETE_ATTACHMENT: Error al eliminar archivo local '{file_instance.archivo.name}' para {file_name_display}: {str(e)}")

        # 3. Eliminar la instancia del modelo File
        file_instance.delete()
        logger.info(f"DELETE_ATTACHMENT: Registro del archivo '{file_name_display}' eliminado de la base de datos.")
        messages.success(request, f"Archivo adjunto '{file_name_display}' eliminado correctamente.")
    else:
        # Solo permitir POST para la eliminación por seguridad.
        messages.error(request, "Método no permitido para eliminar el archivo.")

    return redirect(redirect_url)