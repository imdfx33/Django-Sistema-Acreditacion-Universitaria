from django.shortcuts import render, redirect
from django.contrib import messages
from .models import Form
from database.models import File  
from calendar_create_event.models import Event # Importa también el modelo Event
import uuid
import os
from django.core.files.storage import default_storage
from datetime import datetime

def generate_id():
    return uuid.uuid4().hex[:10]

def gestion_formularios(request):

    formularios = Form.objects.all()
    return render(request, 'formularios/gestion_formularios.html', {'formularios': formularios})

def crear_formulario(request):
    if request.method == 'POST':
        try:
            archivo_subido = request.FILES.get('archivo')

            if not archivo_subido:
                messages.error(request, 'Debes subir un archivo')
                return redirect('gestion-formularios')


            Form.objects.create(
                archivo=archivo_subido,
                status='pendiente'
            )
            return redirect('gestion-formularios')

        except Exception as e:
            messages.error(request, f'Error al crear formulario: {str(e)}')
            return redirect('gestion-formularios')

    return redirect('gestion-formularios')

def actualizar_estado(request, form_id):
    if request.method == 'POST':
        try:
            formulario = Form.objects.get(form_id=form_id)
            nuevo_estado = request.POST.get('estado')

            if nuevo_estado not in dict(Form.STATUS_CHOICES).keys():
                messages.error(request, 'Estado inválido')
                return redirect('gestion-formularios')

            formulario.status = nuevo_estado
            formulario.save()

            return redirect('gestion-formularios')

        except Form.DoesNotExist:
            messages.error(request, 'Formulario no encontrado')
            return redirect('gestion-formularios')

        except Exception as e:
            messages.error(request, f'Error al actualizar estado: {str(e)}')
            return redirect('gestion-formularios')

    return redirect('gestion-formularios')

def adjuntar_pdf(request, form_id):
    if request.method == 'POST':
        try:
            formulario = Form.objects.get(form_id=form_id)
            archivo = request.FILES.get('archivo')

            if not archivo:
                messages.error(request, 'Debes seleccionar un archivo PDF')
                return redirect('gestion-formularios')

            # Guardar archivo
            nombre_archivo_completo = archivo.name
            nombre_archivo, extension = os.path.splitext(nombre_archivo_completo)
            ruta_archivo = os.path.join('informes', f"{uuid.uuid4().hex}.pdf")
            default_storage.save(ruta_archivo, archivo)

            # Determinar el tipo de archivo
            tipo_archivo = extension.lstrip('.')


            evento_asociado = Event.objects.first()  # Ejemplo: toma el primer evento

            if not evento_asociado:
                messages.error(request, 'No se pudo asociar el archivo PDF a un evento.')
                return redirect('gestion-formularios')

            # Crear registro de archivo
            pdf_report_obj = File.objects.create(
                name=nombre_archivo,
                type=tipo_archivo,
                id_event=evento_asociado
            )

            # Asociar al formulario
            formulario.pdf_report = pdf_report_obj
            formulario.save()

            return redirect('gestion-formularios')

        except Exception as e:
            messages.error(request, f'Error al adjuntar PDF: {str(e)}')
            return redirect('gestion-formularios')

    return redirect('gestion-formularios')

