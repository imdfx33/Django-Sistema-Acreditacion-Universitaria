# factorManager/forms.py
from django import forms

from login.models import Rol
from .models import Factor
from projects.models import Project # Asegúrate que la importación es correcta
from django.contrib.auth import get_user_model

User = get_user_model()

class _DatesAndPonderationMixin:
    """
    Mixin para validar fechas y ponderación de un Factor.
    """
    def clean_ponderation(self):
        ponderation = self.cleaned_data.get('ponderation')
        if ponderation is not None and not (0 < ponderation <= 100):
            raise forms.ValidationError("La ponderación debe estar entre 1 y 100.")
        return ponderation

    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        project = cleaned_data.get('project')

        # 1. Fecha de inicio no puede ser posterior a la fecha de fin.
        if start_date and end_date and end_date < start_date:
            self.add_error('end_date', "La fecha de finalización debe ser posterior o igual a la fecha inicial del factor.")

        # 2. Fechas del factor deben estar dentro del rango de fechas del proyecto asociado.
        if project:
            if start_date and start_date < project.start_date:
                self.add_error('start_date', 
                               f"La fecha de inicio del factor ({start_date.strftime('%Y-%m-%d')}) "
                               f"no puede ser anterior a la fecha de inicio del proyecto ({project.start_date.strftime('%Y-%m-%d')}).")
            if end_date and end_date > project.end_date:
                self.add_error('end_date', 
                               f"La fecha de finalización del factor ({end_date.strftime('%Y-%m-%d')}) "
                               f"no puede ser posterior a la fecha de finalización del proyecto ({project.end_date.strftime('%Y-%m-%d')}).")
        return cleaned_data


class FactorCreateForm(_DatesAndPonderationMixin, forms.ModelForm):
    """
    Formulario para la creación de Factores.
    El campo 'project' se presenta como seleccionable.
    Los responsables se pueden asignar durante la creación.
    """
    project = forms.ModelChoiceField(
        queryset=Project.objects.all(), # Idealmente, filtrar por proyectos a los que el usuario tiene acceso de EDITOR
        label='Proyecto Asociado',
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    # El campo 'responsables' ya está en el modelo Factor, se usará el widget por defecto (select multiple)
    # Si se quiere un widget diferente (ej. CheckboxSelectMultiple), se puede definir aquí.

    class Meta:
        model = Factor
        fields = [
            'project', 'name', 'description', 
            'start_date', 'end_date', 'ponderation', 
            'responsables' # Campo ManyToMany para los responsables
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nombre del Factor'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Descripción detallada del factor'}),
            'start_date': forms.DateInput(
                attrs={'type': 'date', 'class': 'form-control'},
                format='%Y-%m-%d'
            ),
            'end_date': forms.DateInput(
                attrs={'type': 'date', 'class': 'form-control'},
                format='%Y-%m-%d'
            ),
            'ponderation': forms.NumberInput(attrs={'class': 'form-control', 'min': '1', 'max': '100'}),
            'responsables': forms.SelectMultiple(attrs={'class': 'form-select select2-multiple', 'multiple': 'multiple'}),
        }
        labels = {
            'name': 'Nombre del Factor',
            'description': 'Descripción',
            'start_date': 'Fecha de Inicio',
            'end_date': 'Fecha de Finalización',
            'ponderation': 'Ponderación',
            'responsables': 'Usuarios Responsables del Factor',
        }

    def __init__(self, *args, **kwargs):
        requesting_user = kwargs.pop('user', None)
        project_from_url = kwargs.pop('project_id', None) # Recibe el ID del proyecto desde la URL
        super().__init__(*args, **kwargs)

        if requesting_user:
            # Filtrar queryset de proyectos para el campo 'project'
            # SuperAdmin/Akadi ven todos. MiniAdmins solo los que tienen rol EDITOR.
            if not (requesting_user.is_superuser or getattr(requesting_user, 'has_elevated_permissions', False)):
                from assignments.models import ProjectAssignment, AssignmentRole
                editable_project_ids = ProjectAssignment.objects.filter(
                    user=requesting_user,
                    role=AssignmentRole.EDITOR
                ).values_list('project_id', flat=True)
                self.fields['project'].queryset = Project.objects.filter(id_project__in=editable_project_ids)
            else:
                self.fields['project'].queryset = Project.objects.all()

            # Limitar queryset de 'responsables' a usuarios que no sean SuperAdmin/Akadi/MiniAdmin
            excluded_roles = [Rol.SUPERADMIN, Rol.MINIADMIN, Rol.ACADI] # Asumiendo que Rol está importado desde login.models
            self.fields['responsables'].queryset = User.objects.exclude(rol__in=excluded_roles).order_by('first_name', 'last_name')
        
        if project_from_url:
            try:
                project_instance = Project.objects.get(id_project=project_from_url)
                self.fields['project'].initial = project_instance
                self.fields['project'].widget = forms.HiddenInput() # Ocultar si viene de URL
                # Si el proyecto viene predefinido, se pueden ajustar las fechas mínima y máxima de los datepickers
                self.fields['start_date'].widget.attrs['min'] = project_instance.start_date.strftime('%Y-%m-%d')
                self.fields['start_date'].widget.attrs['max'] = project_instance.end_date.strftime('%Y-%m-%d')
                self.fields['end_date'].widget.attrs['min'] = project_instance.start_date.strftime('%Y-%m-%d')
                self.fields['end_date'].widget.attrs['max'] = project_instance.end_date.strftime('%Y-%m-%d')
            except Project.DoesNotExist:
                pass # Manejar si el proyecto no existe, aunque la vista debería encargarse.

class FactorUpdateForm(_DatesAndPonderationMixin, forms.ModelForm):
    """
    Formulario para la edición de Factores.
    No permite cambiar el proyecto asociado.
    El enlace al documento de Drive es editable.
    """
    class Meta:
        model = Factor
        # 'project' no se incluye porque no debería cambiarse una vez creado el factor.
        # 'responsables' se maneja vía la página de asignaciones o una sección dedicada si se prefiere.
        fields = [
            'name', 'description', 
            'start_date', 'end_date', 'ponderation',
            'document_link' # Permitir editar el link al documento
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'start_date': forms.DateInput(
                attrs={'type': 'date', 'class': 'form-control'},
                format='%Y-%m-%d'
            ),
            'end_date': forms.DateInput(
                attrs={'type': 'date', 'class': 'form-control'},
                format='%Y-%m-%d'
            ),
            'ponderation': forms.NumberInput(attrs={'class': 'form-control', 'min': '1', 'max': '100'}),
            'document_link': forms.URLInput(attrs={'class': 'form-control', 'placeholder': 'https://docs.google.com/document/d/...'}),
        }
        labels = {
            'name': 'Nombre del Factor',
            'description': 'Descripción',
            'start_date': 'Fecha de Inicio',
            'end_date': 'Fecha de Finalización',
            'ponderation': 'Ponderación (%)',
            'document_link': 'Enlace al Documento de Google Drive',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Al editar, el campo 'project' no está en 'fields', pero lo necesitamos para validación
        if self.instance and self.instance.pk:
            self.cleaned_data = getattr(self, 'cleaned_data', {}) # Asegurar que cleaned_data exista
            self.cleaned_data['project'] = self.instance.project
            # Ajustar min/max de fechas según el proyecto del factor
            project_instance = self.instance.project
            self.fields['start_date'].widget.attrs['min'] = project_instance.start_date.strftime('%Y-%m-%d')
            self.fields['start_date'].widget.attrs['max'] = project_instance.end_date.strftime('%Y-%m-%d')
            self.fields['end_date'].widget.attrs['min'] = project_instance.start_date.strftime('%Y-%m-%d')
            self.fields['end_date'].widget.attrs['max'] = project_instance.end_date.strftime('%Y-%m-%d')

