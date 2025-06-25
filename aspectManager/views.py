# aspectManager/views.py
from django import forms
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.views.generic import CreateView, UpdateView, DeleteView
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.http import HttpResponseForbidden, JsonResponse # JsonResponse para toggle_approval

from .models import Aspect
from .forms import AspectForm, AspectUpdateForm
from traitManager.models import Trait
from login.models import Rol
from assignments.models import AssignmentRole
from core.permissions import (
    get_aspect_permission, # Permiso sobre el Aspecto (heredado de Trait -> Factor)
    can_edit as permission_can_edit
)
from core.mixins import ObjectPermissionRequiredMixin
import logging

logger = logging.getLogger(__name__)

class AspectCreateView(LoginRequiredMixin, CreateView):
    model = Aspect
    form_class = AspectForm
    template_name = 'aspectManager/aspect_form.html'

    _trait_from_url = None # Cache para el trait de la URL

    def get_trait_from_url(self):
        if self._trait_from_url is None:
            trait_id = self.request.GET.get('trait') or self.kwargs.get('trait_pk')
            if trait_id:
                self._trait_from_url = get_object_or_404(Trait, id_trait=trait_id)
        return self._trait_from_url

    def dispatch(self, request, *args, **kwargs):
        user = request.user
        trait_for_creation = self.get_trait_from_url()

        if not Trait.objects.exists():
            messages.error(request, "No existen características. Debes crear al menos una característica antes de añadir aspectos.")
            return redirect(reverse_lazy('trait_list'))

        can_create_globally = user.is_superuser or getattr(user, 'has_elevated_permissions', False)
        
        if trait_for_creation:
            user_aspect_role = get_aspect_permission(user, Aspect(trait=trait_for_creation)) # Permiso sobre el aspecto (heredado)
            if not permission_can_edit(user_aspect_role):
                messages.error(request, "No tienes permiso de Editor en la característica padre para crear aspectos.")
                return HttpResponseForbidden("Permiso denegado para crear aspecto en esta característica.")
        elif not can_create_globally:
            temp_form = AspectForm(user=user) # Pasar usuario para que el form filtre el queryset de traits
            if not temp_form.fields['trait'].queryset.exists():
                messages.error(request, "No tienes permiso para crear aspectos en ninguna característica, o no hay características disponibles.")
                return redirect(reverse_lazy('trait_list'))
            
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        trait_from_url = self.get_trait_from_url()
        if trait_from_url:
            kwargs['trait_id'] = trait_from_url.id_trait
        return kwargs

    def form_valid(self, form):
        aspect = form.save(commit=False)
        # El trait ya está en form.instance.trait
        aspect.save() # Guardar el aspecto
        
        messages.success(self.request, f"Aspecto «{aspect.name}» creado exitosamente y asociado a la característica «{aspect.trait.name}».")
        return redirect(self.get_success_url(aspect))

    def get_success_url(self, aspect=None):
        obj = aspect if aspect else self.object
        if obj and obj.trait:
            return reverse_lazy('trait_detail', kwargs={'pk': obj.trait.pk})
        return reverse_lazy('aspect_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        trait_from_url = self.get_trait_from_url()
        if trait_from_url:
            context['trait_ctx'] = trait_from_url
            context['form_title'] = f"Nuevo Aspecto para Característica: {trait_from_url.name}"
        else:
            context['form_title'] = "Crear Nuevo Aspecto"
        return context

class AspectUpdateView(LoginRequiredMixin, ObjectPermissionRequiredMixin, UpdateView):
    model = Aspect
    form_class = AspectUpdateForm # Usar el form específico para actualización
    template_name = 'aspectManager/aspect_form.html'
    permission_required_roles = [AssignmentRole.EDITOR]

    def get_object_for_permission(self):
        if not hasattr(self, '_object_for_permission_cached'):
            aspect = super().get_object()
            # El permiso para editar un Aspecto se basa en el permiso sobre su Trait padre (que a su vez hereda del Factor)
            self._object_for_permission_cached = aspect 
        return self._object_for_permission_cached

    def get_success_url(self):
        return reverse_lazy('aspect_detail', kwargs={'pk': self.object.pk})

    def form_valid(self, form):
        messages.success(self.request, f"Aspecto «{self.object.name}» actualizado correctamente.")
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        aspect = self.object
        context['form_title'] = f"Editar Aspecto: {aspect.name}"
        context['trait_ctx'] = aspect.trait
        return context

class AspectDeleteView(LoginRequiredMixin, ObjectPermissionRequiredMixin, DeleteView):
    model = Aspect
    template_name = 'aspectManager/aspect_confirm_delete.html'
    permission_required_roles = [AssignmentRole.EDITOR]

    def get_object_for_permission(self):
        if not hasattr(self, '_object_for_permission_cached'):
            aspect = super().get_object()
            self._object_for_permission_cached = aspect
        return self._object_for_permission_cached

    def get_success_url(self):
        if self.object and self.object.trait:
            return reverse_lazy('trait_detail', kwargs={'pk': self.object.trait.pk})
        return reverse_lazy('aspect_list')

    def form_valid(self, form):
        aspect_name = self.object.name
        trait_pk = self.object.trait.pk
        try:
            response = super().form_valid(form) # Esto llama al delete() del objeto
            messages.success(self.request, f"Aspecto «{aspect_name}» eliminado correctamente.")
            return redirect(reverse_lazy('trait_detail', kwargs={'pk': trait_pk}))
        except Exception as e:
            logger.error(f"Error al eliminar el aspecto '{aspect_name}': {e}")
            messages.error(self.request, f"Hubo un error al eliminar el aspecto: {e}")
            return redirect('aspect_detail', pk=self.object.pk)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        aspect = self.object
        context['delete_target_name'] = aspect.name
        context['parent_trait_name'] = aspect.trait.name
        return context

@login_required
def toggle_approval(request, pk):
    aspect = get_object_or_404(Aspect, pk=pk)
    user_role = get_aspect_permission(request.user, aspect) # Permiso sobre el aspecto (heredado)

    if not permission_can_edit(user_role):
        messages.error(request, "No tienes permiso para cambiar el estado de este aspecto.")
        # Devolver un JsonResponse si la petición es AJAX, o redirigir si no.
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'status': 'error', 'message': 'Permiso denegado.'}, status=403)
        raise PermissionDenied("No tienes permiso para cambiar el estado de este aspecto.")

    aspect.approved = not aspect.approved
    aspect.save() # Esto debería disparar las señales para actualizar Factor y Proyecto
    
    estado_txt = "aprobado" if aspect.approved else "marcado como pendiente"
    messages.success(request, f"Aspecto «{aspect.name}» {estado_txt}.")
    
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({
            'status': 'ok', 
            'approved': aspect.approved,
            'message': f"Aspecto «{aspect.name}» {estado_txt}.",
            'trait_progress': aspect.trait.approved_percentage, # Enviar progreso actualizado del Trait
            'factor_progress': aspect.trait.factor.approved_percentage, # Enviar progreso actualizado del Factor
            'project_progress': aspect.trait.factor.project.progress # Enviar progreso actualizado del Proyecto
        })
    
    # Redirigir a la página de detalle de la característica (Trait)
    return redirect('trait_detail', pk=aspect.trait.pk)
