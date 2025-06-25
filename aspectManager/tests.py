# aspectManager/tests.py

from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import models
from django.contrib import messages
from django.db.models import Sum
from django.apps import apps
from django.utils.module_loading import import_string
from django.db.models.signals import post_save, post_delete

from unittest.mock import MagicMock, patch

import uuid

# Import the modules to cover admin, apps, forms, models, signals, views, urls
import aspectManager.admin as admin_module
import aspectManager.apps as apps_module
import aspectManager.forms as forms_module
import aspectManager.models as models_module
import aspectManager.signals as signals_module
import aspectManager.views as views_module
import aspectManager.urls as urls_module

from aspectManager.admin import AspectAdmin
from aspectManager.forms import AspectForm, AspectUpdateForm
from aspectManager.models import Aspect, generate_id_aspect
from aspectManager.views import toggle_approval, AspectCreateView, AspectUpdateView, AspectDeleteView
from traitManager.models import Trait
from factorManager.models import Factor
from projects.models import Project

User = get_user_model()


class ModelAndAdminTests(TestCase):
    def test_generate_id_aspect_length(self):
        """generate_id_aspect should produce a 10-char string"""
        tid = generate_id_aspect()
        self.assertIsInstance(tid, str)
        self.assertEqual(len(tid), 10)

    def test_str_and_get_absolute_url(self):
        """__str__ returns name, get_absolute_url calls reverse or raises"""
        a = Aspect(name="TestAspect")
        self.assertEqual(str(a), "TestAspect")
        # patch reverse to avoid NoReverseMatch
        with patch('django.urls.reverse', return_value='/dummy-url/'):
            url = a.get_absolute_url()
            self.assertEqual(url, '/dummy-url/')

    def test_admin_methods(self):
        """Admin total_aspects and approved_count count correctly"""
        admin_instance = AspectAdmin(Aspect, admin_module.admin.site)
        # Create aspect with no related aspects
        a = Aspect.objects.create(
            trait=Trait.objects.create(
                factor=Factor.objects.create(
                    project=Project.objects.create(name="P"),
                    name="F", start_date="2000-01-01", end_date="2000-01-02", ponderation=0
                ),
                name="T", description=""
            ),
            name="A1"
        )
        # total_aspects should be 0
        self.assertEqual(admin_instance.total_aspects(a), 0)
        # approved_count should be 0
        self.assertEqual(admin_instance.approved_count(a), 0)


class AppsTests(TestCase):
    def test_ready_imports_signals(self):
        """Calling ready() should import the signals module without error"""
        # ensure module is not reloaded
        # Call the standalone ready function
        # aspectManager.apps defines ready() at module-level
        ready_func = getattr(apps_module, 'ready')
        # Should not raise
        ready_func(None)


class FormsTests(TestCase):
    def setUp(self):
        # Set up a trait and related objects
        self.project = Project.objects.create(name="P", start_date="2000-01-01", end_date="2000-01-02")
        self.factor = Factor.objects.create(
            project=self.project, name="F", start_date="2000-01-01", end_date="2000-01-02", ponderation=0
        )
        self.trait = Trait.objects.create(factor=self.factor, name="T", description="")

    def test_clean_weight_valid_and_invalid(self):
        """clean_weight accepts 0–100, rejects out-of-range"""
        form = AspectForm(data={
            'trait': self.trait.pk,
            'name': 'A', 'description': '',
            'weight': '50', 'acceptance_criteria': '',
            'evaluation_rule': '', 'approved': False
        }, user=None)
        self.assertTrue(form.is_valid())
        self.assertEqual(form.clean_weight(), 50)
        form_bad = AspectForm(data={
            'trait': self.trait.pk,
            'name': 'A', 'description': '',
            'weight': '-1', 'acceptance_criteria': '',
            'evaluation_rule': '', 'approved': False
        }, user=None)
        with self.assertRaises(ValidationError):
            form_bad.clean_weight()

    def test_clean_exceeding_total_weight(self):
        """clean() adds error if total weights would exceed 100%"""
        # simulate that other aspects sum to 80%
        mock_manager = MagicMock()
        mock_manager.exclude.return_value.aggregate.return_value = {'total_weight': 80}
        # patch trait.aspects
        self.trait.aspects = mock_manager
        form = AspectForm(data={
            'trait': self.trait.pk,
            'name': 'A', 'description': '',
            'weight': '30', 'acceptance_criteria': '',
            'evaluation_rule': '', 'approved': False
        }, user=None)
        # Force full_clean to run clean()
        form.is_bound = True
        form.data = form.data
        form.full_clean()
        self.assertIn('weight', form.errors)
        self.assertIn('no puede exceder 100%', form.errors['weight'][0])


class SignalTests(TestCase):
    def setUp(self):
        # Create necessary objects
        self.project = Project.objects.create(name="P", start_date="2000-01-01", end_date="2000-01-02")
        self.factor = Factor.objects.create(
            project=self.project, name="F", start_date="2000-01-01", end_date="2000-01-02", ponderation=0
        )
        self.trait = Trait.objects.create(factor=self.factor, name="T", description="")

    def test_update_cascade_on_aspect_save_and_delete(self):
        """Saving or deleting an Aspect should trigger factor.save() once per signal"""
        # patch factor.save
        original_save = self.factor.save
        self.factor.save = MagicMock()
        a = Aspect(trait=self.trait, name="A", description="")
        a.save()  # triggers post_save on Aspect
        self.assertTrue(self.factor.save.called)
        self.factor.save.reset_mock()
        a.delete()  # triggers post_delete on Aspect
        self.assertTrue(self.factor.save.called)
        # restore
        self.factor.save = original_save

    def test_update_project_progress_on_factor_save(self):
        """Saving a Factor triggers project.update_progress(save=True)"""
        # patch project.update_progress
        self.project.update_progress = MagicMock()
        self.factor.save()
        self.project.update_progress.assert_called_with(save=True)


class ViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.superuser = User.objects.create_superuser(
            cedula="000", email="u@example.com", password="pass"
        )
        self.client.force_login(self.superuser)
        # Create minimal Trait for creation
        self.project = Project.objects.create(name="P", start_date="2000-01-01", end_date="2000-01-02")
        self.factor = Factor.objects.create(
            project=self.project, name="F", start_date="2000-01-01", end_date="2000-01-02", ponderation=0
        )
        self.trait = Trait.objects.create(factor=self.factor, name="T", description="")
        # Create existing Aspect
        self.aspect = Aspect.objects.create(trait=self.trait, name="A", description="")

    def test_dispatch_no_traits_redirect(self):
        """If no Trait exists, GET create view redirects with error"""
        Trait.objects.all().delete()
        resp = self.client.get(reverse('aspectManager:aspect_create'))
        self.assertRedirects(resp, reverse('trait_list'))
        msgs = list(messages.get_messages(resp.wsgi_request))
        self.assertTrue(any("No existen características" in str(m) for m in msgs))

    @patch('aspectManager.views.get_aspect_permission', return_value=None)
    @patch('aspectManager.views.permission_can_edit', return_value=False)
    def test_create_view_denied_forbidden(self, mock_perm, mock_can):
        """If user lacks edit permission on trait, GET create view returns 403"""
        url = reverse('aspectManager:aspect_create') + f'?trait={self.trait.id_trait}'
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 403)

    def test_create_view_get_and_post_success(self):
        """GET returns form, POST creates Aspect and redirects"""
        url = reverse('aspectManager:aspect_create') + f'?trait={self.trait.id_trait}'
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        data = {
            'trait': self.trait.pk,
            'name': 'NewA',
            'description': '',
            'weight': '10',
            'acceptance_criteria': '',
            'evaluation_rule': '',
            'approved': False
        }
        resp2 = self.client.post(url, data)
        self.assertRedirects(resp2, reverse('trait_detail', kwargs={'pk': self.trait.pk}))
        self.assertTrue(Aspect.objects.filter(name='NewA').exists())

    def test_update_view_get_and_post(self):
        """GET edit view and POST update view succeed"""
        url = reverse('aspectManager:aspect_edit', args=[self.aspect.pk])
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        data = {
            'trait': self.trait.pk,
            'name': 'A-upd',
            'description': 'desc',
            'weight': '5',
            'acceptance_criteria': 'c',
            'evaluation_rule': 'r',
            'approved': True
        }
        resp2 = self.client.post(url, data)
        self.assertRedirects(resp2, reverse('aspect_detail', kwargs={'pk': self.aspect.pk}))
        self.aspect.refresh_from_db()
        self.assertEqual(self.aspect.name, 'A-upd')
        self.assertTrue(self.aspect.approved)

    def test_delete_view_get_and_post(self):
        """GET delete view and POST delete view succeed"""
        url = reverse('aspectManager:aspect_delete', args=[self.aspect.pk])
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        resp2 = self.client.post(url)
        self.assertRedirects(resp2, reverse('trait_detail', kwargs={'pk': self.trait.pk}))
        self.assertFalse(Aspect.objects.filter(pk=self.aspect.pk).exists())

    def test_toggle_approval_nonajax_and_ajax(self):
        """toggle_approval denies unauthorized, toggles for authorized"""
        # unauthorized user
        other = User.objects.create_user(cedula="001", email="o@example.com", password="pass")
        self.client.force_login(other)
        # non-AJAX should raise
        with self.assertRaises(PermissionDenied):
            self.client.post(reverse('aspectManager:aspect_toggle_approval', args=[self.aspect.pk]))
        # AJAX returns JSON 403
        resp = self.client.post(
            reverse('aspectManager:aspect_toggle_approval', args=[self.aspect.pk]),
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        self.assertEqual(resp.status_code, 403)
        self.assertEqual(resp.json()['status'], 'error')

        # authorized (superuser) toggles
        self.client.force_login(self.superuser)
        # non-AJAX toggles and redirects
        resp2 = self.client.post(reverse('aspectManager:aspect_toggle_approval', args=[self.aspect.pk]))
        self.assertRedirects(resp2, reverse('trait_detail', kwargs={'pk': self.trait.pk}))
        self.aspect.refresh_from_db()
        self.assertTrue(self.aspect.approved)

        # AJAX toggles again
        resp3 = self.client.post(
            reverse('aspectManager:aspect_toggle_approval', args=[self.aspect.pk]),
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        self.assertEqual(resp3.status_code, 200)
        data = resp3.json()
        self.assertEqual(data['status'], 'ok')
        self.assertFalse(data['approved'])
        self.assertIn('trait_progress', data)
        self.assertIn('factor_progress', data)
        self.assertIn('project_progress', data)
