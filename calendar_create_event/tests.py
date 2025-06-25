from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from calendar_create_event.models import Event

User = get_user_model()

class CreateEventWebTest(TestCase):
    def setUp(self):
        # Creamos al Director con cedula, email y contraseña
        self.user = User.objects.create_user(
            cedula='12345678',
            email='director@gmail.com',
            password='Pass123!'
        )
        # Activamos al usuario para poder hacer login
        self.user.is_active = True
        self.user.save()
        # Logueamos usando la cedula
        self.client.login(cedula='12345678', password='Pass123!')

    def test_create_event_success(self):
        response = self.client.post(
            reverse('create_event'),
            {
                'title': 'Reacreditación',
                'description': 'Planificación reacreditación',
                'date': '2025-06-15',
                'time': '09:00',
                'meeting_type': 'Virtual',
                'location': '',
                'link': 'https://zoom.us/abc',
                'participants': []
            },
            follow=True
        )
        self.assertRedirects(response, reverse('create_event'))
        messages = list(response.context['messages'])
        self.assertTrue(any("Evento creado y correos enviados." in str(m) for m in messages))
        self.assertEqual(Event.objects.count(), 1)
        ev = Event.objects.first()
        self.assertEqual(ev.title, 'Reacreditación')
        self.assertEqual(ev.meeting_type, 'Virtual')
        self.assertEqual(ev.link, 'https://zoom.us/abc')

    def test_create_event_missing_title(self):
        response = self.client.post(
            reverse('create_event'),
            {
                'title': '',
                'description': 'Plan reacreditación',
                'date': '2025-06-15',
                'time': '09:00',
                'meeting_type': 'Presencial',
                'location': 'Sala 1',
                'link': '',
                'participants': []
            }
        )
        self.assertEqual(response.status_code, 200)
        self.assertFormError(response, 'form', 'title', 'Este campo es obligatorio.')

class GuardarEventoApiTest(TestCase):
    def setUp(self):
        # Creamos dos usuarios participantes
        self.u1 = User.objects.create_user(
            cedula='11111111', email='u1@gmail.com', password='Aa1!aaaa'
        )
        self.u1.is_active = True; self.u1.save()
        self.u2 = User.objects.create_user(
            cedula='22222222', email='u2@gmail.com', password='Bb2@bbbb'
        )
        self.u2.is_active = True; self.u2.save()

    def test_guardar_evento_success(self):
        payload = {
            "title": "Reacreditación",
            "description": "Plan reacreditación",
            "date": "2025-06-15",
            "time": "09:00",
            "meetingType": "Virtual",
            "link": "https://zoom.us/abc",
            "participants": [self.u1.cedula, self.u2.cedula]
        }
        response = self.client.post(
            reverse('guardar_evento'),
            data=payload,
            content_type='application/json'
        )
        self.assertJSONEqual(response.content, {"success": True})
        ev = Event.objects.get(title="Reacreditación")
        # Ahora los participantes se asignan por cedula
        self.assertCountEqual(
            ev.participants.values_list('cedula', flat=True),
            ['11111111', '22222222']
        )

    def test_guardar_evento_method_not_allowed(self):
        response = self.client.get(reverse('guardar_evento'))
        self.assertJSONEqual(response.content, {
            "success": False,
            "error": "Método no permitido"
        })

class EditEventTest(TestCase):
    def setUp(self):
        # Director activo
        self.user = User.objects.create_user(
            cedula='33333333',
            email='dir2@gmail.com',
            password='Cc3#cccc'
        )
        self.user.is_active = True; self.user.save()
        self.client.login(cedula='33333333', password='Cc3#cccc')
        # Evento inicial
        self.ev = Event.objects.create(
            title='Reacreditación vieja',
            description='Desc',
            date='2025-06-15',
            time='09:00',
            meeting_type='Presencial',
            location='Sala 1',
            link=''
        )

    def test_edit_event_get_and_post(self):
        resp = self.client.get(reverse('edit_event', args=[self.ev.id]))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Reacreditación vieja')

        resp2 = self.client.post(
            reverse('edit_event', args=[self.ev.id]),
            {
                'title': 'Reacreditación nueva',
                'description': 'Desc nueva',
                'date': '2025-06-20',
                'time': '11:00',
                'meeting_type': 'Presencial',
                'location': 'Sala 2',
                'link': '',
                'participants': []
            },
            follow=True
        )
        self.assertRedirects(resp2, reverse('create_event'))
        ev = Event.objects.get(pk=self.ev.id)
        self.assertEqual(ev.title, 'Reacreditación nueva')
        self.assertEqual(ev.location, 'Sala 2')
