# assignments/views.py
import json
import traceback
import logging

from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import JsonResponse, HttpResponseForbidden, HttpResponseBadRequest
from django.db import transaction
from django.conf import settings
from django.contrib import messages # Para mensajes al usuario

from googleapiclient.errors import HttpError

# Asegúrate que Project y Factor están correctamente importados
from projects.models import Project 
from factorManager.models import Factor # Si se usa en otras partes de este archivo

# Importa _drive_service desde projects.models o donde esté definido centralmente
# para asegurar que usas la misma instancia/configuración.
from projects.models import _drive_service as get_drive_service 

from .models import ProjectAssignment, FactorAssignment, AssignmentRole
from login.models import Rol, User # User es settings.AUTH_USER_MODEL

logger = logging.getLogger(__name__)

# --- Helpers de Permisos ---
def is_super_admin_or_akadi(user):
    return user.is_authenticated and user.has_elevated_permissions

def is_super_admin_akadi_or_mini_admin(user):
    return user.is_authenticated and (user.has_elevated_permissions or user.is_mini_admin_role)

# --- Vistas de API ---

@login_required
@user_passes_test(is_super_admin_or_akadi) # Solo SuperAdmin/Akadi pueden ver todos los proyectos para asignar
def api_projects_for_assignment(request):
    """
    API para SuperAdmins/Akadi: Devuelve todos los proyectos.
    Usado cuando un SuperAdmin va a asignar un proyecto a un MiniAdmin.
    """
    try:
        projects = Project.objects.all().order_by('name')
        data = [{'id': p.id_project, 'name': p.name} for p in projects]
        return JsonResponse(data, safe=False)
    except Exception as e:
        logger.error(f"Error en api_projects_for_assignment: {e}\n{traceback.format_exc()}")
        return JsonResponse({'error': 'Error cargando proyectos'}, status=500)

@login_required
@user_passes_test(is_super_admin_akadi_or_mini_admin)
def api_projects_for_mini_admin_factor_assignment(request):
    """
    API para MiniAdmins (y SuperAdmin/Akadi):
    - SuperAdmin/Akadi: Ven todos los proyectos.
    - MiniAdmin: Ven solo los proyectos que tienen asignados con rol EDITOR.
                 (Porque solo en esos pueden gestionar factores y asignar usuarios a factores).
    Usado en la pestaña "Asignar Factor" para que el MiniAdmin seleccione un proyecto.
    """
    user = request.user
    try:
        if user.has_elevated_permissions:
            projects = Project.objects.all().order_by('name')
        elif user.is_mini_admin_role:
            # MiniAdmin solo puede asignar factores en proyectos donde es EDITOR
            assigned_project_ids = ProjectAssignment.objects.filter(
                user=user,
                role=AssignmentRole.EDITOR
            ).values_list('project_id', flat=True)
            projects = Project.objects.filter(id_project__in=assigned_project_ids).order_by('name')
        else:
            return JsonResponse({'error': 'Acceso no autorizado'}, status=403)
            
        data = [{'id': p.id_project, 'name': p.name} for p in projects]
        return JsonResponse(data, safe=False)
    except Exception as e:
        logger.error(f"Error en api_projects_for_mini_admin_factor_assignment: {e}\n{traceback.format_exc()}")
        return JsonResponse({'error': 'Error cargando proyectos para asignación de factor'}, status=500)


@login_required
@user_passes_test(is_super_admin_or_akadi) # Solo SuperAdmin/Akadi asignan proyectos a MiniAdmins
def api_mini_admin_users(request):
    """
    Devuelve una lista de usuarios que son MiniAdmin.
    Usado por SuperAdmin/Akadi para seleccionar a quién asignar un proyecto.
    """
    try:
        minis = User.objects.filter(rol=Rol.MINIADMIN, is_active=True).order_by('first_name', 'last_name')
        data = [{'id': u.cedula, 'name': u.get_full_name} for u in minis]
        return JsonResponse(data, safe=False)
    except Exception as e:
        logger.error(f"Error en api_mini_admin_users: {e}\n{traceback.format_exc()}")
        return JsonResponse({'error': 'Error cargando MiniAdmins'}, status=500)


@login_required
@user_passes_test(is_super_admin_akadi_or_mini_admin)
def api_assignable_users_for_factor(request):
    """
    Devuelve usuarios a los que se les puede asignar un Factor.
    Excluye SuperAdmins, MiniAdmins y Akadi.
    """
    try:
        excluded_roles = [Rol.SUPERADMIN, Rol.MINIADMIN, Rol.ACADI]
        users = User.objects.filter(is_active=True).exclude(rol__in=excluded_roles).order_by('first_name', 'last_name')
        data = [{'id': u.cedula, 'name': u.get_full_name} for u in users]
        return JsonResponse(data, safe=False)
    except Exception as e:
        logger.error(f"Error en api_assignable_users_for_factor: {e}\n{traceback.format_exc()}")
        return JsonResponse({'error': 'Error cargando usuarios asignables'}, status=500)


@login_required
@user_passes_test(is_super_admin_akadi_or_mini_admin)
def api_factors_for_assignment(request, project_id):
    """
    Devuelve factores de un proyecto específico.
    MiniAdmin debe tener acceso al proyecto (se asume que el project_id ya fue filtrado).
    """
    user = request.user
    project = get_object_or_404(Project, id_project=project_id)

    # Verificar si el MiniAdmin tiene acceso a este proyecto (si no es SuperAdmin/Akadi)
    if not user.has_elevated_permissions and user.is_mini_admin_role:
        can_access_project = ProjectAssignment.objects.filter(
            user=user, 
            project=project,
            # MiniAdmin necesita ser al menos lector del proyecto para ver sus factores para asignar
            # pero para ASIGNAR factores, idealmente debería ser EDITOR del proyecto.
            # Esta verificación es más estricta si se requiere que sea editor para gestionar factores.
            role__in=[AssignmentRole.EDITOR, AssignmentRole.COMENTADOR, AssignmentRole.LECTOR] 
        ).exists()
        if not can_access_project:
             return JsonResponse({'error': 'No tienes permiso para ver factores de este proyecto.'}, status=403)
    try:
        factors = Factor.objects.filter(project=project).order_by('name')
        data = [{'id': f.id_factor, 'name': f.name} for f in factors]
        return JsonResponse(data, safe=False)
    except Exception as e:
        logger.error(f"Error en api_factors_for_assignment: {e}\n{traceback.format_exc()}")
        return JsonResponse({'error': 'Error cargando factores'}, status=500)

@login_required
@user_passes_test(is_super_admin_akadi_or_mini_admin)
def api_project_assignments_for_project(request, project_id):
    """Devuelve las asignaciones de MiniAdmins para un proyecto específico."""
    project = get_object_or_404(Project, id_project=project_id)
    # Solo mostrar asignaciones de MiniAdmins para este proyecto
    assignments = ProjectAssignment.objects.filter(project=project, user__rol=Rol.MINIADMIN).select_related('user')
    data = [{'user_id': a.user.cedula, 'role': a.role} for a in assignments]
    return JsonResponse(data, safe=False)


@login_required
@user_passes_test(is_super_admin_akadi_or_mini_admin)
def api_factor_assignments_for_factor(request, factor_id):
    """Devuelve las asignaciones de usuarios (no admins) para un factor específico."""
    factor = get_object_or_404(Factor, id_factor=factor_id)
    excluded_roles = [Rol.SUPERADMIN, Rol.MINIADMIN, Rol.ACADI]
    assignments = FactorAssignment.objects.filter(factor=factor).exclude(user__rol__in=excluded_roles).select_related('user')
    data = [{'user_id': a.user.cedula, 'role': a.role} for a in assignments]
    return JsonResponse(data, safe=False)

# --- Vista Principal de Asignaciones ---
@login_required
@user_passes_test(is_super_admin_akadi_or_mini_admin) # Solo admins pueden acceder a la página de asignaciones
def assignments_page(request):
    context = {
        'is_super_admin_or_akadi': is_super_admin_or_akadi(request.user),
        'is_mini_admin': request.user.is_mini_admin_role
    }
    return render(request, 'assignments/assignments.html', context)

# --- Lógica de Asignación (POST) ---

def _update_drive_permission(drive_service, file_id, user_email, new_app_role_str, current_drive_permissions_map):
    """
    Actualiza o crea un permiso en Google Drive para un usuario y archivo/carpeta dados.
    Si new_app_role_str es None o no mapea a un rol de Drive, elimina el permiso existente.
    """
    google_role_map = {
        AssignmentRole.LECTOR: 'reader',
        AssignmentRole.COMENTADOR: 'commenter',
        AssignmentRole.EDITOR: 'writer',
    }
    target_google_role = google_role_map.get(new_app_role_str) if new_app_role_str else None
    user_email_lower = user_email.lower()
    existing_perm_details = current_drive_permissions_map.get(user_email_lower)

    logger.info(f"Drive Update: FileID='{file_id}', User='{user_email}', AppRole='{new_app_role_str}', TargetDriveRole='{target_google_role}', ExistingPerm='{bool(existing_perm_details)}'")

    if not target_google_role: # Intención de remover el permiso o rol no válido
        if existing_perm_details:
            logger.info(f"Drive: Intentando eliminar permiso para '{user_email_lower}' en FileID '{file_id}' (PermID: {existing_perm_details['id']})")
            try:
                drive_service.permissions().delete(fileId=file_id, permissionId=existing_perm_details['id']).execute()
                logger.info(f"Drive: Permiso eliminado para '{user_email_lower}' en FileID '{file_id}'.")
            except HttpError as e:
                logger.error(f"Drive: ERROR al eliminar permiso para '{user_email_lower}' en FileID '{file_id}'. Código: {e.resp.status}, Razón: {e._get_reason()}")
        else:
            logger.info(f"Drive: No se encontró permiso existente para '{user_email_lower}' en FileID '{file_id}' para eliminar.")
        return

    # Si llegamos aquí, target_google_role es válido (reader, commenter, o writer)
    if existing_perm_details:
        if existing_perm_details.get('role') != target_google_role:
            logger.info(f"Drive: Intentando actualizar permiso para '{user_email_lower}' en FileID '{file_id}' de '{existing_perm_details.get('role')}' a '{target_google_role}' (PermID: {existing_perm_details['id']})")
            try:
                drive_service.permissions().update(
                    fileId=file_id,
                    permissionId=existing_perm_details['id'],
                    body={'role': target_google_role},
                    # transferOwnership=False # Es buena práctica incluirlo si no se pretende transferir
                ).execute()
                logger.info(f"Drive: Permiso actualizado para '{user_email_lower}' en FileID '{file_id}'.")
            except HttpError as e:
                logger.error(f"Drive: ERROR al actualizar permiso para '{user_email_lower}' en FileID '{file_id}'. Código: {e.resp.status}, Razón: {e._get_reason()}")
        else:
            logger.info(f"Drive: Permiso para '{user_email_lower}' en FileID '{file_id}' ya está correcto ('{target_google_role}'). No se necesita acción.")
    else:
        logger.info(f"Drive: Intentando crear permiso para '{user_email_lower}' en FileID '{file_id}' con rol '{target_google_role}'.")
        try:
            drive_service.permissions().create(
                fileId=file_id,
                body={'type': 'user', 'role': target_google_role, 'emailAddress': user_email}, # Usar el email original, no lowercased, para la creación
                sendNotificationEmail=False
            ).execute()
            logger.info(f"Drive: Permiso creado para '{user_email_lower}' en FileID '{file_id}'.")
        except HttpError as e:
            logger.error(f"Drive: ERROR al crear permiso para '{user_email_lower}' en FileID '{file_id}'. Código: {e.resp.status}, Razón: {e._get_reason()}")



@login_required
@user_passes_test(is_super_admin_or_akadi) 
@transaction.atomic
def assign_project_to_mini_admin(request):
    if request.method != 'POST':
        return HttpResponseForbidden("Método no permitido.")

    try:
        payload = json.loads(request.body)
        project_id = payload.get('project_id')
        # assignments_data: [{'user_id': 'cedula_mini', 'role': 'editor'}, ...]
        assignments_data = payload.get('assignments', []) 
    except json.JSONDecodeError:
        return HttpResponseBadRequest("JSON inválido.")
    
    if not project_id:
        return HttpResponseBadRequest("Falta el ID del proyecto (project_id).")

    project = get_object_or_404(Project, id_project=project_id)
    logger.info(f"Iniciando asignación de proyecto '{project.name}' (ID: {project_id}) a MiniAdmins.")

    drive_service = None
    current_drive_permissions_map = {}
    drive_sync_failed_globally = False

    if project.folder_id:
        try:
            drive_service = get_drive_service()
            perms_result = drive_service.permissions().list(
                fileId=project.folder_id, 
                fields='permissions(id,emailAddress,role)' # Solo los campos necesarios
            ).execute()
            # El email de Drive puede tener mayúsculas/minúsculas distintas al de la BD, normalizar a minúsculas para la clave del mapa.
            current_drive_permissions_map = {
                p['emailAddress'].lower(): p for p in perms_result.get('permissions', [])
                if p.get('emailAddress') # Asegurarse que hay emailAddress
            }
            logger.info(f"Drive: Permisos actuales para carpeta '{project.name}' (FolderID: {project.folder_id}): {list(current_drive_permissions_map.keys())}")
        except HttpError as e:
            logger.error(f"Drive: FATAL - No se pudieron obtener permisos para carpeta '{project.name}' (FolderID: {project.folder_id}). Código: {e.resp.status}, Razón: {e._get_reason()}. La sincronización de Drive se omitirá.")
            drive_service = None # Deshabilitar operaciones de Drive si no se pueden leer los permisos
            drive_sync_failed_globally = True
            messages.error(request, f"CRÍTICO: No se pudo conectar con Google Drive para obtener permisos de la carpeta del proyecto '{project.name}'. Los cambios de permisos en Drive no se aplicarán.")
        except Exception as e:
            logger.error(f"Drive: FATAL - Excepción inesperada obteniendo permisos para carpeta '{project.name}' (FolderID: {project.folder_id}): {e}. La sincronización de Drive se omitirá.")
            drive_service = None
            drive_sync_failed_globally = True
            messages.error(request, f"CRÍTICO: Error inesperado con Google Drive para el proyecto '{project.name}'. Los cambios de permisos en Drive no se aplicarán.")
    else:
        logger.warning(f"Proyecto '{project.name}' (ID: {project_id}) no tiene folder_id. No se sincronizarán permisos de Drive.")
        # No es un error fatal si el proyecto no tiene carpeta, pero se debe notificar.
        messages.info(request, f"El proyecto '{project.name}' no tiene una carpeta de Google Drive asociada. No se aplicaron cambios de permisos en Drive.")


    # IDs de MiniAdmins que actualmente tienen una asignación a este proyecto en la BD
    current_bd_miniadmin_assignments = ProjectAssignment.objects.filter(
        project=project, 
        user__rol=Rol.MINIADMIN
    ).select_related('user')

    map_current_bd_assignments = {pa.user.cedula: pa for pa in current_bd_miniadmin_assignments}

    # IDs de MiniAdmins y sus roles deseados desde el payload
    # (solo considerar los que tienen un rol explícito, los vacíos significan desasignar)
    desired_assignments_map = {
        item['user_id']: item['role'] 
        for item in assignments_data 
        if item.get('user_id') # Debe tener user_id
    }
    
    miniadmins_processed_in_payload = set()

    # 1. Procesar las asignaciones recibidas en el payload (crear/actualizar/quitar si rol es vacío)
    for mini_admin_id, role_str in desired_assignments_map.items():
        miniadmins_processed_in_payload.add(mini_admin_id)
        try:
            mini_admin_user = User.objects.get(cedula=mini_admin_id, rol=Rol.MINIADMIN)
        except User.DoesNotExist:
            logger.warning(f"MiniAdmin con cédula '{mini_admin_id}' no encontrado en la BD. Omitiendo.")
            continue

        if role_str and role_str not in AssignmentRole.values: # Si hay rol, debe ser válido
            logger.warning(f"Rol '{role_str}' inválido para MiniAdmin '{mini_admin_user.email}'. Omitiendo.")
            continue
        
        # Si el rol es vacío o nulo, significa desasignar
        if not role_str: 
            logger.info(f"BD: Solicitud para quitar asignación de proyecto para MiniAdmin '{mini_admin_user.email}' del proyecto '{project.name}'.")
            deleted_count, _ = ProjectAssignment.objects.filter(project=project, user=mini_admin_user).delete()
            if deleted_count:
                 logger.info(f"BD: Asignación eliminada para MiniAdmin '{mini_admin_user.email}'.")
            if drive_service and project.folder_id:
                _update_drive_permission(drive_service, project.folder_id, mini_admin_user.email, None, current_drive_permissions_map)
        else: # Crear o actualizar asignación
            ProjectAssignment.objects.update_or_create(
                project=project,
                user=mini_admin_user,
                defaults={'role': role_str}
            )
            logger.info(f"BD: Rol '{role_str}' asignado/actualizado para MiniAdmin '{mini_admin_user.email}' en proyecto '{project.name}'.")
            if drive_service and project.folder_id:
                _update_drive_permission(drive_service, project.folder_id, mini_admin_user.email, role_str, current_drive_permissions_map)

    # 2. MiniAdmins que estaban en la BD pero no vinieron en el payload (significa que fueron deseleccionados completamente)
    #    y por lo tanto deben ser desasignados.
    miniadmin_ids_in_bd = set(map_current_bd_assignments.keys())
    miniadmin_ids_to_remove_fully = miniadmin_ids_in_bd - miniadmins_processed_in_payload

    for mini_admin_id_remove in miniadmin_ids_to_remove_fully:
        assignment_to_delete = map_current_bd_assignments.get(mini_admin_id_remove)
        if assignment_to_delete: # Debería existir
            user_email_to_remove = assignment_to_delete.user.email
            logger.info(f"BD: MiniAdmin '{user_email_to_remove}' no presente en payload, eliminando asignación del proyecto '{project.name}'.")
            assignment_to_delete.delete()
            if drive_service and project.folder_id:
                _update_drive_permission(drive_service, project.folder_id, user_email_to_remove, None, current_drive_permissions_map)
    
    # Devolver el estado actual de asignaciones de MiniAdmins para este proyecto
    final_assignments = ProjectAssignment.objects.filter(project=project, user__rol=Rol.MINIADMIN).select_related('user')
    result_data = [{'user_id': pa.user.cedula, 'role': pa.role} for pa in final_assignments]
    
    if drive_sync_failed_globally:
        messages.warning(request, f"Las asignaciones del proyecto '{project.name}' se guardaron en la base de datos, pero hubo un problema crítico sincronizando con Google Drive.")
    elif not project.folder_id:
         messages.info(request, f"Las asignaciones del proyecto '{project.name}' se guardaron. Este proyecto no tiene carpeta en Drive, por lo que no se sincronizaron permisos allí.")
    else:
        messages.success(request, f"Asignaciones del proyecto '{project.name}' actualizadas y sincronizadas con Google Drive.")
        
    return JsonResponse({'status': 'ok', 'assignments': result_data})

@login_required
@user_passes_test(is_super_admin_akadi_or_mini_admin)
@transaction.atomic
def assign_factor_to_user(request):
    if request.method != 'POST':
        return HttpResponseForbidden()

    try:
        payload = json.loads(request.body)
        factor_id = payload.get('factor_id')
        assignments_data = payload.get('assignments', []) # Lista de {'user_id': cedula_usuario, 'role': 'lector'|...}
    except json.JSONDecodeError:
        return HttpResponseBadRequest("JSON inválido.")
    if not factor_id:
        return HttpResponseBadRequest("Falta factor_id.")

    factor = get_object_or_404(Factor, id_factor=factor_id)
    requesting_user = request.user

    # Verificación de permisos del MiniAdmin sobre el proyecto del factor
    if not requesting_user.has_elevated_permissions and requesting_user.is_mini_admin_role:
        try:
            project_assignment = ProjectAssignment.objects.get(project=factor.project, user=requesting_user)
            if project_assignment.role != AssignmentRole.EDITOR:
                return JsonResponse({'error': 'No tienes permiso de Editor en el proyecto para asignar factores.'}, status=403)
        except ProjectAssignment.DoesNotExist:
            return JsonResponse({'error': 'No tienes asignación a este proyecto para gestionar sus factores.'}, status=403)

    # --- Sincronización con Google Drive ---
    drive = None
    current_drive_permissions = {}
    if factor.document_id:
        try:
            drive = get_drive_service()
            perms_result = drive.permissions().list(fileId=factor.document_id, fields='permissions(id,emailAddress,role)').execute()
            current_drive_permissions = {p['emailAddress'].lower(): p for p in perms_result.get('permissions', [])}
        except Exception as e:
            logger.error(f"Error obteniendo permisos de Drive para documento {factor.document_id}: {e}")
            drive = None
            messages.warning(request, "Hubo un error conectando con Google Drive. Los permisos de Drive no se sincronizaron.")
            
    # --- Actualizar BD ---
    current_assigned_users_in_payload = {assign['user_id'] for assign in assignments_data if assign.get('role')}
    
    # 1. Eliminar asignaciones de usuarios que ya no están o cuyo rol es vacío
    assignments_to_delete = FactorAssignment.objects.filter(factor=factor).exclude(user_id__in=current_assigned_users_in_payload)
    if not drive: # Si no hay conexión a Drive, no intentar borrar permisos de Drive
        assignments_to_delete.delete()
    else:
        for assign_del in assignments_to_delete:
            user_email = assign_del.user.email.lower()
            existing_perm = current_drive_permissions.get(user_email)
            if existing_perm:
                try:
                    drive.permissions().delete(fileId=factor.document_id, permissionId=existing_perm['id']).execute()
                except HttpError as e:
                    logger.warning(f"Drive: No se pudo eliminar permiso para {user_email} en {factor.document_id}: {e}")
            assign_del.delete()

    # 2. Crear o actualizar asignaciones
    for assignment_item in assignments_data:
        user_id = assignment_item.get('user_id')
        role_str = assignment_item.get('role')

        if not user_id:
            continue
        
        # Asegurarse de no asignar a roles administrativos
        excluded_roles = [Rol.SUPERADMIN, Rol.MINIADMIN, Rol.ACADI]
        assigned_user = get_object_or_404(User, cedula=user_id)
        if assigned_user.rol in excluded_roles:
            logger.warning(f"Intento de asignar factor a usuario con rol administrativo: {assigned_user.cedula} ({assigned_user.rol})")
            continue


        if not role_str: # Si el rol es vacío, es como quitar el permiso
            assignment_instance = FactorAssignment.objects.filter(factor=factor, user=assigned_user).first()
            if assignment_instance:
                if drive and factor.document_id:
                    _update_drive_permission(drive, factor.document_id, assigned_user.email, None, current_drive_permissions)
                assignment_instance.delete()
            continue

        if role_str not in AssignmentRole.values:
            logger.warning(f"Rol inválido '{role_str}' para usuario {user_id} en factor {factor_id}")
            continue

        assignment, created = FactorAssignment.objects.update_or_create(
            factor=factor,
            user=assigned_user,
            defaults={'role': role_str}
        )
        
        if drive and factor.document_id:
            _update_drive_permission(drive, factor.document_id, assigned_user.email, role_str, current_drive_permissions)

    final_assignments = FactorAssignment.objects.filter(factor=factor).exclude(user__rol__in=excluded_roles).select_related('user')
    result_data = [{'user_id': pa.user.cedula, 'role': pa.role} for pa in final_assignments]
    return JsonResponse({'status': 'ok', 'assignments': result_data})
