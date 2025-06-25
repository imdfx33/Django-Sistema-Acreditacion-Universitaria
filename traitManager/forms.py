# traitManager/forms.py
from django import forms
from .models import Trait
from factorManager.models import Factor # Para seleccionar el Factor padre
from login.models import Rol, User # Para lógica de permisos si es necesario en el form
from assignments.models import ProjectAssignment, FactorAssignment, AssignmentRole # Para filtrar querysets
from core.permissions import get_factor_permission # Para verificar permisos
from django.db.models import Q # <--- IMPORTACIÓN AÑADIDA

class TraitForm(forms.ModelForm):
    """
    Formulario para la creación y edición de Características (Traits).
    """
    factor = forms.ModelChoiceField(
        queryset=Factor.objects.all(), # Este queryset se refinará en __init__
        label='Factor Asociado',
        widget=forms.Select(attrs={'class': 'form-select'}),
        help_text="Selecciona el factor al que pertenecerá esta característica."
    )

    class Meta:
        model = Trait
        fields = ['factor', 'name', 'description']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nombre de la Característica'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Descripción detallada de la característica'}),
        }
        labels = {
            'name': 'Nombre de la Característica',
            'description': 'Descripción',
        }

    def __init__(self, *args, **kwargs):
        requesting_user = kwargs.pop('user', None)
        factor_from_url = kwargs.pop('factor_id', None) # Recibe el ID del factor desde la URL para preselección
        super().__init__(*args, **kwargs)

        if requesting_user:
            # Filtrar queryset de factores para el campo 'factor'
            # El usuario debe tener permiso de EDITOR sobre el factor (o el proyecto padre) para crear/asignar características.
            
            # 1. Factores de proyectos donde el usuario es EDITOR
            editor_project_ids = ProjectAssignment.objects.filter(
                user=requesting_user, role=AssignmentRole.EDITOR
            ).values_list('project_id', flat=True)
            
            # 2. Factores a los que el usuario está asignado directamente como EDITOR
            editor_factor_ids = FactorAssignment.objects.filter(
                user=requesting_user, role=AssignmentRole.EDITOR
            ).values_list('factor_id', flat=True)

            # Combinar: factores en proyectos que edita O factores que edita directamente.
            # Usamos Q objects para la condición OR.
            editable_factors_qs = Factor.objects.filter(
                Q(project_id__in=editor_project_ids) | Q(id_factor__in=editor_factor_ids)
            ).distinct().order_by('project__name', 'name')
            
            # Si es superusuario o tiene permisos elevados, ve todos los factores
            if requesting_user.is_superuser or getattr(requesting_user, 'has_elevated_permissions', False):
                self.fields['factor'].queryset = Factor.objects.all().order_by('project__name', 'name')
            else:
                self.fields['factor'].queryset = editable_factors_qs
        
        if factor_from_url:
            try:
                factor_instance = Factor.objects.get(id_factor=factor_from_url)
                self.fields['factor'].initial = factor_instance
                self.fields['factor'].widget = forms.HiddenInput() # Ocultar si viene de URL
            except Factor.DoesNotExist:
                # Si el factor_id de la URL no es válido, el campo se mostrará como un select normal
                # La vista debería manejar este caso si el factor es obligatorio.
                pass
        
        # Si no hay factores seleccionables (y no viene preseleccionado), el campo podría estar vacío.
        # La vista debe manejar el caso de que no haya factores disponibles para el usuario.
        if not self.fields['factor'].queryset.exists() and not factor_from_url:
            # Considera deshabilitar el campo o mostrar un mensaje en lugar de ocultarlo,
            # para que el usuario sepa por qué no puede seleccionar un factor.
            # self.fields['factor'].widget = forms.HiddenInput() 
            self.fields['factor'].disabled = True
            self.fields['factor'].help_text = "No hay factores disponibles para asignar o no tienes permisos."


class TraitUpdateForm(forms.ModelForm):
    """
    Formulario para la edición de Características (Traits).
    No permite cambiar el factor asociado.
    """
    class Meta:
        model = Trait
        fields = ['name', 'description'] # 'factor' no es editable aquí
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
        }
        labels = {
            'name': 'Nombre de la Característica',
            'description': 'Descripción',
        }
