# projects/views.py
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.shortcuts import redirect, get_object_or_404
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.contrib.auth.decorators import login_required
from reports.models import FinalReport   

from .models import Project
from .forms import ProjectForm
from assignments.models import AssignmentRole, ProjectAssignment, FactorAssignment
from core.permissions import FilteredListPermissionMixin, ObjectPermissionRequiredMixin 
from login.models import Rol # Asegúrate de importar Rol
# Asegúrate que los nombres de los mixins coincidan con tu core/permissions.py
# En la Fase 1 se llamaban FilteredListPermissionMixin y ObjectPermissionRequiredMixin
# En el archivo de proyecto se usaron ListPermissionMixin y PermissionRequiredMixin, usaré los de la Fase 1.

from core.permissions import get_project_permission # Helper para obtener el rol del usuario en un proyecto

class AdminOrElevatedAccessRequiredMixin(UserPassesTestMixin):
    """
    Permite el acceso solo a superusuarios o usuarios con el rol de SuperAdmin o Akadi.
    """
    def test_func(self):
        user = self.request.user
        return user.is_authenticated and (user.is_superuser or getattr(user, 'has_elevated_permissions', False))

    def handle_no_permission(self):
        messages.error(self.request, "No tienes permiso para realizar esta acción.")
        if not self.request.user.is_authenticated:
            return redirect('login')
        return redirect('home') # O a una página de 'acceso denegado'


class ProjectListView(LoginRequiredMixin, FilteredListPermissionMixin, ListView):
    """
    Lista los proyectos.
    - Superusuarios/Akadi ven todos los proyectos.
    - MiniAdmins y otros usuarios ven solo los proyectos a los que están asignados.
    Permite filtrar por estado de aprobación.
    """
    model = Project
    template_name = 'projects/project_list.html'
    context_object_name = 'projects'
    paginate_by = 10 # Opcional: para paginación

    def get_queryset(self):
        # FilteredListPermissionMixin ya filtra los proyectos base según la asignación del usuario.
        qs = super().get_queryset() 
        
        # Filtrar adicionalmente por estado de aprobación (approved)
        show_completed_param = self.request.GET.get('show_completed', 'false') # Por defecto no mostrar completados
        show_completed = show_completed_param.lower() in ['true', '1', 'yes']
        
        # Si no se quiere mostrar completados, se filtran los que NO están aprobados.
        # Si se quiere mostrar completados, se filtran los que SÍ están aprobados.
        qs = qs.filter(approved=show_completed)
        
        return qs.order_by('-start_date', 'name')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        user = self.request.user
        context['can_create_project'] = user.is_superuser or getattr(user, 'has_elevated_permissions', False)

        # ---  NUEVO  ------------------------------------------------------ #
        # ¿El queryset global (todos los proyectos) está 100 % finalizado?
        context['all_finalized']  = not Project.objects.exclude(progress=100).exists()

        # Informe final más reciente (si existe)
        context['latest_report'] = FinalReport.objects.first()
        # ------------------------------------------------------------------ #

        show_completed_param = self.request.GET.get('show_completed', 'false')
        context['show_completed'] = show_completed_param.lower() in ['true', '1', 'yes']
        return context
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        context['can_create_project'] = user.is_superuser or getattr(user, 'has_elevated_permissions', False)
        
        # Condición para mostrar el botón de generar informe
        context['all_finalized'] = not Project.objects.exclude(progress=100).exists()
        context['user_can_generate_report'] = (
            user.is_authenticated and
            (user.is_superuser or getattr(user, 'rol', None) in (Rol.SUPERADMIN, Rol.ACADI))
        )
        
        # Informe final más reciente (si existe)
        context['latest_report'] = FinalReport.objects.order_by('-generated_at').first()
        
        show_completed_param = self.request.GET.get('show_completed', 'false')
        context['show_completed'] = show_completed_param.lower() in ['true', '1', 'yes']
        return context    


class ProjectDetailView(LoginRequiredMixin, ObjectPermissionRequiredMixin, DetailView):
    """
    Muestra el detalle de un proyecto y sus factores asociados.
    Los permisos para ver el detalle se basan en la asignación al proyecto.
    Los factores listados también se filtran según los permisos del usuario sobre ellos.
    """
    model = Project
    template_name = 'projects/project_detail.html'
    context_object_name = 'project'
    # Roles que pueden ver el detalle del proyecto
    permission_required_roles = [
        AssignmentRole.LECTOR,
        AssignmentRole.COMENTADOR,
        AssignmentRole.EDITOR,
    ]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        project = self.object
        user = self.request.user

        # El rol del usuario en este proyecto (ya establecido por ObjectPermissionRequiredMixin en request.current_permission_role)
        user_project_role = getattr(self.request, 'current_permission_role', None)
        context['user_project_role'] = user_project_role

        # Determinar permisos específicos basados en el rol
        can_edit = user_project_role == AssignmentRole.EDITOR
        context['can_edit_project'] = can_edit
        context['can_delete_project'] = can_edit
        context['can_approve_project'] = can_edit 
        context['can_add_factor'] = can_edit

        # Listar factores:
        # - Si el usuario es EDITOR del proyecto (MiniAdmin del proyecto), ve todos los factores.
        # - Si el usuario tiene otro rol en el proyecto (Lector, Comentador), solo ve los factores
        #   a los que tiene asignación directa.
        # - Si el usuario es SuperAdmin/Akadi, ve todos los factores (ya cubierto por ObjectPermissionRequiredMixin que da EDITOR).
        
        if user_project_role == AssignmentRole.EDITOR:
            factors_qs = project.factors.all()
        else: # Lector o Comentador del proyecto (o usuario normal sin rol directo en proyecto pero con acceso a factores)
            # Obtener IDs de factores a los que el usuario está asignado directamente DENTRO de este proyecto.
            assigned_factor_ids = FactorAssignment.objects.filter(
                user=user,
                factor__project=project
            ).values_list('factor_id', flat=True)
            factors_qs = project.factors.filter(id_factor__in=assigned_factor_ids)
        
        context['factors'] = factors_qs.order_by('name')
        return context


class ProjectCreateView(LoginRequiredMixin, AdminOrElevatedAccessRequiredMixin, CreateView):
    """
    Permite la creación de nuevos proyectos.
    Solo accesible para Superusuarios de Django o usuarios con roles SuperAdmin/Akadi.
    """
    model = Project
    form_class = ProjectForm
    template_name = 'projects/project_form.html'
    success_url = reverse_lazy('project_list')

    def form_valid(self, form):
        # Asignar el usuario actual como creador del proyecto.
        project = form.save(commit=False)
        project.created_by = self.request.user
        project.save() # El método save del modelo Project se encarga de _ensure_folder
        
        # Si el creador es SuperAdmin o Akadi, se le asigna como EDITOR del proyecto automáticamente.
        # Los MiniAdmins se asignan a través de la interfaz de asignaciones.
        if self.request.user.is_superuser or getattr(self.request.user, 'has_elevated_permissions', False):
            ProjectAssignment.objects.get_or_create(
                project=project,
                user=self.request.user,
                defaults={'role': AssignmentRole.EDITOR}
            )
            
        messages.success(self.request, f"Proyecto «{project.name}» creado correctamente.")
        return redirect(self.success_url)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form_title'] = "Crear Nuevo Proyecto"
        return context


class ProjectUpdateView(LoginRequiredMixin, ObjectPermissionRequiredMixin, UpdateView):
    """
    Permite la edición de un proyecto existente.
    Solo accesible para usuarios con rol EDITOR en el proyecto o SuperAdmin/Akadi.
    """
    model = Project
    form_class = ProjectForm
    template_name = 'projects/project_form.html'
    permission_required_roles = [AssignmentRole.EDITOR] # Solo editores pueden modificar

    def get_success_url(self):
        # Redirigir al detalle del proyecto actualizado.
        return reverse_lazy('project_detail', kwargs={'pk': self.object.pk})

    def form_valid(self, form):
        messages.success(self.request, f"Proyecto «{self.object.name}» actualizado correctamente.")
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form_title'] = f"Editar Proyecto: {self.object.name}"
        return context


class ProjectDeleteView(LoginRequiredMixin, ObjectPermissionRequiredMixin, DeleteView):
    """
    Permite la eliminación de un proyecto.
    Solo accesible para usuarios con rol EDITOR en el proyecto o SuperAdmin/Akadi.
    """
    model = Project
    template_name = 'projects/project_confirm_delete.html'
    success_url = reverse_lazy('project_list')
    permission_required_roles = [AssignmentRole.EDITOR] # Solo editores pueden eliminar

    def form_valid(self, form): # Django llama a form_valid en DeleteView para confirmar la eliminación
        project_name = self.object.name
        # La señal pre_delete en models.py se encargará de la lógica de Drive.
        response = super().form_valid(form)
        messages.success(self.request, f"Proyecto «{project_name}» eliminado correctamente.")
        return response
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['delete_target_name'] = self.object.name
        return context


@login_required
def project_approve(request, pk):
    """
    Vista funcional para aprobar un proyecto.
    Solo usuarios con rol EDITOR en el proyecto o SuperAdmin/Akadi pueden aprobar.
    El proyecto debe tener un progreso del 100%.
    """
    project = get_object_or_404(Project, pk=pk)
    user_role_on_project = get_project_permission(request.user, project)

    if user_role_on_project != AssignmentRole.EDITOR:
        messages.error(request, "No tienes permiso para aprobar este proyecto.")
        raise PermissionDenied("No tienes permiso para aprobar este proyecto.")

    if project.progress < 100:
        messages.error(request, f"No se puede aprobar el proyecto «{project.name}» porque su progreso es inferior al 100% ({project.progress}%).")
    elif project.approved:
        messages.info(request, f"El proyecto «{project.name}» ya se encuentra aprobado.")
    else:
        project.approved = True
        project.save(update_fields=['approved'])
        messages.success(request, f"Proyecto «{project.name}» aprobado correctamente.")
    
    return redirect('project_detail', pk=project.pk)

