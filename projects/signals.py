# projects/signals.py
from django.db.models.signals import pre_delete
from django.dispatch import receiver
from .models import Project, _drive_service
# No se necesita importar Factor aquí directamente si solo accedes a través de instance.factors.all()
# Si necesitaras el tipo Factor explícitamente, sería:
# from factorManager.models import Factor

@receiver(pre_delete, sender=Project)
def trash_project_drive(sender, instance, **kwargs):
    """
    Cuando un Proyecto se elimina, mueve su carpeta de Drive a la papelera,
    y también los documentos de Drive de sus Factores asociados.
    """
    drive = _drive_service()
    
    # 1) Mover a papelera todos los Docs de los factores vinculados al proyecto
    # instance.factors.all() funciona debido al related_name en Factor.project
    if hasattr(instance, 'factors'): # Verificar si la relación 'factors' existe
        for factor in instance.factors.all():
            if factor.document_id:
                try:
                    print(f"Signals: Intentando mover a papelera documento {factor.document_id} del factor {factor.name}")
                    drive.files().update(
                        fileId=factor.document_id,
                        body={'trashed': True}
                    ).execute()
                    print(f"Signals: Documento {factor.document_id} movido a papelera.")
                except Exception as e:
                    # Es importante loggear este error pero no impedir la eliminación del proyecto
                    print(f"Error al mover a papelera el documento {factor.document_id} del factor {factor.name}: {e}")
                    pass # Continuar con la eliminación

    # 2) Mover a papelera la carpeta principal del proyecto
    if instance.folder_id:
        try:
            print(f"Signals: Intentando mover a papelera carpeta {instance.folder_id} del proyecto {instance.name}")
            drive.files().update(
                fileId=instance.folder_id,
                body={'trashed': True}
            ).execute()
            print(f"Signals: Carpeta {instance.folder_id} movida a papelera.")
        except Exception as e:
            print(f"Error al mover a papelera la carpeta {instance.folder_id} del proyecto {instance.name}: {e}")
            pass # Continuar con la eliminación
