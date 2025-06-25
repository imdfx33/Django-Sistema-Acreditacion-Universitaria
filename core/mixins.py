# =============================================
# core/mixins.py
# =============================================
"""Mixins de acceso rápido para views basados en los helpers de permisos."""
from __future__ import annotations
from typing import Iterable, Optional

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect

from assignments.models import AssignmentRole
from core.permissions import (
    get_project_permission,
    get_factor_permission,
    ObjectPermissionRequiredMixin,
    FilteredListPermissionMixin,
)

# ---------------------------------------------------------------------------
# Mixins de alto nivel (elevated / admin)
# ---------------------------------------------------------------------------

class ElevatedAccessRequiredMixin(UserPassesTestMixin):
    """Permite únicamente superusers o usuarios con *has_elevated_permissions*."""

    def test_func(self):
        u = self.request.user
        return u.is_authenticated and (u.is_superuser or getattr(u, 'has_elevated_permissions', False))

    def handle_no_permission(self):
        messages.error(self.request, "No tienes permiso para acceder a esta sección.")
        return redirect('login' if not self.request.user.is_authenticated else 'home')

class AdminOrMiniAdminRequiredMixin(UserPassesTestMixin):
    """Superuser, elevated (Akadi) o Mini‑Admin."""

    def test_func(self):
        u = self.request.user
        return u.is_authenticated and (
            u.is_superuser or
            getattr(u, 'has_elevated_permissions', False) or
            getattr(u, 'is_mini_admin_role', False)
        )

    def handle_no_permission(self):
        messages.error(self.request, "No tienes permiso para realizar esta acción.")
        return redirect('login' if not self.request.user.is_authenticated else 'home')

# ---------------------------------------------------------------------------
# Mixins que verifican rol concreto sobre objetos
# ---------------------------------------------------------------------------

class ProjectRoleRequiredMixin(LoginRequiredMixin):
    """Verifica rol mínimo sobre un *Proyecto* antes de *dispatch*."""
    permission_roles: Optional[Iterable[str]] = None

    def dispatch(self, request, *args, **kwargs):
        project = self.get_object()
        role = get_project_permission(request.user, project)
        if role is None or (self.permission_roles and role not in self.permission_roles):
            raise PermissionDenied("No tienes permiso para este proyecto.")
        request.current_permission_role = role  # type: ignore[attr-defined]
        return super().dispatch(request, *args, **kwargs)

class FactorRoleRequiredMixin(LoginRequiredMixin):
    """Verifica rol mínimo sobre un *Factor* antes de *dispatch*."""
    permission_roles: Optional[Iterable[str]] = None

    def dispatch(self, request, *args, **kwargs):
        factor = self.get_object()
        role = get_factor_permission(request.user, factor)
        if role is None or (self.permission_roles and role not in self.permission_roles):
            raise PermissionDenied("No tienes permiso para este factor.")
        request.current_permission_role = role  # type: ignore[attr-defined]
        return super().dispatch(request, *args, **kwargs)

# ---------------------------------------------------------------------------
# Facilitar importación desde *core.mixins*
# ---------------------------------------------------------------------------

ObjectPermissionRequiredMixin = ObjectPermissionRequiredMixin  # re‑export
FilteredListPermissionMixin  = FilteredListPermissionMixin

__all__ = [
    'ElevatedAccessRequiredMixin', 'AdminOrMiniAdminRequiredMixin',
    'ProjectRoleRequiredMixin', 'FactorRoleRequiredMixin',
    'ObjectPermissionRequiredMixin', 'FilteredListPermissionMixin',
]
