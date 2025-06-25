# tests.py
import sys
from datetime import date, timedelta
from django.test import TestCase, Client, RequestFactory, override_settings
from django.urls import reverse, resolve
from django.core.exceptions import ValidationError, PermissionDenied
from django.contrib.auth import get_user_model
from django.contrib.messages import get_messages
from unittest.mock import patch, MagicMock

# Import app modules
import factorManager.admin as admin_module
import factorManager.apps as apps_module
import factorManager.forms as forms_module
import factorManager.models as models_module
import factorManager.signals as signals_module
import factorManager.urls as urls_module
import factorManager.views as views_module

from factorManager.models import (
    _get_service_credentials,
    _drive_service,
    _docs_service,
    _set_permissions,
    generate_id_factor,
    Factor
)
from factorManager.forms import FactorCreateForm, FactorUpdateForm
from factorManager.signals import trash_factor_drive, _update_project_progress
from factorManager.templatetags.factor_permissions import user_can_edit_factor, user_can_view_factor

User = get_user_model()
from projects.models import Project
from assignments.models import AssignmentRole, FactorAssignment
from traitManager.models import Trait
from aspectManager.models import Aspect


class AdminModuleTests(TestCase):
    def test_admin_registration(self):
        """Cover admin.py import and registration"""
        # Ensure module loads without error
        __import__('factorManager.admin')
        # Check that Factor is registered
        from django.contrib import admin
        from .models import Factor
        self.assertIn(Factor, admin.site._registry)


class AppsTests(TestCase):
    def test_ready_imports_signals(self):
        """Cover AppConfig.ready() imports signals"""
        sys.modules.pop('factorManager.signals', None)
        cfg = apps_module.FactormanagerConfig('factorManager', 'factorManager')
        cfg.ready()
        self.assertIn('factorManager.signals', sys.modules)


class UrlsModuleTests(TestCase):
    def test_urlpatterns_resolve(self):
        """Cover urls.py patterns"""
        # Map name to path
        patterns = {
            'factor_list': '',
            'factor_create': 'create/',
            'factor_detail': '<pk>/',
            'factor_edit': '<pk>/edit/',
            'factor_delete': '<pk>/delete/',
            'factor_approve': '<pk>/approve/',
            'factor_reject': '<pk>/reject/',
        }
        for name, suffix in patterns.items():
            # Build a test URL
            test_path = suffix.replace('<pk>', 'XYZ')
            resolver = resolve(f'/{test_path}', urlconf=urls_module)
            self.assertEqual(resolver.url_name, name)


class FormTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.project = Project.objects.create(
            name='PJ', start_date=date.today(), end_date=date.today() + timedelta(days=5)
        )
        self.user = User.objects.create_user(cedula='1', email='u@x.com', password='pwd')

    def test_clean_ponderation_valid(self):
        """Cover _DatesAndPonderationMixin.clean_ponderation valid"""
        form = forms_module._DatesAndPonderationMixin()
        form.cleaned_data = {'ponderation': 50}
        self.assertEqual(form.clean_ponderation(), 50)

    def test_clean_ponderation_invalid(self):
        """Cover ValidationError when ponderation out of range"""
        form = forms_module._DatesAndPonderationMixin()
        form.cleaned_data = {'ponderation': 0}
        with self.assertRaises(ValidationError):
            form.clean_ponderation()

    def test_clean_dates_invalid(self):
        """Cover clean() date validations in mixin"""
        data = {
            'project': self.project,
            'start_date': self.project.start_date - timedelta(days=1),
            'end_date': self.project.end_date + timedelta(days=1),
            'ponderation': 10
        }
        form = FactorCreateForm(data=data, user=self.user, project_id=None)
        self.assertFalse(form.is_valid())
        msg = str(form.errors)
        self.assertIn('anterior a la fecha de inicio del proyecto', msg)
        self.assertIn('posterior a la fecha de finalización del proyecto', msg)

    def test_factorcreateform_init_user_filter(self):
        """Cover FactorCreateForm __init__ filtering by user and project_id"""
        # User without elevated permissions sees none
        form = FactorCreateForm(user=self.user)
        self.assertEqual(form.fields['project'].queryset.count(), 0)
        # Superuser sees all
        superu = User.objects.create_superuser(cedula='2', email='s@x.com', password='pwd')
        form2 = FactorCreateForm(user=superu)
        self.assertGreaterEqual(form2.fields['project'].queryset.count(), 1)

    def test_factorcreateform_init_project_id(self):
        """Cover hiding project field when project_id passed"""
        form = FactorCreateForm(user=self.user, project_id=self.project.id_project)
        self.assertTrue(isinstance(form.fields['project'].widget, forms_module.forms.HiddenInput))


class ModelUtilsTests(TestCase):
    @override_settings(GOOGLE_SERVICE_ACCOUNT_FILE='file.json',
                       GOOGLE_DRIVE_SCOPES=['s1'],
                       GOOGLE_DOCS_SCOPES=['d2'])
    def test_get_service_credentials_and_services(self):
        """Cover credentials, _drive_service, _docs_service"""
        import google.oauth2.service_account as sc
        with patch.object(sc.Credentials, 'from_service_account_file', return_value='creds') as m_cred, \
             patch('factorManager.models.build', return_value='svc') as m_build:
            creds = _get_service_credentials()
            m_cred.assert_called_once_with('file.json', scopes=['s1', 'd2'])
            ds = _drive_service()
            m_build.assert_called_with('drive', 'v3', credentials='creds', cache_discovery=False)
            self.assertEqual(ds, 'svc')
            docs = _docs_service()
            m_build.assert_called_with('docs', 'v1', credentials='creds', cache_discovery=False)
            self.assertEqual(docs, 'svc')

    def test_set_permissions(self):
        """Cover _set_permissions sharing logic based on user roles"""
        u1 = User.objects.create_user(cedula='3', email='a@x.com', password='pwd')
        u2 = User.objects.create_user(cedula='4', email='b@x.com', password='pwd')
        u1.rol = getattr(models_module, 'Rol', type('R', (), {})).SUPERADMIN = 1
        u1.rol =  getattr(models_module, 'Rol', type('R', (), {})).SUPERADMIN
        u2.rol = 0
        drive = MagicMock()
        patcher = patch('factorManager.models._drive_service', return_value=drive)
        patcher.start()
        try:
            _set_permissions('FID')
            # One perm for each user
            self.assertEqual(drive.permissions().create.call_count, 2)
        finally:
            patcher.stop()

    def test_generate_id_factor(self):
        """Cover generate_id_factor uniqueness and length"""
        id1 = generate_id_factor()
        id2 = generate_id_factor()
        self.assertEqual(len(id1), 10)
        self.assertEqual(len(id2), 10)
        self.assertNotEqual(id1, id2)


class FactorModelTests(TestCase):
    def setUp(self):
        self.project = Project.objects.create(
            name='PM', start_date=date.today(), end_date=date.today() + timedelta(days=2)
        )

    def test_approved_percentage(self):
        """Cover approved_percentage property with and without aspects"""
        # No aspects
        f = Factor(project=self.project, name='A', start_date=self.project.start_date, end_date=self.project.end_date)
        self.assertEqual(f.approved_percentage, 0)
        # Some aspects
        mock_qs = MagicMock(count=MagicMock(return_value=5))
        Aspect.objects.filter = MagicMock(side_effect=[mock_qs, MagicMock(count=MagicMock(return_value=2))])
        f2 = Factor(project=self.project, name='B', start_date=self.project.start_date, end_date=self.project.end_date)
        self.assertEqual(f2.approved_percentage, int(2 * 100 / 5))

    def test_clean_model_dates(self):
        """Cover clean() raising ValidationError for out-of-range dates"""
        f = Factor(project=self.project,
                   name='Z',
                   start_date=self.project.start_date - timedelta(days=1),
                   end_date=self.project.end_date + timedelta(days=1))
        with self.assertRaises(ValidationError):
            f.clean()

    def test_save_creates_doc_and_updates(self):
        """Cover save() flow for new Factor"""
        drive = MagicMock()
        docs = MagicMock()
        docs.documents().create.return_value.execute.return_value = {'documentId': 'doc123'}
        drive.files().update.return_value.execute.return_value = None
        patcher1 = patch('factorManager.models._drive_service', return_value=drive)
        patcher2 = patch('factorManager.models._docs_service', return_value=docs)
        patcher1.start(); patcher2.start()
        try:
            # Ensure project has folder_id and update_progress
            self.project.folder_id = 'fld'
            self.project.save()
            self.project.update_progress = MagicMock()
            f = Factor(project=self.project,
                       name='C',
                       start_date=self.project.start_date,
                       end_date=self.project.end_date,
                       ponderation=10)
            f._creator_email = 'u@x.com'
            f.save()
            self.assertEqual(f.document_id, 'doc123')
            self.assertIn('docs.google.com', f.document_link)
            self.project.update_progress.assert_called_once_with(save_instance=True)
        finally:
            patcher1.stop(); patcher2.stop()

    def test_str(self):
        """Cover __str__"""
        f = Factor(project=self.project,
                   name='XYZ',
                   start_date=self.project.start_date,
                   end_date=self.project.end_date)
        self.assertEqual(str(f), 'XYZ')


class SignalTests(TestCase):
    def setUp(self):
        self.factor = Factor(project=Project.objects.create(
            name='S', start_date=date.today(), end_date=date.today()+timedelta(days=1)
        ), name='S1', start_date=date.today(), end_date=date.today()+timedelta(days=1))
        self.factor.document_id = 'DID'
        self.project = self.factor.project
        self.project.update_progress = MagicMock()
        self.drive = MagicMock()
        patch('factorManager.signals._drive_service', return_value=self.drive).start()

    def test_trash_factor_drive(self):
        """Cover trash_factor_drive handler"""
        trash_factor_drive(sender=Factor, instance=self.factor)
        self.assertTrue(self.drive.files().update.called)

    def test_trash_factor_drive_exception(self):
        """Cover exception suppression in trash_factor_drive"""
        self.drive.files().update.return_value.execute.side_effect = Exception()
        # Should not raise
        trash_factor_drive(sender=Factor, instance=self.factor)

    def test_update_project_progress_signal(self):
        """Cover post_save and post_delete updating project progress"""
        # Call handler directly
        _update_project_progress(sender=Factor, instance=self.factor)
        self.project.update_progress.assert_called_with(save_instance=True)


class ViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_superuser(cedula='9', email='a@x.com', password='pwd')
        self.client.force_login(self.user)
        self.project = Project.objects.create(
            name='V', start_date=date.today(), end_date=date.today()+timedelta(days=1)
        )
        self.factor = Factor.objects.create(
            project=self.project, name='F1',
            start_date=self.project.start_date, end_date=self.project.end_date,
            ponderation=50
        )
        # Patch Google services to avoid real calls
        patch('factorManager.models._drive_service', return_value=MagicMock()).start()
        patch('factorManager.models._docs_service', return_value=MagicMock()).start()

    def test_list_view(self):
        """Cover FactorListView GET without filters"""
        resp = self.client.get(reverse('factor_list'))
        self.assertEqual(resp.status_code, 200)
        self.assertIn('factors', resp.context)

    def test_list_view_with_filters(self):
        """Cover filtering by project_id, status, q"""
        url = reverse('factor_list') + f'?project_id={self.project.pk}&status=pending&q=F1'
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)

    def test_detail_view(self):
        """Cover FactorDetailView"""
        resp = self.client.get(reverse('factor_detail', args=[self.factor.pk]))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'F1')

    def test_create_view_no_projects(self):
        """Cover redirect when no projects exist"""
        Project.objects.all().delete()
        resp = self.client.get(reverse('factor_create'))
        self.assertRedirects(resp, reverse('project_list'))
        msgs = list(get_messages(resp.wsgi_request))
        self.assertTrue(any('No existen proyectos' in str(m) for m in msgs))

    def test_create_view_get_and_post(self):
        """Cover GET and POST for FactorCreateView"""
        url = reverse('factor_create') + f'?project={self.project.id_project}'
        # GET
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        # POST valid
        data = {
            'project': self.project.pk,
            'name': 'NewF',
            'start_date': self.project.start_date.isoformat(),
            'end_date': self.project.end_date.isoformat(),
            'ponderation': 10
        }
        resp2 = self.client.post(url, data)
        obj = Factor.objects.filter(name='NewF').first()
        self.assertRedirects(resp2, reverse('factor_detail', args=[obj.pk]))

    def test_update_view(self):
        """Cover FactorUpdateView POST"""
        url = reverse('factor_edit', args=[self.factor.pk])
        resp = self.client.post(url, {
            'name': 'F1X',
            'start_date': self.factor.start_date,
            'end_date': self.factor.end_date,
            'ponderation': 20
        })
        self.assertRedirects(resp, reverse('factor_detail', args=[self.factor.pk]))
        self.factor.refresh_from_db()
        self.assertEqual(self.factor.name, 'F1X')

    def test_delete_view(self):
        """Cover FactorDeleteView"""
        self.factor.document_id = 'DEL'
        self.factor.save()
        resp = self.client.post(reverse('factor_delete', args=[self.factor.pk]))
        self.assertRedirects(resp, reverse('project_detail', args=[self.project.pk]))
        self.assertFalse(Factor.objects.filter(pk=self.factor.pk).exists())

    def test_approve_and_reject_views(self):
        """Cover approve_factor and reject_factor"""
        # PermissionDenied when no role
        with self.assertRaises(PermissionDenied):
            self.client.post(reverse('factor_approve', args=[self.factor.pk]))
        # Stub permission to EDITOR
        patcher = patch('factorManager.views.get_factor_permission', return_value=AssignmentRole.EDITOR)
        patcher.start()
        try:
            # Approve with progress <100
            resp = self.client.post(reverse('factor_approve', args=[self.factor.pk]))
            self.assertRedirects(resp, reverse('factor_detail', args=[self.factor.pk]))
            # Now set approved_percentage to 100 and status pending
            self.factor.approved_percentage = 100
            self.factor.status = 'pending'
            self.factor.save()
            # Approve
            resp2 = self.client.post(reverse('factor_approve', args=[self.factor.pk]))
            self.assertRedirects(resp2, reverse('factor_detail', args=[self.factor.pk]))
            # Reject
            resp3 = self.client.post(reverse('factor_reject', args=[self.factor.pk]))
            self.assertRedirects(resp3, reverse('factor_detail', args=[self.factor.pk]))
        finally:
            patcher.stop()


class TemplateTagTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(cedula='5', email='t@x.com', password='pwd')
        self.factor = self.user  # placeholder, will patch permission

    def test_user_can_edit_and_view(self):
        """Cover template tags user_can_edit_factor and user_can_view_factor"""
        # Unauthenticated
        anon = type('U', (), {'is_authenticated': False})()
        self.assertFalse(user_can_edit_factor(anon, None))
        self.assertFalse(user_can_view_factor(anon, None))
        # Stub get_factor_permission and can_edit
        patch1 = patch('factorManager.templatetags.factor_permissions.get_factor_permission', return_value=AssignmentRole.EDITOR)
        patch2 = patch('factorManager.templatetags.factor_permissions.can_edit', return_value=True)
        patch1.start(); patch2.start()
        try:
            self.assertTrue(user_can_edit_factor(self.user, self.factor))
            self.assertTrue(user_can_view_factor(self.user, self.factor))
        finally:
            patch1.stop(); patch2.stop()
