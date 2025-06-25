# traitList/tests.py

from django.test import TestCase, Client, RequestFactory
from django.urls import reverse, resolve
from django.apps import apps
from django.contrib import admin
import importlib

# Import modules to ensure they load
import traitList.models as models_module
import traitList.admin as admin_module
import traitList.apps as apps_module
import traitList.urls as urls_module
import traitList.views as views_module

from django.contrib.auth import get_user_model
from datetime import date, timedelta
from unittest.mock import patch, MagicMock

# Import models used by the views
from projects.models import Project
from factorManager.models import Factor
from traitManager.models import Trait
from database.models import File
from assignments.models import AssignmentRole, FactorAssignment, ProjectAssignment

User = get_user_model()

class ModuleTests(TestCase):
    def test_import_modules_and_attributes(self):
        # Ensure modules import without errors and attributes exist
        importlib.import_module('traitList.models')
        importlib.import_module('traitList.admin')
        importlib.import_module('traitList.apps')
        importlib.import_module('traitList.urls')
        importlib.import_module('traitList.views')
        self.assertTrue(hasattr(apps_module, 'TraitlistConfig'))
        self.assertTrue(hasattr(views_module, 'TraitListView'))
        self.assertTrue(hasattr(views_module, 'TraitDetailView'))
        self.assertTrue(hasattr(urls_module, 'urlpatterns'))

    def test_apps_config(self):
        config = apps_module.TraitlistConfig('traitList', apps_module)
        self.assertEqual(config.default_auto_field, 'django.db.models.BigAutoField')
        self.assertEqual(config.name, 'traitList')
        self.assertEqual(config.verbose_name, 'Listado de Características')

    def test_admin_module(self):
        # admin module should load and expose admin.site
        self.assertTrue(hasattr(admin_module, 'admin'))
        self.assertTrue(hasattr(admin, 'site'))

    def test_models_module(self):
        # models module loads
        self.assertEqual(models_module.__name__, 'traitList.models')

    def test_urls_patterns(self):
        # urlpatterns contain expected names
        names = [p.name for p in urls_module.urlpatterns]
        self.assertIn('trait_list', names)
        self.assertIn('trait_detail', names)

class TraitListViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_superuser(
            username='admin', email='admin@example.com', password='pass'
        )
        self.client.force_login(self.user)
        self.project = Project.objects.create(
            name='Proj', start_date=date.today(), end_date=date.today() + timedelta(days=5)
        )
        self.factor1 = Factor.objects.create(
            project=self.project,
            name='Factor1',
            start_date=date.today(),
            end_date=date.today() + timedelta(days=1),
            ponderation=10
        )
        self.factor2 = Factor.objects.create(
            project=self.project,
            name='Factor2',
            start_date=date.today() + timedelta(days=2),
            end_date=date.today() + timedelta(days=3),
            ponderation=20,
            status='approved'
        )
        self.trait1 = Trait.objects.create(
            factor=self.factor1, name='Trait1', description='Desc1'
        )
        self.trait2 = Trait.objects.create(
            factor=self.factor2, name='Trait2', description='Desc2'
        )

    def test_list_no_filters(self):
        """Cubre get_queryset con sin filtros y get_context_data para superuser."""
        resp = self.client.get(reverse('trait_list'))
        self.assertEqual(resp.status_code, 200)
        traits = resp.context['traits']
        self.assertIn(self.trait1, traits)
        self.assertIn(self.trait2, traits)
        self.assertIn(self.project, resp.context['available_projects'])
        self.assertIn(self.factor1, resp.context['available_factors'])
        self.assertTrue(resp.context['can_create_trait_anywhere'])
        self.assertEqual(resp.context['current_search_query'], None)

    def test_filter_by_search(self):
        """Cubre filtro 'q' en get_queryset."""
        resp = self.client.get(reverse('trait_list') + '?q=Trait1')
        traits = resp.context['traits']
        self.assertIn(self.trait1, traits)
        self.assertNotIn(self.trait2, traits)

    def test_filter_by_project(self):
        """Cubre filtro 'project_id' en get_queryset."""
        resp = self.client.get(reverse('trait_list') + f'?project_id={self.project.pk}')
        traits = resp.context['traits']
        self.assertIn(self.trait1, traits)
        self.assertIn(self.trait2, traits)

    def test_filter_by_factor(self):
        """Cubre filtro 'factor_id' en get_queryset."""
        resp = self.client.get(reverse('trait_list') + f'?factor_id={self.factor1.pk}')
        traits = resp.context['traits']
        self.assertEqual(list(traits), [self.trait1])

    def test_filter_by_status(self):
        """Cubre filtro 'status' en get_queryset basado en factor__status."""
        resp = self.client.get(reverse('trait_list') + '?status=approved')
        traits = resp.context['traits']
        self.assertIn(self.trait2, traits)
        self.assertNotIn(self.trait1, traits)

    def test_context_for_normal_user(self):
        """Cubre get_context_data para usuario sin permisos elevados o asignaciones."""
        normal = User.objects.create_user(username='user', email='u@example.com', password='pass')
        self.client.force_login(normal)
        resp = self.client.get(reverse('trait_list'))
        self.assertFalse(resp.context['can_create_trait_anywhere'])
        self.assertQuerysetEqual(resp.context['available_projects'], [])
        self.assertQuerysetEqual(resp.context['available_factors'], [])

class TraitDetailViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_superuser(
            username='admin2', email='admin2@example.com', password='pass'
        )
        self.client.force_login(self.user)
        self.project = Project.objects.create(
            name='Proj2', start_date=date.today(), end_date=date.today() + timedelta(days=5)
        )
        self.factor = Factor.objects.create(
            project=self.project,
            name='FactorX',
            start_date=date.today(),
            end_date=date.today() + timedelta(days=1),
            ponderation=15
        )
        self.trait = Trait.objects.create(
            factor=self.factor, name='TraitX', description='DescX'
        )
        # Patch attachments to cover File.objects.filter branch
        self.files = [MagicMock(name='f1'), MagicMock(name='f2')]
        patcher = patch('traitList.views.File.objects.filter', return_value=self.files)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_detail_view_context(self):
        """Cubre get_context_data en TraitDetailView, incluidas ramas de permisos y attachments."""
        resp = self.client.get(reverse('trait_detail', args=[self.trait.pk]))
        self.assertEqual(resp.status_code, 200)
        ctx = resp.context
        self.assertEqual(ctx['trait'], self.trait)
        self.assertEqual(ctx['factor'], self.factor)
        self.assertEqual(ctx['project'], self.project)
        self.assertEqual(list(ctx['aspects']), [])
        self.assertEqual(ctx['total_aspects_count'], 0)
        self.assertEqual(ctx['approved_aspects_count'], 0)
        self.assertEqual(ctx['attachments'], self.files)
        # verificar llaves de permisos
        self.assertIn('can_edit_trait', ctx)
        self.assertFalse(ctx['can_edit_trait'])
        self.assertFalse(ctx['can_add_aspect'])
        self.assertFalse(ctx['can_attach_to_trait'])
