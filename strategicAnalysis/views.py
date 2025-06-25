from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods, require_POST
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
import json
from .models import Dofa, PlanMejoramiento

User = get_user_model()

@login_required(login_url='login')
def submit_request(request):
    attached_files_info = request.session.pop('attached_files_info', None)

    context = {
        'attached_files_info': attached_files_info,
        # ... otros datos de contexto ...
    }
    return render(request, 'strategicAnalysis/submit_request.html', context)

@login_required(login_url='login')
def matrix_DOFA(request):
    test_user = None
    try:
        test_user = User.objects.get(cedula='1058932590')
    except User.DoesNotExist:
        print("ERROR CRÍTICO: El usuario de prueba con cédula '1058932590' no existe.")
        pass

    latest_dofa = None
    if test_user:
        latest_dofa = Dofa.objects.filter(user=test_user).order_by('-updated_at').first()

    context = {}
    if latest_dofa:

        context = {
            'fortalezas_data': latest_dofa.fortalezas if latest_dofa.fortalezas is not None else "",
            'debilidades_data': latest_dofa.debilidades if latest_dofa.debilidades is not None else "",
            'oportunidades_data': latest_dofa.oportunidades if latest_dofa.oportunidades is not None else "",
            'amenazas_data': latest_dofa.amenazas if latest_dofa.amenazas is not None else "",
            'existing_dofa_id': latest_dofa.dofa_id
        }
    return render(request, 'strategicAnalysis/matrixDOFA.html', context)


@require_http_methods(["POST"])
def save_dofa_data_view(request):
    test_user = None
    try:
        test_user = User.objects.get(cedula='1058932590')
    except User.DoesNotExist:
        print("ERROR CRÍTICO: El usuario de prueba no existe para guardar.")
        return JsonResponse({'status': 'error', 'message': "Usuario de prueba no encontrado para guardar."}, status=500)

    try:
        request_data = json.loads(request.body.decode('utf-8'))

        fortalezas_text = request_data.get('fortalezas', '')
        debilidades_text = request_data.get('debilidades', '')
        oportunidades_text = request_data.get('oportunidades', '')
        amenazas_text = request_data.get('amenazas', '')

        dofa_instance = Dofa.objects.create(
            user=test_user,
            fortalezas=fortalezas_text,
            debilidades=debilidades_text,
            oportunidades=oportunidades_text,
            amenazas=amenazas_text
        )
        message = 'Análisis DOFA guardado exitosamente (modo prueba).'

        return JsonResponse({
            'status': 'success',
            'message': message,
            'dofa_id': dofa_instance.dofa_id
        })
    except json.JSONDecodeError:
        return JsonResponse({'status': 'error', 'message': 'Error en el formato de los datos generales recibidos (payload no es JSON).'}, status=400)
    except Exception as e:
        user_identifier = test_user.cedula if test_user else 'N/A'
        print(f"Error saving DOFA for test user (cedula: {user_identifier}): {e}")
        return JsonResponse({'status': 'error', 'message': 'Ocurrió un error inesperado al guardar el análisis DOFA (modo prueba).'}, status=500)

MAIN_PLAN_ID = "improvement_plan"
@login_required(login_url='login')
def plan_mejoramiento_view(request, pk=None):
    plan_instancia = None
    current_plan_id_to_load = pk if pk else MAIN_PLAN_ID
    try:
        plan_instancia, created = PlanMejoramiento.objects.get_or_create(
            plan_id=current_plan_id_to_load,
            defaults={
                'title': f'Plan de Mejoramiento ({current_plan_id_to_load})',
                'contenido_json': {'plan_texto': '', 'notas_texto': ''}
            }
        )
        if created:
            print(f"Plan de Mejoramiento (sin notas) CREADO con plan_id: {current_plan_id_to_load}")
        else:
            print(f"Plan de Mejoramiento (sin notas) CARGADO con plan_id: {current_plan_id_to_load}")

    except Exception as e:
        print(f"Error crítico al obtener o crear PlanMejoramiento (sin notas) con plan_id {current_plan_id_to_load}: {e}")
        plan_instancia = None

    data_for_template = {
        'plan_id': plan_instancia.plan_id if plan_instancia else current_plan_id_to_load, # Pasar siempre un plan_id
        'plan_texto': plan_instancia.plan_texto if plan_instancia else "",

    }

    context = {
        'plan_data': data_for_template,
    }
    return render(request, 'strategicAnalysis/improvement_plan.html', context)


@require_POST # Asegura que esta vista solo acepte peticiones POST
def save_plan(request):
    try:
        data = json.loads(request.body)
        plan_id_from_frontend = data.get('plan_id')
        plan_texto_data = data.get('plan_texto', '')
        notas_texto_data = data.get('notas_texto', '')

        if not plan_id_from_frontend:
            return JsonResponse({'status': 'error', 'message': 'No se proporcionó plan_id.'}, status=400)

        plan_instancia = get_object_or_404(PlanMejoramiento, plan_id=plan_id_from_frontend)

        plan_instancia.plan_texto = plan_texto_data

        if plan_id_from_frontend == MAIN_PLAN_ID:
            plan_instancia.notas_texto = ""
        else:
            plan_instancia.notas_texto = notas_texto_data

        plan_instancia.save()

        print(f"Plan de Mejoramiento ACTUALIZADO con plan_id: {plan_id_from_frontend}")
        return JsonResponse({'status': 'success', 'message': 'Plan guardado exitosamente.'})

    except PlanMejoramiento.DoesNotExist:
        print(f"Error en save_plan: PlanMejoramiento con plan_id {plan_id_from_frontend} no existe.")
        return JsonResponse({'status': 'error', 'message': f'Plan con ID {plan_id_from_frontend} no encontrado.'}, status=404)
    except json.JSONDecodeError:
        return JsonResponse({'status': 'error', 'message': 'Error decodificando JSON.'}, status=400)
    except Exception as e:
        print(f"Error inesperado en save_plan: {e}") # Log del error
        return JsonResponse({'status': 'error', 'message': f'Ocurrió un error al guardar: {e}'}, status=500)

@login_required(login_url='login')
def revision_plan_view(request):
    current_plan_id_to_load = MAIN_PLAN_ID
    print(f"REVISION_PLAN_VIEW (CON NOTAS): Intentando cargar plan_id: {current_plan_id_to_load}")

    try:
        plan_instancia = get_object_or_404(PlanMejoramiento, plan_id=current_plan_id_to_load)
        print(f"REVISION_PLAN_VIEW (CON NOTAS): Plan CARGADO con plan_id: {plan_instancia.plan_id}")

    except PlanMejoramiento.DoesNotExist:
        print(f"REVISION_PLAN_VIEW (CON NOTAS): Error - Plan con plan_id {current_plan_id_to_load} NO ENCONTRADO. Esto no debería pasar si se creó primero.")

        plan_instancia = None

    except Exception as e:
        print(f"REVISION_PLAN_VIEW (CON NOTAS): Error crítico al obtener: {e}")
        plan_instancia = None

    data_for_template = {
        'plan_id': plan_instancia.plan_id if plan_instancia else current_plan_id_to_load,
        'plan_texto': plan_instancia.plan_texto if plan_instancia else "",
        'notas_texto': plan_instancia.notas_texto if plan_instancia else "", # <-- PASA LAS NOTAS
    }
    print(f"REVISION_PLAN_VIEW (CON NOTAS): Datos para plantilla: {data_for_template}")

    context = { 'plan_data': data_for_template }
    return render(request, 'strategicAnalysis/revision_plan.html', context)


