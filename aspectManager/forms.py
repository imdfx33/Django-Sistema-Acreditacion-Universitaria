# aspectManager/forms.py
from django import forms
from .models import Aspect
from traitManager.models import Trait # Para seleccionar el Trait padre
from login.models import User, Rol # Para lógica de permisos si es necesario
from assignments.models import ProjectAssignment, FactorAssignment, AssignmentRole # Para filtrar querysets
from core.permissions import get_trait_permission # Para verificar permisos
from django.db.models import Q, Sum # <--- IMPORTACIÓN 'Sum' AÑADIDA

class AspectForm(forms.ModelForm):
    """
    Formulario para la creación y edición de Aspectos.
    El campo 'trait' (Característica) se presenta como seleccionable.
    """
    trait = forms.ModelChoiceField(
        queryset=Trait.objects.all(), # Este queryset se refinará en __init__
        label='Característica Asociada',
        widget=forms.Select(attrs={'class': 'form-select'}),
        help_text="Selecciona la característica a la que pertenecerá este aspecto."
    )

    class Meta:
        model = Aspect
        fields = [
            'trait', 'name', 'description',
            'weight', 'acceptance_criteria', 'evaluation_rule',
            'approved' # Permitir marcar como aprobado/pendiente desde el form de edición
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nombre del Aspecto'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Descripción detallada del aspecto'}),
            'weight': forms.NumberInput(attrs={'class': 'form-control', 'min': '0', 'max': '100', 'step': '0.01'}),
            'acceptance_criteria': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Criterios para considerar este aspecto como cumplido'}),
            'evaluation_rule': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Regla o método de evaluación'}),
            'approved': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        labels = {
            'name': 'Nombre del Aspecto',
            'description': 'Descripción',
            'weight': 'Peso (%) en la Característica',
            'acceptance_criteria': 'Criterio de Aceptación',
            'evaluation_rule': 'Regla de Evaluación',
            'approved': '¿Aspecto Cumplido/Aprobado?',
        }

    def __init__(self, *args, **kwargs):
        requesting_user = kwargs.pop('user', None)
        trait_from_url = kwargs.pop('trait_id', None)
        super().__init__(*args, **kwargs)

        if requesting_user:
            # Filtrar queryset de Características (Traits).
            # El usuario debe tener permiso de EDITOR sobre el Factor padre del Trait.
            if requesting_user.is_superuser or getattr(requesting_user, 'has_elevated_permissions', False):
                self.fields['trait'].queryset = Trait.objects.all().select_related('factor', 'factor__project').order_by('factor__project__name', 'factor__name', 'name')
            else:
                # 1. Factores de proyectos donde el usuario es EDITOR
                editor_project_ids = ProjectAssignment.objects.filter(
                    user=requesting_user, role=AssignmentRole.EDITOR
                ).values_list('project_id', flat=True)
                
                # 2. Factores a los que el usuario está asignado directamente como EDITOR
                editor_factor_ids = FactorAssignment.objects.filter(
                    user=requesting_user, role=AssignmentRole.EDITOR
                ).values_list('factor_id', flat=True)

                # El usuario puede seleccionar traits de factores en proyectos que edita O factores que edita directamente.
                self.fields['trait'].queryset = Trait.objects.filter(
                    Q(factor__project_id__in=editor_project_ids) | Q(factor_id__in=editor_factor_ids)
                ).distinct().select_related('factor', 'factor__project').order_by('factor__project__name', 'factor__name', 'name')

        if trait_from_url:
            try:
                trait_instance = Trait.objects.get(id_trait=trait_from_url)
                self.fields['trait'].initial = trait_instance
                # Si el trait viene de la URL y el usuario solo tiene permiso sobre ese trait/factor para crear,
                # podríamos ocultar el campo.
                if requesting_user and not (requesting_user.is_superuser or getattr(requesting_user, 'has_elevated_permissions', False)):
                    user_trait_role = get_trait_permission(requesting_user, trait_instance) # Permiso sobre el Trait (heredado del Factor)
                    if user_trait_role == AssignmentRole.EDITOR:
                        if self.fields['trait'].queryset.count() == 1 and self.fields['trait'].queryset.first() == trait_instance:
                           self.fields['trait'].widget = forms.HiddenInput()
            except Trait.DoesNotExist:
                pass
        
        if not self.fields['trait'].queryset.exists() and not trait_from_url:
            self.fields['trait'].disabled = True
            self.fields['trait'].help_text = "No hay características disponibles o no tienes permiso para crear aspectos en ninguna."
            
    def clean_weight(self):
        weight = self.cleaned_data.get("weight")
        if weight is not None and not (0 <= weight <= 100): # Permitir 0 si es válido
            raise forms.ValidationError("El peso debe estar entre 0 y 100.")
        return weight

    def clean(self):
        cleaned_data = super().clean()
        trait = cleaned_data.get('trait')
        weight = cleaned_data.get('weight')

        if trait and weight is not None:
            current_aspect_id = self.instance.pk if self.instance and self.instance.pk else None
            
            other_aspects_weight_sum = trait.aspects.exclude(
                pk=current_aspect_id 
            ).aggregate(total_weight=Sum('weight'))['total_weight'] or 0 # CORREGIDO: Usar Sum directamente
            
            total_proposed_weight = other_aspects_weight_sum + weight

            if total_proposed_weight > 100:
                remaining_weight = 100 - other_aspects_weight_sum
                self.add_error('weight', 
                               f"La suma de los pesos de los aspectos para la característica '{trait.name}' "
                               f"no puede exceder 100%. Actualmente es {other_aspects_weight_sum}%. "
                               f"Puedes asignar un máximo de {remaining_weight:.2f}% a este aspecto.")
        return cleaned_data

class AspectUpdateForm(AspectForm): # Hereda de AspectForm
    """
    Formulario específico para la actualización de Aspectos.
    El campo 'trait' no es editable.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            self.fields['trait'].widget = forms.HiddenInput() 
            self.fields['trait'].initial = self.instance.trait 
            self.fields['trait'].queryset = Trait.objects.filter(pk=self.instance.trait.pk)
