# traitManager/views.py
from django import forms # Necesario para forms.HiddenInput
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.views.generic import CreateView, UpdateView, DeleteView
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.http import HttpResponseForbidden # Para respuestas de permiso denegado

from .models import Trait
from .forms import TraitForm, TraitUpdateForm # Usar TraitUpdateForm para la edición
from factorManager.models import Factor
from login.models import Rol # Para comprobaciones de roles específicos
from assignments.models import AssignmentRole # Para roles de asignación
from core.permissions import (
    get_factor_permission, 
    can_edit as permission_can_edit # Alias para la función can_edit
)
from core.mixins import ObjectPermissionRequiredMixin # Usaremos este para Update y Delete

class TraitCreateView(LoginRequiredMixin, CreateView):
    """
    Permite la creación de nuevas Características (Traits).
    - Se asocia a un Factor.
    - Permisos: El usuario debe ser EDITOR del Factor padre (directo o heredado del proyecto)
      o SuperAdmin/Akadi.
    - Si se accede con ?factor=<factor_pk>, se preselecciona el factor.
    """
    model = Trait
    form_class = TraitForm
    template_name = 'traitManager/trait_form.html'

    def get_factor_from_request(self):
        factor_id = self.request.GET.get('factor') or self.kwargs.get('factor_pk') # Aceptar factor_pk desde URL kwargs también
        if factor_id:
            return get_object_or_404(Factor, id_factor=factor_id)
        return None

    def dispatch(self, request, *args, **kwargs):
        user = request.user
        factor_for_creation = self.get_factor_from_request()

        if not Factor.objects.exists():
            messages.error(request, "No existen factores. Debes crear al menos un factor antes de añadir características.")
            return redirect('factor_list') # O a la lista de proyectos si tiene más sentido

        # Si se especifica un factor para la creación
        if factor_for_creation:
            user_factor_role = get_factor_permission(user, factor_for_creation)
            if not permission_can_edit(user_factor_role):
                messages.error(request, "No tienes permiso de Editor en este factor para crear características.")
                return HttpResponseForbidden("Permiso denegado para crear característica en este factor.")
        else:
            # Si no se especifica factor, solo SuperAdmin/Akadi pueden crear (el form les permitirá elegir)
            if not (user.is_superuser or getattr(user, 'has_elevated_permissions', False)):
                messages.error(request, "Debes seleccionar un factor para crear una característica o no tienes permisos suficientes.")
                return redirect('factor_list') # O a una página relevante

        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user # Pasar usuario al form para filtrar factores
        factor_from_url = self.get_factor_from_request()
        if factor_from_url:
            kwargs['factor_id'] = factor_from_url.id_factor
        return kwargs
        
    def form_valid(self, form):
        trait = form.save(commit=False)
        # El factor ya debería estar asignado por el form si vino por URL o fue seleccionado.
        # Si el campo 'factor' estaba oculto y se pasó por URL, form.instance.factor ya debería estar seteado
        # por el 'initial' y el widget oculto.
        # Si el usuario seleccionó un factor en el formulario, también está bien.
        
        # No es necesario inyectar _creator_email para Trait a menos que Trait tenga lógica de Drive propia.
        # Por ahora, el documento de Drive está a nivel de Factor.
        
        trait.save() # Guardar la característica
        
        messages.success(self.request, f"Característica «{trait.name}» creada exitosamente y asociada al factor «{trait.factor.name}».")
        return redirect(self.get_success_url(trait))

    def get_success_url(self, trait=None):
        obj = trait if trait else self.object
        # Redirigir al detalle del factor padre
        if obj and obj.factor:
            return reverse_lazy('factor_detail', kwargs={'pk': obj.factor.pk})
        return reverse_lazy('trait_list') # Fallback si no hay factor

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        factor_from_url = self.get_factor_from_request()
        if factor_from_url:
            context['factor_ctx'] = factor_from_url # Para mostrar info del factor en el template
            context['form_title'] = f"Nueva Característica para Factor: {factor_from_url.name}"
        else:
            context['form_title'] = "Crear Nueva Característica"
        return context

class TraitUpdateView(LoginRequiredMixin, ObjectPermissionRequiredMixin, UpdateView):
    """
    Permite la edición de una Característica.
    Solo accesible para usuarios con rol EDITOR en el Factor padre de la Característica.
    """
    model = Trait
    form_class = TraitUpdateForm # Usar el form específico para actualización
    template_name = 'traitManager/trait_form.html' 
    # ObjectPermissionRequiredMixin usa _get_user_role_for_object que ya tiene la lógica para Trait (hereda de Factor)
    permission_required_roles = [AssignmentRole.EDITOR] 

    def get_object(self, queryset=None):
        # ObjectPermissionRequiredMixin llamará a esto.
        # Aseguramos que el objeto para el permiso sea el Factor padre.
        trait = super().get_object(queryset)
        self._object_for_permission = trait.factor # El permiso se basa en el Factor padre
        return trait

    def get_success_url(self):
        # Redirigir al detalle de la característica actualizada.
        return reverse_lazy('trait_detail', kwargs={'pk': self.object.pk})

    def form_valid(self, form):
        messages.success(self.request, f"Característica «{self.object.name}» actualizada correctamente.")
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form_title'] = f"Editar Característica: {self.object.name}"
        context['factor_ctx'] = self.object.factor # Para breadcrumbs o info en el template
        return context

class TraitDeleteView(LoginRequiredMixin, ObjectPermissionRequiredMixin, DeleteView):
    """
    Permite la eliminación de una Característica.
    Solo accesible para usuarios con rol EDITOR en el Factor padre.
    """
    model = Trait
    template_name = 'traitManager/trait_confirm_delete.html'
    permission_required_roles = [AssignmentRole.EDITOR]

    def get_object(self, queryset=None):
        trait = super().get_object(queryset)
        self._object_for_permission = trait.factor # El permiso se basa en el Factor padre
        return trait

    def get_success_url(self):
        # Redirigir al detalle del factor padre después de eliminar la característica.
        if self.object and self.object.factor:
            return reverse_lazy('factor_detail', kwargs={'pk': self.object.factor.pk})
        return reverse_lazy('trait_list') # Fallback

    def form_valid(self, form):
        trait_name = self.object.name
        factor_pk = self.object.factor.pk # Guardar antes de eliminar
        response = super().form_valid(form)
        messages.success(self.request, f"Característica «{trait_name}» eliminada correctamente.")
        return redirect(reverse_lazy('factor_detail', kwargs={'pk': factor_pk}))
        
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['delete_target_name'] = self.object.name
        context['parent_factor_name'] = self.object.factor.name
        return context

# Las vistas factor_add_trait y trait_create_for_factor que estaban en el archivo
# original de traitManager/views.py parecen redundantes o podrían simplificarse con TraitCreateView
# si se maneja bien el parámetro ?factor=<factor_pk>.
# Por ahora, las comentaré o eliminaré para evitar confusión, ya que TraitCreateView
# ya intenta manejar la creación de una característica para un factor específico.

# Si se necesita una vista separada para "añadir una característica EXISTENTE a un factor",
# esa lógica sería diferente (manejar una relación ManyToMany si una Característica pudiera
# pertenecer a múltiples Factores, lo cual no es el caso según el modelo actual donde Trait.factor es ForeignKey).
# Dado que Trait tiene un ForeignKey a Factor, cada Trait pertenece a UN SOLO Factor.
# Por lo tanto, "añadir una característica existente" no tiene sentido en este modelo.
# Lo que sí tiene sentido es "crear una nueva característica PARA un factor".
