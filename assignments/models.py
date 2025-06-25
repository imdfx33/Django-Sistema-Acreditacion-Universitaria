# assignments/models.py
from django.db import models
from django.conf import settings
# Asegúrate que los modelos Project y Factor están correctamente referenciados
# Si están en apps diferentes, usa 'app_name.ModelName'
from projects.models import Project
from factorManager.models import Factor 
# from login.models import User # Ya no es necesario si usas settings.AUTH_USER_MODEL

class AssignmentRole(models.TextChoices):
    LECTOR      = 'lector',     'Lector'
    COMENTADOR  = 'comentador', 'Comentador'
    EDITOR      = 'editor',     'Editor'
    # VISITANTE podría ser LECTOR. Si son distintos, mantenlo.
    # VISITANTE   = 'visitante',  'Visitante' # Considera si es igual a LECTOR

class ProjectAssignment(models.Model):
    project     = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='project_assignments_to_users') # Cambiado related_name
    user        = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='project_assignments_as_user') # Cambiado related_name
    role        = models.CharField(max_length=12, choices=AssignmentRole.choices)
    assigned_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('project', 'user') # Un usuario solo puede tener un rol por proyecto
        verbose_name = "Asignación de Proyecto"
        verbose_name_plural = "Asignaciones de Proyectos"

    def __str__(self):
        return f"{self.user.get_full_name} - {self.project.name} ({self.get_role_display()})"

class FactorAssignment(models.Model):
    factor      = models.ForeignKey(Factor, on_delete=models.CASCADE, related_name='factor_assignments_to_users') # Cambiado related_name
    user        = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='factor_assignments_as_user') # Cambiado related_name
    role        = models.CharField(max_length=12, choices=AssignmentRole.choices)
    assigned_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('factor', 'user') # Un usuario solo puede tener un rol por factor
        verbose_name = "Asignación de Factor"
        verbose_name_plural = "Asignaciones de Factores"

    def __str__(self):
        return f"{self.user.get_full_name} - {self.factor.name} ({self.get_role_display()})"
