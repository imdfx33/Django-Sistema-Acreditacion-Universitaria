from django.test import TestCase

# Create your tests here.
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from datetime import datetime, timedelta
from calendar_create_event.models import Event
from django.contrib.auth import get_user_model

User = get_user_model()

class CalendarViewTest(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            cedula='12345678', email='user1@gmail.com', password='Pass123!'
        )
        self.user.is_active = True
        self.user.save()
        self.client.login(cedula='12345678', password='Pass123!')

    def test_calendar_view_with_events(self):
        today = timezone.now().date()
        Event.objects.create(
            title='Reunión comité',
            description='Discusión',
            date=today,
            time='10:00',
            meeting_type='Virtual',
            link='https://zoom.us/abc',
        ).participants.set([self.user])

        response = self.client.get(reverse('calendar'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Reunión comité')
        self.assertContains(response, today.strftime("%d"))

    def test_calendar_view_no_events(self):
        response = self.client.get(reverse('calendar'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '—')  # Marca de día sin eventos

    def test_calendar_navigation_links(self):
        response = self.client.get(reverse('calendar'))
        self.assertContains(response, 'Semana Anterior')
        self.assertContains(response, 'Semana Siguiente')

    def test_calendar_crash_simulation(self):
        # Simula fallo en la base de datos
        with self.settings(DEBUG_PROPAGATE_EXCEPTIONS=True):
            original = Event.objects.filter
            Event.objects.filter = lambda *args, **kwargs: 1 / 0  # rompe intencionalmente
            with self.assertRaises(ZeroDivisionError):
                self.client.get(reverse('calendar'))
            Event.objects.filter = original  # restaurar

class ListEventsViewTest(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            cedula='98765432', email='miembro@gmail.com', password='Secret456!'
        )
        self.user.is_active = True
        self.user.save()
        self.client.login(cedula='98765432', password='Secret456!')

    def test_list_view_with_user_events(self):
        event = Event.objects.create(
            title='Sesión informativa',
            description='Info importante',
            date='2025-06-15',
            time='09:00',
            meeting_type='Presencial',
            location='Sala 1'
        )
        event.participants.set([self.user])

        response = self.client.get(reverse('list_events'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Sesión informativa')
        self.assertContains(response, 'Sala 1')
        self.assertContains(response, 'Presencial')

    def test_list_view_no_events(self):
        response = self.client.get(reverse('list_events'))
        self.assertContains(response, 'No hay reuniones agendadas aún.')

   
