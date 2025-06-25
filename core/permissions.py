# =============================================
# core/permissions.py
# =============================================
"""
Permisos jerárquicos Proyecto → Factor → Trait → Aspect.

Roles disponibles ( assignments.models.AssignmentRole ):
- lector        → sólo lectura
- comentador    → puede comentar ‒ no modifica contenido
- editor        → control total sobre el objeto

Los usuarios superuser o con la bandera has_elevated_permissions heredan
rol «editor» en toda la jerarquía.

Mini‑Admin (rol en login.models.Rol) se implementa como un usuario normal
asignado al Proyecto con AssignmentRole.EDITOR. Por simplicidad el
cálculo de permisos no distingue si un usuario es Mini‑Admin o no: el rol
proviene estrictamente de la asignación.
"""
from __future__ import annotations

from pyexpat.errors import messages
from typing import Iterable, Optional, Union, TYPE_CHECKING

from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied
from django.db.models import Q # Import Q

from assignments.models import AssignmentRole, ProjectAssignment, FactorAssignment
from projects.models import Project
from factorManager.models import Factor
from traitManager.models import Trait
from aspectManager.models import Aspect

if TYPE_CHECKING:  # Sólo para type‑checkers
    from django.contrib.auth.models import AbstractBaseUser

User = get_user_model()

# ---------------------------------------------------------------------------
# Utilidades internas
# ---------------------------------------------------------------------------

_ROLE_ORDER = {
    AssignmentRole.LECTOR: 0,
    AssignmentRole.COMENTADOR: 1,
    AssignmentRole.EDITOR: 2,
}

def _highest_role(*roles: Optional[str]) -> Optional[str]:
    """Devuelve el rol más alto dentro de *roles* (None se ignora)."""
    highest: Optional[str] = None
    for r in roles:
        if r is None:
            continue
        if highest is None or _ROLE_ORDER[r] > _ROLE_ORDER[highest]:
            highest = r
    return highest

# ---------------------------------------------------------------------------
# Helpers de obtención de rol por tipo de objeto
# ---------------------------------------------------------------------------

def get_project_permission(user: 'AbstractBaseUser', project: Project) -> Optional[str]:
    if not user.is_authenticated: # Añadido para manejar usuarios anónimos
        return None
    if user.is_superuser or getattr(user, 'has_elevated_permissions', False):
        return AssignmentRole.EDITOR
    try:
        return ProjectAssignment.objects.only('role').get(user=user, project=project).role
    except ProjectAssignment.DoesNotExist:
        return None

def get_factor_permission(user: 'AbstractBaseUser', factor: Factor) -> Optional[str]:
    if not user.is_authenticated: # Añadido
        return None
    if user.is_superuser or getattr(user, 'has_elevated_permissions', False):
        return AssignmentRole.EDITOR
    
    direct_assignment = FactorAssignment.objects.filter(user=user, factor=factor).values_list('role', flat=True).first()
    project_permission = get_project_permission(user, factor.project)
    
    # Si el usuario es EDITOR del proyecto, hereda EDITOR para el factor.
    # De lo contrario, el permiso directo sobre el factor tiene precedencia si es mayor,
    # o se usa el permiso del proyecto si no hay asignación directa al factor.
    if project_permission == AssignmentRole.EDITOR:
        return AssignmentRole.EDITOR
        
    return _highest_role(direct_assignment, project_permission)


def get_trait_permission(user: 'AbstractBaseUser', trait: Trait) -> Optional[str]:
    return get_factor_permission(user, trait.factor)

def get_aspect_permission(user: 'AbstractBaseUser', aspect: Aspect) -> Optional[str]:
    return get_trait_permission(user, aspect.trait)

# ---------------------------------------------------------------------------
# Comodidades para templates y pruebas
# ---------------------------------------------------------------------------

def can_view(role: Optional[str]) -> bool:
    return role is not None  # cualquier rol permite ver

def can_comment(role: Optional[str]) -> bool:
    return role in {AssignmentRole.COMENTADOR, AssignmentRole.EDITOR}

def can_edit(role: Optional[str]) -> bool:
    return role == AssignmentRole.EDITOR

# ---------------------------------------------------------------------------
# Mixins
# ---------------------------------------------------------------------------

class ObjectPermissionRequiredMixin:
    """Valida permisos a nivel de objeto en Detail/Update/Delete views."""
    permission_required_roles: Optional[Iterable[str]] = None
    _object_for_permission = None # Cache para el objeto

    def get_object_for_permission(self):
        if self._object_for_permission is None:
            self._object_for_permission = super().get_object()
        return self._object_for_permission

    def _get_user_role_for_object(self, user: 'AbstractBaseUser', obj: Union[Project, Factor, Trait, Aspect]) -> Optional[str]:
        if isinstance(obj, Project):
            return get_project_permission(user, obj)
        if isinstance(obj, Factor):
            return get_factor_permission(user, obj)
        if isinstance(obj, Trait):
            return get_trait_permission(user, obj)
        if isinstance(obj, Aspect):
            return get_aspect_permission(user, obj)
        # Considerar añadir un log o error más específico si el tipo no es soportado
        raise TypeError(f"Tipo de objeto no soportado para permisos: {type(obj)}")


    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission() # Redirige a login

        obj = self.get_object_for_permission() # Usa el método para obtener el objeto
        
        role = self._get_user_role_for_object(request.user, obj)
        request.current_permission_role = role # Guardar el rol en el request para acceso en la vista/template

        if role is None:
            messages.error(request, "No tienes acceso a este recurso.")
            raise PermissionDenied("No tienes acceso a este recurso.")

        if self.permission_required_roles and role not in self.permission_required_roles:
            allowed_roles_display = ", ".join(
                dict(AssignmentRole.choices).get(r, r) for r in self.permission_required_roles
            )
            current_role_display = dict(AssignmentRole.choices).get(role, role)
            messages.error(request, f"Se requiere rol '{allowed_roles_display}'; tu rol actual es '{current_role_display}'.")
            raise PermissionDenied(f"Se requiere rol '{allowed_roles_display}'; tu rol actual es '{current_role_display}'.")
        
        return super().dispatch(request, *args, **kwargs)


class FilteredListPermissionMixin:
    """Filtra automáticamente un ListView según los permisos del usuario."""

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user

        if not user.is_authenticated: # Si el usuario no está autenticado, no debería ver nada
            return qs.none()

        if user.is_superuser or getattr(user, 'has_elevated_permissions', False):
            return qs # Superusuarios y Akadi ven todo

        model = self.model

        if model is Project:
            assigned_project_ids = ProjectAssignment.objects.filter(user=user).values_list('project_id', flat=True)
            return qs.filter(id_project__in=assigned_project_ids)

        if model is Factor:
            # Factores de proyectos donde el usuario es EDITOR (MiniAdmin del proyecto)
            editor_project_ids = ProjectAssignment.objects.filter(
                user=user, role=AssignmentRole.EDITOR
            ).values_list('project_id', flat=True)
            q_factors_from_editor_projects = Q(project_id__in=editor_project_ids)

            # Factores a los que el usuario está asignado directamente (con cualquier rol)
            directly_assigned_factor_ids = FactorAssignment.objects.filter(
                user=user
            ).values_list('factor_id', flat=True)
            q_directly_assigned_factors = Q(id_factor__in=directly_assigned_factor_ids)
            
            # Combinar las condiciones: el usuario ve factores de proyectos que edita O factores a los que está asignado directamente.
            return qs.filter(q_factors_from_editor_projects | q_directly_assigned_factors).distinct()

        if model is Trait:
            # Traits de factores donde el usuario es EDITOR (heredado del proyecto o directo al factor)
            # O traits de factores a los que tiene asignación directa (lector/comentador)
            
            # 1. Factores donde el usuario es EDITOR (directo o heredado del proyecto)
            editor_factor_ids = set()
            editor_project_ids = ProjectAssignment.objects.filter(user=user, role=AssignmentRole.EDITOR).values_list('project_id', flat=True)
            for factor in Factor.objects.filter(project_id__in=editor_project_ids):
                editor_factor_ids.add(factor.id_factor)
            
            direct_editor_factor_ids = FactorAssignment.objects.filter(user=user, role=AssignmentRole.EDITOR).values_list('factor_id', flat=True)
            for fid in direct_editor_factor_ids:
                editor_factor_ids.add(fid)

            q_traits_from_editor_factors = Q(factor_id__in=list(editor_factor_ids))

            # 2. Traits de factores donde el usuario tiene asignación directa (Lector o Comentador)
            #    (ya que los de EDITOR ya están cubiertos arriba)
            assigned_factor_ids_non_editor = FactorAssignment.objects.filter(
                user=user, role__in=[AssignmentRole.LECTOR, AssignmentRole.COMENTADOR]
            ).values_list('factor_id', flat=True)
            q_traits_from_assigned_factors_non_editor = Q(factor_id__in=assigned_factor_ids_non_editor)
            
            return qs.filter(q_traits_from_editor_factors | q_traits_from_assigned_factors_non_editor).distinct()


        if model is Aspect:
            # Similar a Trait: Aspectos de traits cuyos factores el usuario puede editar,
            # o aspectos de traits cuyos factores el usuario puede ver/comentar.
            
            # 1. Factores donde el usuario es EDITOR
            editor_factor_ids = set()
            editor_project_ids = ProjectAssignment.objects.filter(user=user, role=AssignmentRole.EDITOR).values_list('project_id', flat=True)
            for factor in Factor.objects.filter(project_id__in=editor_project_ids):
                editor_factor_ids.add(factor.id_factor)
            
            direct_editor_factor_ids = FactorAssignment.objects.filter(user=user, role=AssignmentRole.EDITOR).values_list('factor_id', flat=True)
            for fid in direct_editor_factor_ids:
                editor_factor_ids.add(fid)
            
            q_aspects_from_editor_factors = Q(trait__factor_id__in=list(editor_factor_ids))

            # 2. Factores donde el usuario es LECTOR o COMENTADOR
            assigned_factor_ids_non_editor = FactorAssignment.objects.filter(
                user=user, role__in=[AssignmentRole.LECTOR, AssignmentRole.COMENTADOR]
            ).values_list('factor_id', flat=True)
            q_aspects_from_assigned_factors_non_editor = Q(trait__factor_id__in=assigned_factor_ids_non_editor)

            return qs.filter(q_aspects_from_editor_factors | q_aspects_from_assigned_factors_non_editor).distinct()

        return qs.none() # Por defecto, si el modelo no está manejado, no mostrar nada.

__all__ = [
    'AssignmentRole',
    'get_project_permission', 'get_factor_permission', 'get_trait_permission', 'get_aspect_permission',
    'can_view', 'can_comment', 'can_edit',
    'ObjectPermissionRequiredMixin', 'FilteredListPermissionMixin',
]
