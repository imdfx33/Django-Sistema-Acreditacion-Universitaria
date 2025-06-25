# traitManager/tests.py

from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.contrib.messages import get_messages
from datetime import date, timedelta
from django.core.exceptions import ValidationError
from django.db import models
from unittest.mock import MagicMock, patch

# ── Stubs para evitar llamadas externas en Factor.save ──
import factorManager.models as fm_mod
fm_mod.Factor.save = lambda self, *args, **kwargs: models.Model.save(self, *args, **kwargs)

from projects.models      import Project
from factorManager.models import Factor
from traitManager.models  import Trait, generate_id_trait
from traitManager.forms   import TraitForm

User = get_user_model()

class ModelTests(TestCase):
    def test_generate_id_trait_length(self):
        tid = generate_id_trait()
        self.assertTrue(isinstance(tid, str) and len(tid) == 10)

    def test_str_method(self):
        t = Trait()
        t.name = 'TestTrait'
        self.assertEqual(str(t), 'TestTrait')

    def test_approved_percentage_zero(self):
        t = Trait()
        # Preparamos un mock para aspects que devuelva count=0
        mock_aspects = MagicMock()
        mock_aspects.count.return_value = 0
        with patch.object(Trait, 'aspects', new=mock_aspects):
            self.assertEqual(t.approved_percentage, 0)

    def test_approved_percentage_nonzero(self):
        t = Trait()
        # Mock para aspects con total=5 y aprobados=2
        mock_aspects = MagicMock()
        mock_aspects.count.return_value = 5
        mock_filter = MagicMock()
        mock_filter.count.return_value = 2
        mock_aspects.filter.return_value = mock_filter

        with patch.object(Trait, 'aspects', new=mock_aspects):
            expected = int(2 * 100 / 5)
            self.assertEqual(t.approved_percentage, expected)

class FormTests(TestCase):
    def setUp(self):
        # Evitar creación de carpeta en Project
        import projects.models as proj_mod
        proj_mod.Project._ensure_folder = lambda self: None

        self.project = Project.objects.create(
            name='P', start_date=date.today(),
            end_date=date.today() + timedelta(days=3)
        )
        self.factor = Factor.objects.create(
            project=self.project,
            name='F', start_date=date.today(),
            end_date=date.today() + timedelta(days=2),
            ponderation=10
        )

    def test_valid_form(self):
        data = {
            'factor': self.factor.pk,
            'name': 'NewTrait',
            'description': 'Una descripción'
        }
        form = TraitForm(data=data)
        self.assertTrue(form.is_valid())

    def test_missing_name(self):
        form = TraitForm(data={'factor': self.factor.pk, 'name': '', 'description': 'Desc'})
        self.assertFalse(form.is_valid())
        self.assertIn('name', form.errors)

    def test_missing_factor(self):
        form = TraitForm(data={'name': 'NT', 'description': 'Desc'})
        self.assertFalse(form.is_valid())
        self.assertIn('factor', form.errors)

class ViewTests(TestCase):
    def setUp(self):
        # Evitar creación de carpeta en Project
        import projects.models as proj_mod
        proj_mod.Project._ensure_folder = lambda self: None

        self.client = Client()
        # Superusuario con @gmail.com
        self.superuser = User.objects.create_superuser(
            cedula='00010',
            email='admin10@gmail.com',
            password='Aa1!aaaa'
        )
        self.client.force_login(self.superuser)

        # Proyecto y Factor
        self.project = Project.objects.create(
            name='ProjV', start_date=date.today(),
            end_date=date.today() + timedelta(days=1)
        )
        self.factor = Factor.objects.create(
            project=self.project,
            name='FV', start_date=self.project.start_date,
            end_date=self.project.end_date,
            ponderation=5
        )

        # Trait existente y asignación de responsable
        self.trait = Trait.objects.create(
            factor=self.factor, name='Existing', description='Ex'
        )
        self.factor.responsables.add(self.superuser)

    def test_factor_add_trait_denied_for_unauthorized(self):
        other = User.objects.create_user(
            cedula='00011',
            email='user11@gmail.com',
            password='Aa1!aaaa'
        )
        self.client.force_login(other)
        resp = self.client.post(
            reverse('factor_add_trait', args=[self.factor.pk]),
            {'trait_id': self.trait.pk}
        )
        self.assertRedirects(resp, reverse('factor_detail', args=[self.factor.pk]))
        msgs = list(get_messages(resp.wsgi_request))
        self.assertTrue(any("No tienes permiso" in str(m) for m in msgs))

    def test_factor_add_trait_success(self):
        resp = self.client.post(
            reverse('factor_add_trait', args=[self.factor.pk]),
            {'trait_id': self.trait.pk}
        )
        self.assertRedirects(resp, reverse('factor_detail', args=[self.factor.pk]))
        self.trait.refresh_from_db()
        self.assertIn(self.trait, self.factor.traits.all())

    def test_trait_create_for_factor_denied_without_permission(self):
        other = User.objects.create_user(
            cedula='00012',
            email='user12@gmail.com',
            password='Aa1!aaaa'
        )
        self.client.force_login(other)
        resp = self.client.get(reverse('trait_create_for_factor', args=[self.factor.pk]))
        self.assertRedirects(resp, reverse('factor_detail', args=[self.factor.pk]))
        msgs = list(get_messages(resp.wsgi_request))
        self.assertTrue(any("No tienes permiso" in str(m) for m in msgs))

    def test_trait_create_for_factor_get_and_post(self):
        # GET válido
        resp = self.client.get(reverse('trait_create_for_factor', args=[self.factor.pk]))
        self.assertEqual(resp.status_code, 200)
        # POST crea Trait
        data = {'factor': self.factor.pk, 'name': 'BrandNew', 'description': 'Desc Nuevo'}
        resp2 = self.client.post(
            reverse('trait_create_for_factor', args=[self.factor.pk]),
            data
        )
        self.assertRedirects(resp2, reverse('factor_detail', args=[self.factor.pk]))
        self.assertTrue(Trait.objects.filter(name='BrandNew').exists())

    def test_global_create_redirect_when_no_factors(self):
        Factor.objects.all().delete()
        resp = self.client.get(reverse('trait_create'))
        self.assertRedirects(resp, reverse('factor_list'))
        msgs = list(get_messages(resp.wsgi_request))
        self.assertTrue(any("Debes crear al menos" in str(m) for m in msgs))
