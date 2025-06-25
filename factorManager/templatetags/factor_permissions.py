# factorManager/templatetags/factor_permissions.py
from django import template
from assignments.models import AssignmentRole # Asegúrate que AssignmentRole está aquí
from core.permissions import get_factor_permission, can_edit # Tus funciones de core.permissions

register = template.Library()

@register.simple_tag
def user_can_edit_factor(user, factor):
    """
    Template tag para verificar si un usuario puede editar un factor específico.
    Esto incluye superusuarios, usuarios con permisos elevados,
    o usuarios con el rol de EDITOR en el factor (directo o heredado).
    """
    if not user or not user.is_authenticated:
        return False
    
    # Superusuarios y usuarios con 'has_elevated_permissions' (ej. Akadi) siempre pueden editar.
    # Esta lógica ya está dentro de get_factor_permission.
    # get_factor_permission devolverá AssignmentRole.EDITOR para estos usuarios.
    
    role = get_factor_permission(user, factor)
    return can_edit(role)

@register.simple_tag
def user_can_view_factor(user, factor): # Opcional: si necesitas verificar vista explícitamente
    """
    Template tag para verificar si un usuario puede ver un factor específico.
    """
    if not user or not user.is_authenticated:
        return False
    
    role = get_factor_permission(user, factor)
    return role is not None # Cualquier rol asignado (Lector, Comentador, Editor) permite ver
