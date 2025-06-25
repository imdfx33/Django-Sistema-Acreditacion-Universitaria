# traitList/views.py
from django.views.generic import ListView, DetailView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Count, Q, Prefetch, Value, CharField
from django.db.models.functions import Concat

from traitManager.models import Trait
from factorManager.models import Factor
from aspectManager.models import Aspect
from projects.models import Project # Para el filtro de proyectos
from database.models import File # Para adjuntos
from django.contrib.contenttypes.models import ContentType # Para adjuntos

from core.permissions import (
    FilteredListPermissionMixin, 
    ObjectPermissionRequiredMixin,
    get_trait_permission, # Para el detalle
    can_edit as permission_can_edit # Alias
)
from assignments.models import AssignmentRole, FactorAssignment, ProjectAssignment # Para roles

class TraitListView(LoginRequiredMixin, FilteredListPermissionMixin, ListView):
    """
    Lista las Características.
    - SuperAdmin/Akadi ven todas.
    - MiniAdmins (EDITOR en proyecto) ven todas las de sus proyectos.
    - Usuarios normales ven solo aquellas de factores a los que tienen acceso.
    Permite filtrar por factor, estado del factor y proyecto.
    """
    model = Trait
    template_name = 'traitList/trait_list.html'
    context_object_name = 'traits'
    paginate_by = 10

    def get_queryset(self):
        # FilteredListPermissionMixin ya filtra las características base
        qs = super().get_queryset().select_related('factor', 'factor__project').order_by('factor__project__name', 'factor__name', 'name')
        
        search_query = self.request.GET.get('q')
        project_filter_id = self.request.GET.get('project_id')
        factor_filter_id = self.request.GET.get('factor_id')
        # El estado se filtra basado en el estado del factor padre
        status_filter = self.request.GET.get('status') 

        if search_query:
            qs = qs.filter(Q(name__icontains=search_query) | Q(description__icontains=search_query))
        if project_filter_id:
            qs = qs.filter(factor__project_id=project_filter_id)
        if factor_filter_id:
            qs = qs.filter(factor_id=factor_filter_id)
        if status_filter:
            qs = qs.filter(factor__status=status_filter)
            
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user

        # Para los filtros en el template
        # Proyectos disponibles para filtrar:
        if user.is_superuser or getattr(user, 'has_elevated_permissions', False):
            context['available_projects'] = Project.objects.all().order_by('name')
            context['available_factors'] = Factor.objects.all().order_by('project__name', 'name')
            context['can_create_trait_anywhere'] = True 
        elif getattr(user, 'is_mini_admin_role', False):
            editor_project_ids = ProjectAssignment.objects.filter(user=user, role=AssignmentRole.EDITOR).values_list('project_id', flat=True)
            context['available_projects'] = Project.objects.filter(id_project__in=editor_project_ids).order_by('name')
            context['available_factors'] = Factor.objects.filter(project_id__in=editor_project_ids).order_by('project__name', 'name')
            context['can_create_trait_anywhere'] = editor_project_ids.exists()
        else: 
            assigned_factor_ids = FactorAssignment.objects.filter(user=user).values_list('factor_id', flat=True)
            context['available_factors'] = Factor.objects.filter(id_factor__in=assigned_factor_ids).select_related('project').order_by('project__name', 'name')
            project_ids_from_assigned_factors = context['available_factors'].values_list('project_id', flat=True).distinct()
            context['available_projects'] = Project.objects.filter(id_project__in=project_ids_from_assigned_factors).order_by('name')
            context['can_create_trait_anywhere'] = False

        context['status_choices'] = Factor.STATUS_CHOICES 
        context['current_project_filter'] = self.request.GET.get('project_id')
        context['current_factor_filter'] = self.request.GET.get('factor_id')
        context['current_status_filter'] = self.request.GET.get('status')
        context['current_search_query'] = self.request.GET.get('q')
        return context

class TraitDetailView(LoginRequiredMixin, ObjectPermissionRequiredMixin, DetailView):
    model = Trait
    template_name = "traitList/trait_detail.html"
    context_object_name = "trait"
    permission_required_roles = [
        AssignmentRole.LECTOR,
        AssignmentRole.COMENTADOR,
        AssignmentRole.EDITOR,
    ]

    def get_object(self, queryset=None):
        trait = super().get_object(queryset)
        self._object_for_permission = trait 
        return trait

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        trait = self.object
        user = self.request.user

        user_trait_role = getattr(self.request, 'current_permission_role', None)
        context['user_trait_role'] = user_trait_role
        
        can_edit_this_trait = permission_can_edit(user_trait_role)
        context['can_edit_trait'] = can_edit_this_trait
        context['can_delete_trait'] = can_edit_this_trait
        context['can_add_aspect'] = can_edit_this_trait
        context['can_attach_to_trait'] = can_edit_this_trait

        context['factor'] = trait.factor
        context['project'] = trait.factor.project

        aspects_qs = trait.aspects.all().order_by('name')
        context['aspects'] = aspects_qs
        
        # Calcular conteos de aspectos aquí
        context['total_aspects_count'] = aspects_qs.count()
        context['approved_aspects_count'] = aspects_qs.filter(approved=True).count()
        
        ct_trait = ContentType.objects.get_for_model(Trait)
        context['attachments'] = File.objects.filter(content_type=ct_trait, object_id=trait.pk)
        
        return context
