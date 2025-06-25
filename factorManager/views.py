# factorManager/views.py
from venv import logger
from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse_lazy
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.contrib.auth.decorators import login_required
from django.db.models import Q, Count, Prefetch
from django.http import HttpResponseForbidden

from .models import Factor
from projects.models import Project
from traitManager.models import Trait
from aspectManager.models import Aspect # Necesario para calcular progreso
from .forms import FactorCreateForm, FactorUpdateForm # Cambiado FactorForm a FactorUpdateForm
from assignments.models import ProjectAssignment, FactorAssignment, AssignmentRole
from login.models import Rol, User # Para User y Rol

from core.permissions import (
    FilteredListPermissionMixin, 
    ObjectPermissionRequiredMixin,
    get_factor_permission,
    get_project_permission,
    can_edit as permission_can_edit # Alias para evitar colisión
)
from core.mixins import ElevatedAccessRequiredMixin, AdminOrMiniAdminRequiredMixin

class FactorListView(LoginRequiredMixin, FilteredListPermissionMixin, ListView):
    """
    Lista los factores.
    - SuperAdmin/Akadi ven todos los factores.
    - MiniAdmins (EDITOR en proyecto) ven todos los factores de sus proyectos asignados.
    - Usuarios normales ven solo los factores a los que tienen asignación directa.
    Permite filtrar por proyecto y estado.
    """
    model = Factor
    template_name = 'factorManager/factor_list.html'
    context_object_name = 'factors'
    paginate_by = 10

    def get_queryset(self):
        # FilteredListPermissionMixin ya filtra los factores base
        qs = super().get_queryset().select_related('project').prefetch_related('responsables')
        
        project_filter_id = self.request.GET.get('project_id')
        status_filter = self.request.GET.get('status')
        search_query = self.request.GET.get('q')

        if project_filter_id:
            qs = qs.filter(project_id=project_filter_id)
        if status_filter:
            qs = qs.filter(status=status_filter)
        if search_query:
            qs = qs.filter(Q(name__icontains=search_query) | Q(description__icontains=search_query))
            
        return qs.order_by('project__name', 'name')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        
        # Para el filtro de proyectos en el template:
        # SuperAdmin/Akadi ven todos. MiniAdmins solo aquellos donde son EDITOR.
        if user.is_superuser or getattr(user, 'has_elevated_permissions', False):
            context['available_projects'] = Project.objects.all().order_by('name')
            context['can_create_factor_anywhere'] = True
        elif getattr(user, 'is_mini_admin_role', False):
            editable_project_ids = ProjectAssignment.objects.filter(
                user=user, role=AssignmentRole.EDITOR
            ).values_list('project_id', flat=True)
            context['available_projects'] = Project.objects.filter(id_project__in=editable_project_ids).order_by('name')
            # Un MiniAdmin puede crear factores en los proyectos que edita
            context['can_create_factor_anywhere'] = editable_project_ids.exists()
        else:
            # Usuarios normales no pueden crear factores directamente desde esta lista global.
            # Se les asignan factores, no los crean.
            context['available_projects'] = Project.objects.none()
            context['can_create_factor_anywhere'] = False

        context['status_choices'] = Factor.STATUS_CHOICES
        context['current_project_filter'] = self.request.GET.get('project_id')
        context['current_status_filter'] = self.request.GET.get('status')
        context['current_search_query'] = self.request.GET.get('q')
        return context


class FactorDetailView(LoginRequiredMixin, ObjectPermissionRequiredMixin, DetailView):
    """
    Muestra el detalle de un factor, sus características y aspectos.
    Los permisos se basan en la asignación al factor o al proyecto padre.
    """
    model = Factor
    template_name = 'factorManager/factor_detail.html'
    context_object_name = 'factor'
    # Roles que pueden ver el detalle del factor
    permission_required_roles = [
        AssignmentRole.LECTOR,
        AssignmentRole.COMENTADOR,
        AssignmentRole.EDITOR,
    ]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        factor = self.object
        user = self.request.user

        # El rol del usuario en este factor (ya establecido por ObjectPermissionRequiredMixin en request.current_permission_role)
        user_factor_role = getattr(self.request, 'current_permission_role', None)
        context['user_factor_role'] = user_factor_role

        # Determinar permisos específicos
        can_edit = permission_can_edit(user_factor_role)
        context['can_edit_factor'] = can_edit
        context['can_delete_factor'] = can_edit
        context['can_approve_reject_factor'] = can_edit 
        context['can_add_trait'] = can_edit
        context['can_assign_factor'] = can_edit # Si es EDITOR del factor (o del proyecto)

        # Listar características, anotando progreso de aspectos
        # Solo se muestran si el usuario puede ver el factor
        traits_qs = factor.traits.annotate(
            total_aspects=Count('aspects', distinct=True),
            approved_aspects=Count('aspects', filter=Q(aspects__approved=True), distinct=True)
        ).prefetch_related(
            Prefetch('aspects', queryset=Aspect.objects.order_by('name'), to_attr='sorted_aspects')
        )
        
        context['traits'] = traits_qs.order_by('name')
        context['project'] = factor.project # Para breadcrumbs y contexto
        return context

class FactorCreateView(LoginRequiredMixin, CreateView):
    """
    Permite la creación de nuevos factores.
    - SuperAdmin/Akadi pueden crear factores en cualquier proyecto.
    - MiniAdmins (EDITOR de un proyecto) pueden crear factores en ESE proyecto.
    Si se pasa ?project=<project_pk> en la URL, se preselecciona y oculta el proyecto.
    """
    model = Factor
    form_class = FactorCreateForm
    template_name = 'factorManager/factor_form.html'

    def get_project_from_request(self):
        project_id = self.request.GET.get('project')
        if project_id:
            return get_object_or_404(Project, id_project=project_id)
        return None

    def dispatch(self, request, *args, **kwargs):
        project_from_url = self.get_project_from_request()
        user = request.user

        if not (user.is_superuser or getattr(user, 'has_elevated_permissions', False)):
            # Es MiniAdmin o un usuario normal
            if project_from_url: # Creando factor para un proyecto específico
                user_project_role = get_project_permission(user, project_from_url)
                if user_project_role != AssignmentRole.EDITOR:
                    messages.error(request, "No tienes permiso de Editor en este proyecto para crear factores.")
                    return HttpResponseForbidden("No tienes permiso de Editor en este proyecto para crear factores.")
            else: # Intentando crear factor sin especificar proyecto (desde un botón "Crear Factor" genérico)
                  # Solo SuperAdmin/Akadi pueden hacer esto. MiniAdmins deben tener un proyecto como contexto.
                messages.error(request, "Debes seleccionar un proyecto para crear un factor o no tienes permisos suficientes.")
                return redirect('project_list') # O una página de error/dashboard

        if not Project.objects.exists():
            messages.error(request, "No existen proyectos. Debes crear al menos un proyecto antes de añadir factores.")
            return redirect('project_list') # Asumiendo que tienes esta URL

        return super().dispatch(request, *args, **kwargs)
        
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user # Pasar usuario al form para filtrar proyectos
        project_from_url = self.get_project_from_request()
        if project_from_url:
            kwargs['project_id'] = project_from_url.id_project
        return kwargs

    def form_valid(self, form):
        factor = form.save(commit=False)
        
        # Si el proyecto no vino por URL, ya está en form.cleaned_data
        # Si vino por URL, el campo 'project' en el form podría estar oculto, 
        # así que lo reasignamos si es necesario (aunque el form ya debería tenerlo)
        project_from_url = self.get_project_from_request()
        if project_from_url and not form.cleaned_data.get('project'):
            factor.project = project_from_url

        # Inyectar _creator_email para la lógica de Google Docs en Factor.save()
        factor._creator_email = self.request.user.email
        
        try:
            factor.save() # Esto llamará al método save() personalizado del modelo Factor
            form.save_m2m() # Para guardar responsables si el campo está en el form y usa widget por defecto
        except Exception as e:
            logger.error(f"Error al guardar el factor o crear documento de Drive: {e}")
            messages.error(self.request, f"Hubo un error al guardar el factor o al interactuar con Google Drive: {e}")
            return self.form_invalid(form)

        # Si el creador es MiniAdmin EDITOR del proyecto, o SuperAdmin/Akadi,
        # se le asigna rol EDITOR sobre el Factor creado.
        project_role_of_creator = get_project_permission(self.request.user, factor.project)
        if project_role_of_creator == AssignmentRole.EDITOR:
            FactorAssignment.objects.get_or_create(
                factor=factor,
                user=self.request.user,
                defaults={'role': AssignmentRole.EDITOR}
            )
            
        messages.success(self.request, f"Factor «{factor.name}» creado exitosamente.")
        return redirect(self.get_success_url(factor))

    def get_success_url(self, factor=None):
        obj = factor if factor else self.object
        return reverse_lazy('factor_detail', kwargs={'pk': obj.pk})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        project_from_url = self.get_project_from_request()
        if project_from_url:
            context['project_ctx'] = project_from_url
            context['form_title'] = f"Crear Nuevo Factor para el Proyecto: {project_from_url.name}"
        else:
            context['form_title'] = "Crear Nuevo Factor"
        return context

class FactorUpdateView(LoginRequiredMixin, ObjectPermissionRequiredMixin, UpdateView):
    """
    Permite la edición de un factor.
    Solo accesible para usuarios con rol EDITOR en el factor (directo o heredado del proyecto).
    """
    model = Factor
    form_class = FactorUpdateForm 
    template_name = 'factorManager/factor_form.html'
    permission_required_roles = [AssignmentRole.EDITOR]

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        # Para que _DatesAndPonderationMixin pueda acceder al proyecto para validaciones
        if self.object:
            kwargs['initial'] = kwargs.get('initial', {})
            kwargs['initial']['project'] = self.object.project
        return kwargs
        
    def form_valid(self, form):
        factor = form.save(commit=False)
        # Lógica adicional si fuera necesaria antes de super().form_valid()
        # El método save() personalizado de Factor se encargará de is_completed y project.update_progress
        try:
            response = super().form_valid(form)
            messages.success(self.request, f"Factor «{factor.name}» actualizado correctamente.")
            return response
        except Exception as e:
            logger.error(f"Error al actualizar el factor: {e}")
            messages.error(self.request, f"Hubo un error al actualizar el factor: {e}")
            return self.form_invalid(form)


    def get_success_url(self):
        return reverse_lazy('factor_detail', kwargs={'pk': self.object.pk})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form_title'] = f"Editar Factor: {self.object.name}"
        # Si se necesita el proyecto en el contexto para la plantilla (ej. breadcrumbs)
        context['project_ctx'] = self.object.project 
        return context

class FactorDeleteView(LoginRequiredMixin, ObjectPermissionRequiredMixin, DeleteView):
    """
    Permite la eliminación de un factor.
    Solo accesible para usuarios con rol EDITOR en el factor.
    """
    model = Factor
    template_name = 'factorManager/factor_confirm_delete.html'
    permission_required_roles = [AssignmentRole.EDITOR]

    def get_success_url(self):
        # Redirigir a la lista de factores del proyecto al que pertenecía el factor
        project_pk = self.object.project.pk
        return reverse_lazy('project_detail', kwargs={'pk': project_pk})

    def form_valid(self, form):
        factor_name = self.object.name
        project_pk = self.object.project.pk # Guardar antes de eliminar el objeto

        # La señal pre_delete en factorManager.signals se encarga de Drive.
        # El método save() de Project se llama desde la señal post_delete de Factor.
        try:
            super().form_valid(form)
            messages.success(self.request, f"Factor «{factor_name}» eliminado correctamente.")
        except Exception as e:
            logger.error(f"Error al eliminar el factor '{factor_name}': {e}")
            messages.error(self.request, f"Hubo un error al eliminar el factor: {e}")
            return redirect('factor_detail', pk=self.object.pk) # Volver al detalle del factor si falla

        return redirect(reverse_lazy('project_detail', kwargs={'pk': project_pk}))
        
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['delete_target_name'] = self.object.name
        return context


# Vistas para aprobar/rechazar factor (similares a las de projects/views.py para proyectos)
@login_required
def approve_factor(request, pk):
    factor = get_object_or_404(Factor, pk=pk)
    user_role = get_factor_permission(request.user, factor)

    if not permission_can_edit(user_role): # Solo editores pueden aprobar/rechazar
        raise PermissionDenied("No tienes permiso para cambiar el estado de este factor.")

    if factor.approved_percentage < 100:
        messages.error(request, f"No se puede aprobar el factor «{factor.name}» porque su progreso de aspectos es inferior al 100% ({factor.approved_percentage}%).")
    elif factor.status == 'approved':
        messages.info(request, f"El factor «{factor.name}» ya se encuentra aprobado.")
    else:
        factor.status = 'approved'
        factor.save() # Esto llamará a factor.project.update_progress() vía señal
        messages.success(request, f"Factor «{factor.name}» aprobado correctamente.")
    
    return redirect('factor_detail', pk=factor.pk)

@login_required
def reject_factor(request, pk):
    factor = get_object_or_404(Factor, pk=pk)
    user_role = get_factor_permission(request.user, factor)

    if not permission_can_edit(user_role):
        raise PermissionDenied("No tienes permiso para cambiar el estado de este factor.")

    if factor.status == 'rejected':
        messages.info(request, f"El factor «{factor.name}» ya se encuentra rechazado.")
    else:
        factor.status = 'rejected'
        factor.save() # Esto llamará a factor.project.update_progress() vía señal
        messages.success(request, f"Factor «{factor.name}» rechazado correctamente.")
        
    return redirect('factor_detail', pk=factor.pk)

