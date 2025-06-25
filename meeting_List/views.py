from django.shortcuts import render, redirect
from calendar_create_event.models import Event
from django.contrib.auth.decorators import login_required
from datetime import datetime, timedelta, date
from django.utils import timezone
# Create your views here.


@login_required
def list_events(request):
    user = request.user
    events = Event.objects.filter(participants=user).order_by('-date', '-time')
    return render(request, 'list_events.html', {'events': events})


def get_week_days(start_date):
    """ Retorna la semana desde el domingo hasta sábado """
    start_of_week = start_date - timedelta(days=start_date.weekday() + 1 if start_date.weekday() != 6 else 0)
    return [start_of_week + timedelta(days=i) for i in range(7)]

def calendar(request):
    today = datetime.today()
    start_param = request.GET.get('start')
    if start_param:
        start_of_week = datetime.strptime(start_param, "%Y-%m-%d")
    else:
        start_of_week = today - timedelta(days=today.weekday())  # lunes de esta semana

    # Fechas de la semana (lunes a domingo)
    week_days = [start_of_week + timedelta(days=i) for i in range(7)]

    # Eventos en la semana
    events = Event.objects.filter(date__range=[week_days[0].date(), week_days[-1].date()])

    # Agrupar eventos por día
    events_by_day = []
    for day in week_days:
        day_events = events.filter(date=day.date()).order_by('time')
        events_by_day.append((day, day_events))

    context = {
        'week_days': week_days,
        'events_by_day': events_by_day,
        'prev_start': (start_of_week - timedelta(days=7)).strftime("%Y-%m-%d"),
        'next_start': (start_of_week + timedelta(days=7)).strftime("%Y-%m-%d"),
    }
    return render(request, 'calendar.html', context)
