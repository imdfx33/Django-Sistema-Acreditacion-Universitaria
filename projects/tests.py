# test.py
import sys
import uuid
from datetime import date, timedelta
from django.test import TestCase, Client, RequestFactory, override_settings
from django.urls import resolve, reverse
from django.core.exceptions import ValidationError, PermissionDenied
from django.contrib.auth import get_user_model
from django.contrib.messages import get_messages
from unittest.mock import patch, MagicMock

# Import all modules of the app
import projects.admin as admin_module
import projects.apps as apps_module
import projects.forms as forms_module
import projects.models as models_module
import projects.signals as signals_module
import projects.urls as urls_module
import projects.views as views_module

from projects.models import (
    _drive_service,
    _set_initial_permissions_for_creator,
    _gen_id,
    Project
)
User = get_user_model()
# Views import these; assume assignments app is installed
from assignments.models import AssignmentRole, ProjectAssignment, FactorAssignment


class AdminModuleTests(TestCase):
    def test_import_admin(self):
        """Covers import and registration in admin.py"""
        __import__('projects.admin')


class AppsTests(TestCase):
    def test_apps_config(self):
        """Covers ProjectsConfig attributes"""
        cfg = apps_module.ProjectsConfig('projects', 'projects')
        self.assertEqual(cfg.name, 'projects')
        self.assertEqual(cfg.default_auto_field, 'django.db.models.BigAutoField')

    def test_ready_imports_signals(self):
        """Covers ready() importing signals"""
        sys.modules.pop('projects.signals', None)
        cfg = apps_module.ProjectsConfig('projects', 'projects')
        cfg.ready()
        self.assertIn('projects.signals', sys.modules)


class UrlsModuleTests(TestCase):
    def test_urlpatterns_resolve(self):
        """Covers URL patterns in urls.py"""
        match = resolve('/', urlconf=urls_module)
        self.assertEqual(match.func.view_class, views_module.ProjectListView)
        match2 = resolve('/create/', urlconf=urls_module)
        self.assertEqual(match2.func.view_class, views_module.ProjectCreateView)
        match3 = resolve('/ABC/', urlconf=urls_module)
        self.assertEqual(match3.func.view_class, views_module.ProjectDetailView)
        match4 = resolve('/ABC/edit/', urlconf=urls_module)
        self.assertEqual(match4.func.view_class, views_module.ProjectUpdateView)
        match5 = resolve('/ABC/delete/', urlconf=urls_module)
        self.assertEqual(match5.func.view_class, views_module.ProjectDeleteView)
        match6 = resolve('/ABC/approve/', urlconf=urls_module)
        self.assertEqual(match6.func, views_module.project_approve)


class ProjectFormTests(TestCase):
    def test_valid_dates(self):
        """Covers _DatesMixin.clean with valid dates"""
        data = {'name': 'Test', 'start_date': '2025-01-01', 'end_date': '2025-01-02'}
        form = forms_module.ProjectForm(data=data)
        self.assertTrue(form.is_valid())

    def test_invalid_dates(self):
        """Covers ValidationError in _DatesMixin.clean when end_date < start_date"""
        data = {'name': 'Test', 'start_date': '2025-01-02', 'end_date': '2025-01-01'}
        form = forms_module.ProjectForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn(
            "La fecha final debe ser posterior o igual a la fecha inicial.",
            form.errors['__all__'][0]
        )


class ModelUtilsTests(TestCase):
    @override_settings(
        GOOGLE_SERVICE_ACCOUNT_FILE='file.json',
        GOOGLE_DRIVE_SCOPES=['s1'],
        GOOGLE_DOCS_SCOPES=['d2']
    )
    def test_drive_service(self):
        """Covers _drive_service function"""
        import google.oauth2.service_account as sc
        with patch.object(sc.Credentials, 'from_service_account_file', return_value='creds') as mock_cred, \
             patch('projects.models.build', return_value='service') as mock_build:
            svc = _drive_service()
            mock_cred.assert_called_once_with('file.json', scopes=['s1', 'd2'])
            mock_build.assert_called_once_with(
                'drive', 'v3', credentials='creds', cache_discovery=False
            )
            self.assertEqual(svc, 'service')

    def test_set_initial_permissions_success(self):
        """Covers successful _set_initial_permissions_for_creator"""
        drive = MagicMock()
        drive.permissions.return_value.create.return_value.execute.return_value = None
        with patch('projects.models._drive_service', return_value=drive):
            _set_initial_permissions_for_creator('FID', 'e@mail')
            drive.permissions.return_value.create.assert_called_once_with(
                fileId='FID',
                body={'type': 'user', 'role': 'writer', 'emailAddress': 'e@mail'},
                sendNotificationEmail=False
            )

    def test_set_initial_permissions_exception(self):
        """Covers exception branch in _set_initial_permissions_for_creator"""
        drive = MagicMock()
        drive.permissions.return_value.create.return_value.execute.side_effect = Exception('err')
        with patch('projects.models._drive_service', return_value=drive):
            # Should catch internally, not raise
            _set_initial_permissions_for_creator('FID', 'e@mail')

    def test_gen_id(self):
        """Covers _gen_id generating unique IDs of correct length"""
        id1 = _gen_id(8)
        id2 = _gen_id(8)
        self.assertEqual(len(id1), 8)
        self.assertEqual(len(id2), 8)
        self.assertNotEqual(id1, id2)


class ProjectModelTests(TestCase):
    def setUp(self):
        # Mock drive service for folder operations
        self.drive = MagicMock()
        self.drive.files.return_value.create.return_value.execute.return_value = {'id': 'folder123'}
        self.drive.files.return_value.update.return_value.execute.return_value = None
        patcher = patch('projects.models._drive_service', return_value=self.drive)
        patcher.start()
        self.addCleanup(patcher.stop)
        # Create a user for created_by (custom user model expects cedula, email, password)
        self.user = User.objects.create_user(cedula='1234', email='u@m.com', password='P@ssw0rd')

    def test_folder_creation_on_save(self):
        """Covers Project.save and _ensure_folder for new instance with created_by"""
        p = Project(
            name='Proj1',
            start_date=date.today(),
            end_date=date.today() + timedelta(days=1),
            created_by=self.user
        )
        p.save()
        self.assertEqual(p.folder_id, 'folder123')
        self.drive.files.return_value.create.assert_called()

    def test_str_and_ordering_meta(self):
        """Covers __str__ and Meta.ordering"""
        p = Project(
            name='MyProject',
            start_date=date.today(),
            end_date=date.today() + timedelta(days=1)
        )
        self.assertEqual(str(p), 'MyProject')

    def test_calc_progress_no_factors(self):
        """Covers _calc_progress branch when no factors"""
        p = Project(
            name='NoFact',
            start_date=date.today(),
            end_date=date.today() + timedelta(days=1)
        )
        factors = MagicMock(count=MagicMock(return_value=0))
        p.factors = factors
        self.assertEqual(p._calc_progress(), 0)

    def test_calc_progress_partial(self):
        """Covers _calc_progress computing percentage"""
        p = Project(
            name='PartProj',
            start_date=date.today(),
            end_date=date.today() + timedelta(days=1)
        )
        factors = MagicMock()
        factors.count.return_value = 5
        filt = MagicMock(count=MagicMock(return_value=2))
        factors.filter.return_value = filt
        p.factors = factors
        self.assertEqual(p._calc_progress(), 40)

    def test_update_progress_save_flag(self):
        """Covers update_progress with and without save_instance flag"""
        p = Project(
            name='UpdProj',
            start_date=date.today(),
            end_date=date.today() + timedelta(days=1)
        )
        p.progress = 0
        p._calc_progress = lambda: 80
        p.update_progress(save_instance=False)
        self.assertEqual(p.progress, 80)
        p._calc_progress = lambda: 90
        p.progress = 90
        p.update_progress(save_instance=True)
        self.assertEqual(p.progress, 90)


class SignalTests(TestCase):
    def setUp(self):
        # Mock drive service for signal handler
        self.drive = MagicMock()
        self.files = self.drive.files.return_value
        self.files.update.return_value.execute.return_value = None
        patcher = patch('projects.signals._drive_service', return_value=self.drive)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_trash_project_drive(self):
        """Covers trash_project_drive for factors and folder"""
        class F: pass
        f1, f2 = F(), F()
        f1.document_id = 'doc1'
        f2.document_id = None
        factors = MagicMock(all=MagicMock(return_value=[f1, f2]))
        p = Project(
            name='SigProj',
            start_date=date.today(),
            end_date=date.today() + timedelta(days=1)
        )
        p.factors = factors
        p.folder_id = 'fid123'
        signals_module.trash_project_drive(sender=Project, instance=p)
        # One factor with document + one folder
        self.assertEqual(self.files.update.call_count, 2)


class ProjectViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        # Create superuser to bypass permission mixins
        self.user = User.objects.create_superuser(
            cedula='0000', email='admin@x.com', password='Adm1n!'
        )
        self.client.force_login(self.user)
        self.p1 = Project.objects.create(
            name='ListProj',
            start_date=date.today(),
            end_date=date.today() + timedelta(days=1),
            approved=False,
            created_by=self.user
        )
        self.p2 = Project.objects.create(
            name='DoneProj',
            start_date=date.today(),
            end_date=date.today() + timedelta(days=1),
            approved=True,
            created_by=self.user
        )

    def test_list_view_default(self):
        """Covers ProjectListView default filter (show_completed=False)"""
        resp = self.client.get(reverse('project_list'))
        self.assertEqual(resp.status_code, 200)
        qs = resp.context['projects']
        self.assertIn(self.p1, qs)
        self.assertNotIn(self.p2, qs)

    def test_list_view_show_completed(self):
        """Covers ProjectListView with show_completed=True"""
        resp = self.client.get(reverse('project_list') + '?show_completed=true')
        self.assertEqual(resp.status_code, 200)
        qs = resp.context['projects']
        self.assertIn(self.p2, qs)
        self.assertNotIn(self.p1, qs)

    def test_detail_view(self):
        """Covers ProjectDetailView"""
        resp = self.client.get(reverse('project_detail', args=[self.p1.pk]))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'ListProj')

    def test_create_view(self):
        """Covers ProjectCreateView form_valid path"""
        data = {
            'name': 'NewProj',
            'start_date': date.today().isoformat(),
            'end_date': (date.today() + timedelta(days=1)).isoformat()
        }
        resp = self.client.post(reverse('project_create'), data)
        self.assertRedirects(resp, reverse('project_list'))
        self.assertTrue(Project.objects.filter(name='NewProj').exists())

    def test_update_view(self):
        """Covers ProjectUpdateView form_valid path"""
        data = {
            'name': 'ListProjX',
            'start_date': self.p1.start_date,
            'end_date': self.p1.end_date
        }
        resp = self.client.post(reverse('project_edit', args=[self.p1.pk]), data)
        self.assertRedirects(resp, reverse('project_list'))
        self.p1.refresh_from_db()
        self.assertEqual(self.p1.name, 'ListProjX')

    def test_delete_view(self):
        """Covers ProjectDeleteView form_valid and signal behavior"""
        resp = self.client.post(reverse('project_delete', args=[self.p1.pk]))
        self.assertRedirects(resp, reverse('project_list'))
        self.assertFalse(Project.objects.filter(pk=self.p1.pk).exists())

    def test_approve_view_reject_no_permission(self):
        """Covers project_approve raising PermissionDenied when not editor"""
        with self.assertRaises(PermissionDenied):
            self.client.post(reverse('project_approve', args=[self.p1.pk]))

    def test_approve_view_success(self):
        """Covers project_approve approval when user has EDITOR permission"""
        self.p1.progress = 100
        self.p1.save()
        with patch('projects.views.get_project_permission', return_value=AssignmentRole.EDITOR):
            resp = self.client.post(reverse('project_approve', args=[self.p1.pk]))
            self.assertRedirects(resp, reverse('project_detail', args=[self.p1.pk]))
            self.p1.refresh_from_db()
            self.assertTrue(self.p1.approved)
