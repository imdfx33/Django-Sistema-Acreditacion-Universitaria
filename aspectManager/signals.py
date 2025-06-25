# aspectManager/signals.py
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .models import Aspect
from factorManager.models import Factor

@receiver([post_save, post_delete], sender=Aspect)
def _update_cascade(sender, instance, **kwargs):
    # ahora cada Aspecto → 1 Trait → 1 Factor
    factor = instance.trait.factor
    factor.save()  # re-calcula is_completed & proyecto

@receiver([post_save, post_delete], sender=Factor)
def _update_project_progress(sender, instance, **kwargs):
    # cada vez que cambie un Factor → forzamos recálculo en Proyecto
    instance.project.update_progress(save=True)