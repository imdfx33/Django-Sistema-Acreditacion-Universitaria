# factorManager/signals.py
from django.db.models.signals import pre_delete, post_save, post_delete
from django.dispatch import receiver
from .models import Factor # Factor es el sender
from projects.models import _drive_service # Importar si es necesario para otras señales, o quitar si no se usa

@receiver(pre_delete, sender=Factor)
def trash_factor_drive(sender, instance, **kwargs):
    """
    Mueve el documento de Google Drive asociado al factor a la papelera.
    """
    if instance.document_id:
        try:
            # Es mejor obtener el servicio de Drive de una fuente centralizada si es posible,
            # por ejemplo, desde projects.models o core, para asegurar consistencia.
            # Si _drive_service está definido en este mismo archivo (factorManager/models.py),
            # entonces from .models import _drive_service sería correcto.
            # Si está en projects.models, entonces from projects.models import _drive_service.
            # Asumiendo que está en projects.models como en el error anterior.
            drive = _drive_service() 
            drive.files().update(
                fileId=instance.document_id,
                body={'trashed': True}
            ).execute()
            print(f"Signals: Documento {instance.document_id} del factor {instance.name} movido a papelera.")
        except Exception as e:
            print(f"Error al mover a papelera el documento {instance.document_id} del factor {instance.name}: {e}")
            pass

@receiver([post_save, post_delete], sender=Factor)
def _update_project_progress(sender, instance, **kwargs):
    """
    Actualiza el progreso del proyecto asociado después de que un factor se guarda o elimina.
    """
    if instance.project: # Asegurarse que el factor tiene un proyecto asociado
        # CORRECCIÓN: Cambiar 'save=True' por 'save_instance=True'
        # para que coincida con la definición en projects/models.py
        instance.project.update_progress(save_instance=True)
        print(f"Signals: Progreso actualizado para el proyecto {instance.project.name} debido a cambios en el factor {instance.name}")

