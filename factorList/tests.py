# tests.py
import sys
from datetime import date, timedelta
from django.test import TestCase, Client, RequestFactory, override_settings
from django.urls import reverse, resolve
from django.http import HttpResponse
from django.contrib.auth import get_user_model
from django.contrib.messages import get_messages
from unittest.mock import patch, MagicMock, PropertyMock

# Cover module imports
import factorList.admin as admin_module
import factorList.apps as apps_module
import factorList.models as models_module
import factorList.urls as urls_module
import factorList.views as views_module

User = get_user_model()
from projects.models import Project
from factorManager.models import Factor


class ModuleImportTests(TestCase):
    def test_import_admin(self):
        """Covers import of admin.py"""
        __import__('factorList.admin')

    def test_import_models(self):
        """Covers import of models.py (empty)"""
        __import__('factorList.models')

    def test_app_config(self):
        """Covers AppConfig in apps.py"""
        cfg = apps_module.FactorlistConfig('factorList', 'factorList')
        self.assertEqual(cfg.name, 'factorList')
        self.assertEqual(cfg.default_auto_field, 'django.db.models.BigAutoField')


class UrlsTests(TestCase):
    def test_urlpatterns_resolve(self):
        """Covers URL patterns in urls.py via resolve()"""
        mapping = {
            'factor_list': '',
            'factor_detail': 'XYZ/',
            'factor_approve': 'XYZ/approve',
            'factor_reject': 'XYZ/reject',
        }
        for name, path in mapping.items():
            match = resolve(f'/{path}', urlconf=urls_module)
            self.assertEqual(match.url_name, name)


class FactorListViewTests(TestCase):
    def setUp(self):
        # Patch rendering to avoid template issues
        self.list_patcher = patch.object(
            views_module.FactorListView,
            'render_to_response',
            lambda self, context, **kwargs: HttpResponse('OK')
        )
        self.list_patcher.start()
        self.client = Client()
        self.user = User.objects.create_superuser(
            cedula='00001', email='a@gmail.com', password='Aa1!aaaa'
        )
        self.client.force_login(self.user)
        # Create a project
        self.project = Project.objects.create(
            name='P',
            start_date=date.today(),
            end_date=date.today() + timedelta(days=5)
        )
        # Create two factors
        self.f1 = Factor.objects.create(
            project=self.project,
            name='F1',
            start_date=date.today(),
            end_date=date.today() + timedelta(days=1),
            ponderation=10
        )
        self.f2 = Factor.objects.create(
            project=self.project,
            name='F2',
            start_date=date.today(),
            end_date=date.today() + timedelta(days=2),
            ponderation=20,
            status='approved'
        )

    def tearDown(self):
        self.list_patcher.stop()

    def test_list_no_filters(self):
        """Covers default get_queryset and context_data branches"""
        resp = self.client.get(reverse('factor_list'))
        self.assertEqual(resp.content, b'OK')

    def test_filter_by_name(self):
        """Covers filtering by 'q' parameter"""
        resp = self.client.get(reverse('factor_list') + '?q=F1')
        self.assertEqual(resp.content, b'OK')

    def test_filter_by_project(self):
        """Covers filtering by 'proyecto' parameter"""
        resp = self.client.get(reverse('factor_list') + f'?proyecto={self.project.pk}')
        self.assertEqual(resp.content, b'OK')

    def test_filter_by_status(self):
        """Covers filtering by 'estado' parameter"""
        resp = self.client.get(reverse('factor_list') + '?estado=approved')
        self.assertEqual(resp.content, b'OK')

    def test_filter_by_dates(self):
        """Covers filtering by 'start_date' and 'end_date' parameters"""
        sd = (date.today() - timedelta(days=1)).isoformat()
        ed = (date.today() + timedelta(days=3)).isoformat()
        resp = self.client.get(reverse('factor_list') + f'?start_date={sd}&end_date={ed}')
        self.assertEqual(resp.content, b'OK')


class FactorDetailApproveRejectTests(TestCase):
    def setUp(self):
        # Patch render to avoid template loading
        self.render_patcher = patch('factorList.views.render', lambda req, tpl, ctx: HttpResponse('DETAIL'))
        self.render_patcher.start()
        self.client = Client()
        self.user = User.objects.create_superuser(
            cedula='00002', email='b@gmail.com', password='Aa1!aaaa'
        )
        self.client.force_login(self.user)
        self.project = Project.objects.create(
            name='P2',
            start_date=date.today(),
            end_date=date.today() + timedelta(days=5)
        )
        self.factor = Factor.objects.create(
            project=self.project,
            name='F3',
            start_date=date.today(),
            end_date=date.today() + timedelta(days=1),
            ponderation=30
        )

    def tearDown(self):
        self.render_patcher.stop()

    def test_detail_view(self):
        """Covers factor_detail view logic"""
        resp = self.client.get(reverse('factor_detail', args=[self.factor.pk]))
        self.assertEqual(resp.content, b'DETAIL')

    def test_approve_error_if_incomplete(self):
        """Covers branch where approved_percentage < 100"""
        resp = self.client.post(reverse('factor_approve', args=[self.factor.pk]))
        self.factor.refresh_from_db()
        self.assertNotEqual(self.factor.status, 'approved')
        msgs = list(get_messages(resp.wsgi_request))
        self.assertTrue(any("No puedes aprobar un factor" in str(m) for m in msgs))

    def test_approve_success_when_complete(self):
        """Covers branch where approved_percentage >= 100"""
        # Patch property on class
        with patch.object(
            Factor, 'approved_percentage',
            new_callable=PropertyMock,
            return_value=100
        ):
            resp = self.client.post(reverse('factor_approve', args=[self.factor.pk]))
        self.factor.refresh_from_db()
        self.assertEqual(self.factor.status, 'approved')
        msgs = list(get_messages(resp.wsgi_request))
        self.assertTrue(any("aprobado" in str(m) for m in msgs))

    def test_reject_always(self):
        """Covers reject_factor view"""
        resp = self.client.post(reverse('factor_reject', args=[self.factor.pk]))
        self.factor.refresh_from_db()
        self.assertEqual(self.factor.status, 'rejected')
        msgs = list(get_messages(resp.wsgi_request))
        self.assertTrue(any("rechazado" in str(m) for m in msgs))
