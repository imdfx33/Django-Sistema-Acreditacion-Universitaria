# aspectList/views.py
from django.views.generic import ListView, DetailView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q

from aspectManager.models import Aspect
from traitManager.models import Trait
from factorManager.models import Factor
from projects.models import Project

from core.permissions import (
    FilteredListPermissionMixin, 
    ObjectPermissionRequiredMixin,
    get_aspect_permission, # Para el detalle
    can_edit as permission_can_edit
)
from assignments.models import AssignmentRole, ProjectAssignment, FactorAssignment # User para filtros

class AspectListView(LoginRequiredMixin, FilteredListPermissionMixin, ListView):
    model = Aspect
    template_name = 'aspectList/aspect_list.html'
    context_object_name = 'aspects'
    paginate_by = 15

    def get_queryset(self):
        qs = super().get_queryset().select_related('trait', 'trait__factor', 'trait__factor__project')
        qs = qs.order_by('trait__factor__project__name', 'trait__factor__name', 'trait__name', 'name')
        
        search_query = self.request.GET.get('q')
        project_filter_id = self.request.GET.get('project_id')
        factor_filter_id = self.request.GET.get('factor_id')
        trait_filter_id = self.request.GET.get('trait_id')
        approved_filter = self.request.GET.get('approved')

        if search_query:
            qs = qs.filter(
                Q(name__icontains=search_query) | 
                Q(description__icontains=search_query) |
                Q(acceptance_criteria__icontains=search_query)
            )
        if project_filter_id:
            qs = qs.filter(trait__factor__project_id=project_filter_id)
        if factor_filter_id:
            qs = qs.filter(trait__factor_id=factor_filter_id)
        if trait_filter_id:
            qs = qs.filter(trait_id=trait_filter_id)
        if approved_filter in ['true', 'false']:
            qs = qs.filter(approved=(approved_filter == 'true'))
            
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user

        # Lógica para filtros disponibles similar a TraitListView, pero un nivel más abajo
        if user.is_superuser or getattr(user, 'has_elevated_permissions', False):
            context['available_projects'] = Project.objects.all().order_by('name')
            context['available_factors'] = Factor.objects.all().order_by('project__name', 'name')
            context['available_traits'] = Trait.objects.all().order_by('factor__name', 'name')
            context['can_create_aspect_anywhere'] = True
        elif getattr(user, 'is_mini_admin_role', False):
            editor_project_ids = ProjectAssignment.objects.filter(user=user, role=AssignmentRole.EDITOR).values_list('project_id', flat=True)
            context['available_projects'] = Project.objects.filter(id_project__in=editor_project_ids).order_by('name')
            context['available_factors'] = Factor.objects.filter(project_id__in=editor_project_ids).order_by('project__name', 'name')
            context['available_traits'] = Trait.objects.filter(factor__project_id__in=editor_project_ids).order_by('factor__name', 'name')
            context['can_create_aspect_anywhere'] = editor_project_ids.exists()
        else: 
            assigned_factor_ids = FactorAssignment.objects.filter(user=user).values_list('factor_id', flat=True)
            context['available_traits'] = Trait.objects.filter(factor_id__in=assigned_factor_ids).select_related('factor__project').order_by('factor__project__name', 'factor__name', 'name')
            
            factor_ids_from_assigned_traits = context['available_traits'].values_list('factor_id', flat=True).distinct()
            context['available_factors'] = Factor.objects.filter(id_factor__in=factor_ids_from_assigned_traits).select_related('project').order_by('project__name', 'name')

            project_ids_from_assigned_factors = context['available_factors'].values_list('project_id', flat=True).distinct()
            context['available_projects'] = Project.objects.filter(id_project__in=project_ids_from_assigned_factors).order_by('name')
            context['can_create_aspect_anywhere'] = False

        context['approved_choices'] = [('', 'Todos'), ('true', 'Aprobado'), ('false', 'Pendiente')]
        context['current_project_filter'] = self.request.GET.get('project_id')
        context['current_factor_filter'] = self.request.GET.get('factor_id')
        context['current_trait_filter'] = self.request.GET.get('trait_id')
        context['current_approved_filter'] = self.request.GET.get('approved')
        context['current_search_query'] = self.request.GET.get('q')

        # Para el botón de editar en la lista
        editable_aspects_pks = set()
        for aspect in context['aspects']:
            role_on_aspect = get_aspect_permission(user, aspect) # Permiso sobre el aspecto (heredado)
            if permission_can_edit(role_on_aspect):
                editable_aspects_pks.add(aspect.pk)
        context['editable_aspects_pks'] = editable_aspects_pks
        return context

class AspectDetailView(LoginRequiredMixin, ObjectPermissionRequiredMixin, DetailView):
    model = Aspect
    template_name = "aspectList/aspect_detail.html"
    context_object_name = "aspect"
    permission_required_roles = [
        AssignmentRole.LECTOR,
        AssignmentRole.COMENTADOR,
        AssignmentRole.EDITOR,
    ]

    def get_object_for_permission(self):
        if not hasattr(self, '_object_for_permission_cached'):
            aspect = super().get_object()
            # El permiso para ver un Aspecto se basa en el permiso sobre sí mismo (que hereda de Trait -> Factor)
            self._object_for_permission_cached = aspect
        return self._object_for_permission_cached

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        aspect = self.object
        user = self.request.user

        user_aspect_role = getattr(self.request, 'current_permission_role', None)
        context['user_aspect_role'] = user_aspect_role
        
        can_edit_this_aspect = permission_can_edit(user_aspect_role)
        context['can_edit_aspect'] = can_edit_this_aspect
        context['can_delete_aspect'] = can_edit_this_aspect
        context['can_toggle_approval'] = can_edit_this_aspect

        context['trait'] = aspect.trait
        context['factor'] = aspect.trait.factor
        context['project'] = aspect.trait.factor.project
        return context
