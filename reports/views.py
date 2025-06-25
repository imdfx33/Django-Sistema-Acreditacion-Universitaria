# reports/views.py
import json
from venv import logger
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import JsonResponse, HttpResponseForbidden, HttpResponseBadRequest
from django.views.decorators.http import require_POST
from django.core.management import call_command
from django.urls import reverse

from projects.models import Project # Asumiendo que Project está en la app 'projects'
from login.models import Rol # Asumiendo que Rol está en la app 'login'

# --- Helpers de Permisos ---
def _user_can_generate_report(user):
    """
    Verifica si el usuario tiene permisos para generar el informe.
    (SuperAdmin, Akadi, o superusuario de Django)
    """
    if not user.is_authenticated:
        return False
    # El modelo User tiene un campo 'rol' y 'Rol' es una clase TextChoices/Enum
    # y una propiedad 'has_elevated_permissions'
    return user.is_superuser or getattr(user, 'rol', None) in (Rol.SUPERADMIN, Rol.ACADI)

def _all_projects_are_finalized():
    """
    Verifica si todos los proyectos en el sistema están marcados como finalizados (progreso 100%).
    """
    # Exclude(progress=100) encuentra proyectos que NO están al 100%.
    # Si no existe ninguno así, todos están finalizados.
    return not Project.objects.exclude(progress=100).exists()

# --- Vista AJAX para disparar la generación del informe ---
@login_required
@require_POST # Solo permitir peticiones POST
def generate_final_report(request):
    """
    Endpoint AJAX para iniciar la generación del informe final.
    """
    if not _user_can_generate_report(request.user):
        return HttpResponseForbidden(json.dumps({'error': 'No tienes permiso para realizar esta acción.'}), content_type='application/json')

    if not _all_projects_are_finalized():
        return HttpResponseBadRequest(json.dumps({'error': 'Aún existen proyectos en progreso. No se puede generar el informe final.'}), content_type='application/json')

    try:
        # Ejecutar el comando de gestión.
        # Es una operación potencialmente larga, idealmente se manejaría de forma asíncrona (ej. con Celery).
        # Por simplicidad y siguiendo el prompt, call_command es síncrono aquí.
        # El frontend recibirá la respuesta después de que el comando termine.
        # Si el comando es muy largo, esto podría causar timeouts en el request HTTP.
        # El mensaje al usuario sugiere que recargue, lo que implica que el proceso podría tardar.
        
        call_command("generar_informe", user_id=request.user.pk, verbosity=1)
        
        # Si el comando fue exitoso, el nuevo informe debería ser el más reciente.
        # (El comando mismo guarda el FinalReport)
        
        return JsonResponse({
            "status": "ok",
            "message": "El informe final se ha generado exitosamente. La página se recargará para mostrar el enlace.",
            # Podríamos intentar obtener el enlace aquí, pero es más simple recargar.
        })
    except Exception as e:
        logger.error(f"Error al invocar el comando generar_informe: {e}", exc_info=True)
        return JsonResponse({
            "status": "error",
            "message": f"Ocurrió un error al generar el informe: {str(e)}"
        }, status=500)

