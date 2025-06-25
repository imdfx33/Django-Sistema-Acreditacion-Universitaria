# projects/forms.py
from django import forms
from .models import Project

class _DatesMixin:
    """
    Mixin para validar que la fecha de inicio no sea posterior a la fecha de fin.
    """
    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')

        if start_date and end_date and end_date < start_date:
            raise forms.ValidationError(
                "La fecha final debe ser posterior o igual a la fecha inicial."
            )
        return cleaned_data

class ProjectForm(_DatesMixin, forms.ModelForm):
    """
    Formulario para la creación y edición de Proyectos.
    """
    class Meta:
        model = Project
        # Campos que se mostrarán en el formulario.
        # 'created_by' se asignará automáticamente en la vista.
        # 'progress' y 'folder_id' se manejan internamente por el modelo.
        fields = ['name', 'start_date', 'end_date']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nombre del Proyecto'}),
            'start_date': forms.DateInput(
                attrs={'type': 'date', 'class': 'form-control'},
                format='%Y-%m-%d'  # Asegura que el formato sea el esperado por el widget HTML5
            ),
            'end_date': forms.DateInput(
                attrs={'type': 'date', 'class': 'form-control'},
                format='%Y-%m-%d'  # Asegura que el formato sea el esperado por el widget HTML5
            ),
        }
        labels = {
            'name': 'Nombre del Proyecto',
            'start_date': 'Fecha de Inicio',
            'end_date': 'Fecha de Finalización',
        }

    def __init__(self, *args, **kwargs):
        # Se puede capturar el usuario si se necesita lógica de permisos a nivel de formulario.
        # self.user = kwargs.pop('user', None) 
        super().__init__(*args, **kwargs)
        # Ejemplo: Deshabilitar campos si el usuario no tiene permisos elevados.
        # if self.user and not self.user.has_elevated_permissions:
        #     for field_name in self.fields:
        #         self.fields[field_name].disabled = True
