# ARCHIVO: calendar_create_event/views.py

from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from django.template.loader import render_to_string
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test # Importaciones añadidas
from django.conf import settings # Para settings.AUTH_USER_MODEL si es necesario aquí

from .models import Event
from .formsCreateEvent import EventForm
from .utils import send_invitation_email # Asumo que esta función está en utils.py
from login.models import Rol # Importar el modelo Rol de tu app login

import json

# --- Función de prueba de permisos ---
def user_is_admin_for_meetings(user):
    """
    Verifica si el usuario autenticado tiene un rol de administrador
    (SUPERADMIN, MINIADMIN, o ACADI).
    """
    if not user.is_authenticated:
        return False
    # Utilizamos las propiedades del modelo User que ya tienes definidas
    return user.is_super_admin_role or user.is_mini_admin_role or user.is_akadi_role

# --- Vistas protegidas ---

@login_required # Requiere que el usuario esté logueado
@user_passes_test(user_is_admin_for_meetings, login_url='/login/restricted_access/') # Verifica el rol
def create_event(request):
    if request.method == 'POST':
        form = EventForm(request.POST)
        if form.is_valid():
            # No hay campo 'organizer' en el modelo Event proporcionado.
            # Si lo añades en el futuro, aquí es donde lo asignarías:
            # event = form.save(commit=False)
            # event.organizer = request.user
            # event.save()
            # form.save_m2m() # Si el formulario tiene campos ManyToMany que no se guardan con event.save()
            
            event = form.save() # Guardamos el evento según tu modelo actual
            
            _send_invites(event, request) # Pasamos request para posible uso futuro o consistencia
            messages.success(request, 'Evento creado y correos enviados.')
            # Considera redirigir a una vista de lista o detalle del evento en lugar de 'create_event'
            # Por ejemplo: return redirect('calendar_view') o return redirect('event_detail', event_id=event.id)
            return redirect('calendar') 
        else:
            messages.error(request, 'Por favor corrige los errores en el formulario.')
    else:
        form = EventForm()
    return render(request, 'calendar_create_event/create_event.html', {'form': form})

@csrf_exempt # Mantener si es una API interna llamada por JS sin tokens CSRF explícitos
@login_required # Es buena práctica añadir login_required incluso a endpoints @csrf_exempt
def guardar_evento(request):
    # Protección de la API
    if not user_is_admin_for_meetings(request.user):
        return JsonResponse({"success": False, "error": "Acceso denegado. Permisos insuficientes."}, status=403)

    if request.method == "POST":
        try:
            data = json.loads(request.body)
            
            # Validar datos esenciales (ejemplo básico)
            required_fields = ['title', 'description', 'date', 'time', 'meetingType']
            for field in required_fields:
                if field not in data or not data[field]:
                    return JsonResponse({"success": False, "error": f"El campo '{field}' es obligatorio."}, status=400)

            event = Event.objects.create(
                title=data["title"],
                description=data["description"],
                date=data["date"],
                time=data["time"],
                location=(data.get("location") if data.get("meetingType") == "Presencial" else ""),
                link=(data.get("link") if data.get("meetingType") == "Virtual" else ""),
                meeting_type=data["meetingType"],
                # No hay 'organizer' en el modelo Event actual. Si lo añades:
                # organizer=request.user 
            )
            participant_ids = data.get("participants", [])
            if participant_ids: # Asegurarse de que participant_ids no sea None
                 event.participants.set(participant_ids)
            
            _send_invites(event, request)
            return JsonResponse({"success": True, "message": "Evento guardado y correos enviados."})
        except json.JSONDecodeError:
            return JsonResponse({"success": False, "error": "Error al decodificar JSON."}, status=400)
        except Exception as e:
            # Loggear el error real en el servidor para depuración
            # logger.error(f"Error al guardar evento: {str(e)}") 
            return JsonResponse({"success": False, "error": f"Error interno del servidor: {str(e)}"}, status=500)
            
    return JsonResponse({"success": False, "error": "Método no permitido. Se esperaba POST."}, status=405)

@login_required
@user_passes_test(user_is_admin_for_meetings, login_url='/login/restricted_access/')
def edit_event(request, event_id):
    evento = get_object_or_404(Event, id=event_id)
    
    # Opcional: Si además de ser admin, solo el 'organizer' puede editar (si añades campo organizer)
    # if evento.organizer != request.user and not user_is_admin_for_meetings(request.user):
    #     messages.error(request, "No tienes permiso para editar este evento.")
    #     return redirect('calendar_view') # o a donde corresponda

    if request.method == 'POST':
        form = EventForm(request.POST, instance=evento)
        if form.is_valid():
            event = form.save()
            _send_invites(event, request) # Pasamos request
            messages.success(request, 'Evento actualizado y correos reenviados.')
            # Considera redirigir a la vista de detalle del evento o lista
            return redirect('calendar_view') # Asumiendo que 'calendar_view' es la vista de lista/calendario
        else:
            messages.error(request, 'Por favor corrige los errores en el formulario.')
    else:
        form = EventForm(instance=evento)
    return render(request, 'calendar_create_event/edit_event.html', {
        'form': form, 
        'evento': evento
    })

# --- Función de ayuda para enviar invitaciones ---
def _send_invites(event, request): # Añadido request por si es útil para la plantilla o contexto
    """Envía un correo a cada participante con la invitación."""
    subject = f"Invitación: {event.title}"
    # Asegúrate de que settings.AUTH_USER_MODEL está correctamente configurado
    # y que user.email es el campo correcto para el correo.
    for user_participant in event.participants.all():
        html_content = render_to_string('calendar_create_event/email_invitation.html', {
            'event': event,
            'user': user_participant, # El usuario participante que recibe el correo
            'request': request # Opcional, por si la plantilla de correo necesita info del request
        })
        # La función send_invitation_email ya debería manejar el from_email desde settings
        send_invitation_email(user_participant.email, subject, html_content)