# assignments/tests.py
import json
from unittest.mock import patch, MagicMock, ANY
from django.test import TestCase, Client, RequestFactory, override_settings
from django.urls import reverse, NoReverseMatch
from django.contrib.auth import get_user_model
from django.contrib.sessions.middleware import SessionMiddleware
from django.contrib.messages import get_messages
from django.contrib import messages as django_messages
from django.db.models import Model
from django.http import JsonResponse, HttpResponseForbidden, HttpResponseBadRequest
from django.conf import settings

# Attempt to import User and Rol from login.models, with fallbacks
try:
    from login.models import User, Rol as LoginRol
except ImportError:
    User = get_user_model() # Fallback to Django's default User
    class MockLoginRol:
        SUPERADMIN = 'superadmin'
        MINIADMIN = 'miniadmin'
        ACADI = 'acadi'
        EDITOR = 'editor'
        LECTOR = 'lector'
        COMENTADOR = 'comentador'
    LoginRol = MockLoginRol

# Models from other apps (mocked)
class MockProject(Model):
    pk = 1
    id_project = 1
    name = "Mocked Project"
    folder_id = "mock_project_folder_id" # For Drive integration

    class _meta:
        app_label = 'projects'
        model_name = 'project'
        pk = MagicMock()
        pk.name = 'id_project'
    
    objects = MagicMock()
    objects.get.return_value = MagicMock(spec=Model, pk=1, id_project=1, name="Fetched Project", folder_id="mock_project_folder_id")
    objects.all.return_value.order_by.return_value = []
    objects.filter.return_value.order_by.return_value = []


    def __str__(self):
        return self.name

class MockFactor(Model):
    pk = 1
    id_factor = 1
    name = "Mocked Factor"
    project = MagicMock(spec=MockProject) # Assign a mock project
    project.pk = MockProject.pk
    project.id_project = MockProject.id_project # Ensure consistency
    document_id = "mock_factor_document_id" # For Drive integration

    class _meta:
        app_label = 'factorManager'
        model_name = 'factor'
        pk = MagicMock()
        pk.name = 'id_factor'

    objects = MagicMock()
    objects.get.return_value = MagicMock(spec=Model, pk=1, id_factor=1, name="Fetched Factor", project=project, document_id="mock_factor_document_id")
    objects.filter.return_value.order_by.return_value = []
    
    def __str__(self):
        return self.name

# Google API Client Errors (mocked)
class MockHttpError(Exception):
    def __init__(self, resp_status, reason_str):
        self.resp = MagicMock()
        self.resp.status = resp_status
        self.reason = reason_str
        super().__init__(f"HTTP error {resp_status}: {reason_str}")

    def _get_reason(self):
        return self.reason

# Models from this app (assignments)
from .models import AssignmentRole, ProjectAssignment, FactorAssignment
from .apps import AssignmentsConfig
# admin.py is empty, so no specific admin tests beyond app structure
from .views import (
    is_super_admin_or_akadi, is_super_admin_akadi_or_mini_admin,
    api_projects_for_assignment, api_projects_for_mini_admin_factor_assignment,
    api_mini_admin_users, api_assignable_users_for_factor,
    api_factors_for_assignment, api_project_assignments_for_project,
    api_factor_assignments_for_factor, assignments_page,
    assign_project_to_mini_admin, assign_factor_to_user,
    _update_drive_permission
)

# Mock the drive service globally for views
mock_drive_service_global_instance = MagicMock()

def mock_get_drive_service_for_views():
    return mock_drive_service_global_instance


@override_settings(
    LOGIN_URL='login:login', # Standard login URL
    ROOT_URLCONF='assignments.urls', # Focus on this app's URLs
    STATICFILES_DIRS=[],
    TEMPLATES=[{
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [], # Add template dirs if needed
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    }],
    SECRET_KEY='test_secret_key_for_assignments',
    AUTH_USER_MODEL='login.User' if 'login.User' in settings.INSTALLED_APPS else 'auth.User'
)
class AssignmentsAppsConfigTests(TestCase):
    """Tests for assignments/apps.py."""
    def test_assignments_config(self):
        """Test AssignmentsConfig attributes."""
        self.assertEqual(AssignmentsConfig.name, 'assignments')
        self.assertEqual(AssignmentsConfig.default_auto_field, 'django.db.models.BigAutoField')

class AssignmentsModelsTests(TestCase):
    """Tests for assignments/models.py."""
    @classmethod
    def setUpTestData(cls):
        # Use actual User model if login.models.User is available, otherwise Django's default
        UserActual = User 
        
        cls.user1 = UserActual.objects.create_user(username='user1_models', password='password', cedula='modeluser1', email='modeluser1@example.com', first_name="Model", last_name="UserOne")
        cls.project1 = MockProject() # Using the mock
        cls.project1.pk = 101 # Ensure pk for DB relations
        cls.project1.id_project = 101
        cls.project1.name = "Project For Model Test"
        # If MockProject needs to be saved for FK, it's tricky.
        # For FK relations with mocks, usually we don't save the mock, just assign its pk.
        
        cls.factor1 = MockFactor()
        cls.factor1.pk = 201
        cls.factor1.id_factor = 201
        cls.factor1.name = "Factor For Model Test"
        cls.factor1.project = cls.project1 # Link mock factor to mock project


    def test_assignment_role_choices(self):
        """Test AssignmentRole choices."""
        self.assertIn(('lector', 'Lector'), AssignmentRole.choices)
        self.assertIn(('editor', 'Editor'), AssignmentRole.choices)

    @patch('projects.models.Project', MockProject) # Patch Project where Factor model might try to import it
    @patch('factorManager.models.Factor', MockFactor) # Patch Factor where models might try to import it
    def test_project_assignment_creation_and_str(self):
        """Test ProjectAssignment model creation and __str__."""
        # To make ProjectAssignment work with mocked Project, we need Project.objects.get to return our mock
        with patch.object(MockProject, 'objects') as mock_project_manager:
            mock_project_manager.get.return_value = self.project1
            
            # Ensure user has get_full_name
            if not hasattr(self.user1, 'get_full_name'):
                self.user1.get_full_name = MagicMock(return_value=f"{self.user1.first_name} {self.user1.last_name}")

            assignment = ProjectAssignment.objects.create(
                project=self.project1, # This will be the PK due to FK field
                user=self.user1,
                role=AssignmentRole.EDITOR
            )
            self.assertEqual(str(assignment), f"{self.user1.get_full_name()} - {self.project1.name} (Editor)")
            # Test unique_together (implicitly, by trying to create a duplicate if DB backend supports it)
            with self.assertRaises(Exception): # IntegrityError for real DB, other for mocks
                ProjectAssignment.objects.create(project=self.project1, user=self.user1, role=AssignmentRole.LECTOR)

    @patch('projects.models.Project', MockProject)
    @patch('factorManager.models.Factor', MockFactor)
    def test_factor_assignment_creation_and_str(self):
        """Test FactorAssignment model creation and __str__."""
        with patch.object(MockFactor, 'objects') as mock_factor_manager:
            mock_factor_manager.get.return_value = self.factor1
            
            if not hasattr(self.user1, 'get_full_name'):
                 self.user1.get_full_name = MagicMock(return_value=f"{self.user1.first_name} {self.user1.last_name}")

            assignment = FactorAssignment.objects.create(
                factor=self.factor1, # PK
                user=self.user1,
                role=AssignmentRole.LECTOR
            )
            self.assertEqual(str(assignment), f"{self.user1.get_full_name()} - {self.factor1.name} (Lector)")
            with self.assertRaises(Exception):
                FactorAssignment.objects.create(factor=self.factor1, user=self.user1, role=AssignmentRole.EDITOR)

class AssignmentsUrlsTests(TestCase):
    """Tests for assignments/urls.py."""
    def test_reverse_urls(self):
        """Test that all named URLs in assignments app can be reversed."""
        self.assertTrue(reverse('assignments:assignments_page'))
        self.assertTrue(reverse('assignments:assignments')) # Alias
        self.assertTrue(reverse('assignments:api_projects_for_assignment'))
        self.assertTrue(reverse('assignments:api_projects_for_mini_admin_factor_assignment'))
        self.assertTrue(reverse('assignments:api_mini_admin_users'))
        self.assertTrue(reverse('assignments:api_assignable_users_for_factor'))
        self.assertTrue(reverse('assignments:api_factors_for_assignment', kwargs={'project_id': 'proj1'}))
        self.assertTrue(reverse('assignments:api_project_assignments_for_project', kwargs={'project_id': 'proj1'}))
        self.assertTrue(reverse('assignments:api_factor_assignments_for_factor', kwargs={'factor_id': 'fact1'}))
        self.assertTrue(reverse('assignments:assign_project_to_mini_admin'))
        self.assertTrue(reverse('assignments:assign_factor_to_user'))

@patch('assignments.views.User', User) # Ensure User model is correctly patched
@patch('assignments.views.Rol', LoginRol)
@patch('assignments.views.Project', MockProject)
@patch('assignments.views.Factor', MockFactor)
@patch('assignments.views.ProjectAssignment', ProjectAssignment) # Use real assignment models for DB ops
@patch('assignments.views.FactorAssignment', FactorAssignment)
@patch('assignments.views.AssignmentRole', AssignmentRole)
@patch('assignments.views.get_drive_service', side_effect=mock_get_drive_service_for_views) # Central Drive mock
@patch('assignments.views.messages', django_messages) # Use actual messages for testing
@patch('googleapiclient.errors.HttpError', MockHttpError) # Mock HttpError
class AssignmentsViewsTests(TestCase):
    """Tests for assignments/views.py."""

    @classmethod
    def setUpTestData(cls):
        cls.super_user = User.objects.create_superuser('superassign', 'superassign@example.com', 'password', cedula='S001', rol=LoginRol.SUPERADMIN, has_elevated_permissions=True)
        cls.akadi_user = User.objects.create_user('akadiassign', 'akadiassign@example.com', 'password', cedula='A001', rol=LoginRol.ACADI, has_elevated_permissions=True)
        cls.mini_admin_user = User.objects.create_user('miniassign', 'miniassign@example.com', 'password', cedula='M001', rol=LoginRol.MINIADMIN, is_mini_admin_role=True, has_elevated_permissions=False)
        cls.editor_user = User.objects.create_user('editorassign', 'editorassign@example.com', 'password', cedula='E001', rol=LoginRol.EDITOR)
        cls.lector_user = User.objects.create_user('lectorassign', 'lectorassign@example.com', 'password', cedula='L001', rol=LoginRol.LECTOR)

        # Mock project and factor instances that might be fetched via get_object_or_404
        # We will patch their managers' get methods for more control in specific tests.
        cls.project1 = MockProject()
        cls.project1.pk = cls.project1.id_project = "proj_test_1"
        cls.project1.name = "Project Test One"
        cls.project1.folder_id = "drive_folder_p1"

        cls.factor1_p1 = MockFactor()
        cls.factor1_p1.pk = cls.factor1_p1.id_factor = "fact_test_1"
        cls.factor1_p1.name = "Factor Test One P1"
        cls.factor1_p1.project = cls.project1
        cls.factor1_p1.document_id = "drive_doc_f1"
        
        # Ensure User instances have mocked properties if not on actual model
        for user in [cls.super_user, cls.akadi_user, cls.mini_admin_user, cls.editor_user, cls.lector_user]:
            if not hasattr(user, 'has_elevated_permissions'):
                user.has_elevated_permissions = (user.rol == LoginRol.SUPERADMIN or user.rol == LoginRol.ACADI)
            if not hasattr(user, 'is_mini_admin_role'):
                user.is_mini_admin_role = (user.rol == LoginRol.MINIADMIN)
            if not hasattr(user, 'get_full_name'):
                 user.get_full_name = MagicMock(return_value=f"{user.first_name or user.username} {user.last_name or ''}".strip())


    def setUp(self):
        self.client = Client()
        # Reset global drive mock for each test
        mock_drive_service_global_instance.reset_mock()
        # Default behavior for drive permissions list
        mock_drive_service_global_instance.permissions.return_value.list.return_value.execute.return_value = {'permissions': []}


    # Test Permission Helpers
    def test_permission_helpers(self):
        """Test is_super_admin_or_akadi and is_super_admin_akadi_or_mini_admin."""
        self.assertTrue(is_super_admin_or_akadi(self.super_user))
        self.assertTrue(is_super_admin_or_akadi(self.akadi_user))
        self.assertFalse(is_super_admin_or_akadi(self.mini_admin_user))

        self.assertTrue(is_super_admin_akadi_or_mini_admin(self.super_user))
        self.assertTrue(is_super_admin_akadi_or_mini_admin(self.akadi_user))
        self.assertTrue(is_super_admin_akadi_or_mini_admin(self.mini_admin_user))
        self.assertFalse(is_super_admin_akadi_or_mini_admin(self.editor_user))

    # Test assignments_page
    def test_assignments_page_access(self):
        """Test access to assignments_page for different roles."""
        users_allowed = [self.super_user, self.akadi_user, self.mini_admin_user]
        users_denied = [self.editor_user, self.lector_user]

        for user in users_allowed:
            self.client.force_login(user)
            response = self.client.get(reverse('assignments:assignments_page'))
            self.assertEqual(response.status_code, 200, f"User {user.username} should access.")
            self.assertTemplateUsed(response, 'assignments/assignments.html')
            self.assertEqual(response.context['is_super_admin_or_akadi'], is_super_admin_or_akadi(user))
            self.assertEqual(response.context['is_mini_admin'], user.is_mini_admin_role)


        for user in users_denied:
            self.client.force_login(user)
            response = self.client.get(reverse('assignments:assignments_page'))
            self.assertNotEqual(response.status_code, 200, f"User {user.username} should NOT access.")
            # It should redirect to login due to @user_passes_test

    # Test API Views (GET)
    @patch('assignments.views.Project.objects.all')
    def test_api_projects_for_assignment(self, mock_project_all):
        """Test api_projects_for_assignment view."""
        mock_project_all.return_value.order_by.return_value = [self.project1]
        self.client.force_login(self.super_user)
        response = self.client.get(reverse('assignments:api_projects_for_assignment'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), [{'id': self.project1.id_project, 'name': self.project1.name}])
        
        # Test error case
        mock_project_all.side_effect = Exception("DB Error")
        response_err = self.client.get(reverse('assignments:api_projects_for_assignment'))
        self.assertEqual(response_err.status_code, 500)
        self.assertIn('error', response_err.json())


    @patch('assignments.views.Project.objects')
    @patch('assignments.views.ProjectAssignment.objects')
    def test_api_projects_for_mini_admin_factor_assignment(self, mock_pa_objects, mock_proj_objects):
        """Test api_projects_for_mini_admin_factor_assignment for different roles."""
        # Superuser sees all
        self.client.force_login(self.super_user)
        mock_proj_objects.all.return_value.order_by.return_value = [self.project1]
        response_super = self.client.get(reverse('assignments:api_projects_for_mini_admin_factor_assignment'))
        self.assertEqual(response_super.status_code, 200)
        self.assertEqual(len(response_super.json()), 1)

        # MiniAdmin sees assigned projects (as EDITOR)
        self.client.force_login(self.mini_admin_user)
        mock_pa_objects.filter.return_value.values_list.return_value = [self.project1.id_project]
        mock_proj_objects.filter.return_value.order_by.return_value = [self.project1]
        response_mini = self.client.get(reverse('assignments:api_projects_for_mini_admin_factor_assignment'))
        self.assertEqual(response_mini.status_code, 200)
        self.assertEqual(len(response_mini.json()), 1)
        mock_pa_objects.filter.assert_called_with(user=self.mini_admin_user, role=AssignmentRole.EDITOR)

        # Lector (or other non-privileged) gets 403
        self.client.force_login(self.lector_user)
        response_lector = self.client.get(reverse('assignments:api_projects_for_mini_admin_factor_assignment'))
        self.assertEqual(response_lector.status_code, 403) # Due to user_passes_test

        # Test general exception
        self.client.force_login(self.super_user)
        mock_proj_objects.all.side_effect = Exception("DB Error")
        response_err = self.client.get(reverse('assignments:api_projects_for_mini_admin_factor_assignment'))
        self.assertEqual(response_err.status_code, 500)


    @patch('assignments.views.User.objects.filter')
    def test_api_mini_admin_users(self, mock_user_filter):
        """Test api_mini_admin_users view."""
        mock_user_filter.return_value.order_by.return_value = [self.mini_admin_user]
        self.client.force_login(self.super_user)
        response = self.client.get(reverse('assignments:api_mini_admin_users'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 1)
        mock_user_filter.assert_called_with(rol=LoginRol.MINIADMIN, is_active=True)
        
        mock_user_filter.side_effect = Exception("DB Error")
        response_err = self.client.get(reverse('assignments:api_mini_admin_users'))
        self.assertEqual(response_err.status_code, 500)


    @patch('assignments.views.User.objects.filter')
    def test_api_assignable_users_for_factor(self, mock_user_filter):
        """Test api_assignable_users_for_factor view."""
        mock_user_filter.return_value.exclude.return_value.order_by.return_value = [self.editor_user, self.lector_user]
        self.client.force_login(self.mini_admin_user) # MiniAdmin can access
        response = self.client.get(reverse('assignments:api_assignable_users_for_factor'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 2)
        mock_user_filter.return_value.exclude.assert_called_with(rol__in=[LoginRol.SUPERADMIN, LoginRol.MINIADMIN, LoginRol.ACADI])

        mock_user_filter.side_effect = Exception("DB Error")
        response_err = self.client.get(reverse('assignments:api_assignable_users_for_factor'))
        self.assertEqual(response_err.status_code, 500)


    @patch('assignments.views.Project.objects.get')
    @patch('assignments.views.Factor.objects.filter')
    @patch('assignments.views.ProjectAssignment.objects.filter')
    def test_api_factors_for_assignment(self, mock_pa_filter, mock_factor_filter, mock_project_get):
        """Test api_factors_for_assignment view."""
        mock_project_get.return_value = self.project1
        mock_factor_filter.return_value.order_by.return_value = [self.factor1_p1]
        
        # Superuser
        self.client.force_login(self.super_user)
        response_super = self.client.get(reverse('assignments:api_factors_for_assignment', kwargs={'project_id': self.project1.id_project}))
        self.assertEqual(response_super.status_code, 200)
        self.assertEqual(len(response_super.json()), 1)

        # MiniAdmin with access
        self.client.force_login(self.mini_admin_user)
        mock_pa_filter.return_value.exists.return_value = True # MiniAdmin has access
        response_mini_ok = self.client.get(reverse('assignments:api_factors_for_assignment', kwargs={'project_id': self.project1.id_project}))
        self.assertEqual(response_mini_ok.status_code, 200)
        mock_pa_filter.assert_called_with(user=self.mini_admin_user, project=self.project1, role__in=[AssignmentRole.EDITOR, AssignmentRole.COMENTADOR, AssignmentRole.LECTOR])


        # MiniAdmin without access
        mock_pa_filter.return_value.exists.return_value = False # MiniAdmin no access
        response_mini_denied = self.client.get(reverse('assignments:api_factors_for_assignment', kwargs={'project_id': self.project1.id_project}))
        self.assertEqual(response_mini_denied.status_code, 403)

        # Test general exception
        self.client.force_login(self.super_user)
        mock_factor_filter.side_effect = Exception("DB Error")
        response_err = self.client.get(reverse('assignments:api_factors_for_assignment', kwargs={'project_id': self.project1.id_project}))
        self.assertEqual(response_err.status_code, 500)


    @patch('assignments.views.Project.objects.get')
    @patch('assignments.views.ProjectAssignment.objects.filter')
    def test_api_project_assignments_for_project(self, mock_pa_filter, mock_project_get):
        """Test api_project_assignments_for_project view."""
        mock_project_get.return_value = self.project1
        mock_assignment = MagicMock(spec=ProjectAssignment, user=self.mini_admin_user, role=AssignmentRole.EDITOR)
        mock_pa_filter.return_value.select_related.return_value = [mock_assignment]
        
        self.client.force_login(self.super_user)
        response = self.client.get(reverse('assignments:api_project_assignments_for_project', kwargs={'project_id': self.project1.id_project}))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 1)
        mock_pa_filter.assert_called_with(project=self.project1, user__rol=LoginRol.MINIADMIN)

    @patch('assignments.views.Factor.objects.get')
    @patch('assignments.views.FactorAssignment.objects.filter')
    def test_api_factor_assignments_for_factor(self, mock_fa_filter, mock_factor_get):
        """Test api_factor_assignments_for_factor view."""
        mock_factor_get.return_value = self.factor1_p1
        mock_assignment = MagicMock(spec=FactorAssignment, user=self.editor_user, role=AssignmentRole.EDITOR)
        mock_fa_filter.return_value.exclude.return_value.select_related.return_value = [mock_assignment]

        self.client.force_login(self.mini_admin_user) # MiniAdmin can access
        response = self.client.get(reverse('assignments:api_factor_assignments_for_factor', kwargs={'factor_id': self.factor1_p1.id_factor}))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 1)
        mock_fa_filter.return_value.exclude.assert_called_with(user__rol__in=[LoginRol.SUPERADMIN, LoginRol.MINIADMIN, LoginRol.ACADI])

    # Test POST views
    @patch('assignments.views.Project.objects.get')
    @patch('assignments.views.User.objects.get')
    @patch('assignments.views._update_drive_permission') # Mock the helper
    def test_assign_project_to_mini_admin_success(self, mock_update_drive, mock_user_get, mock_project_get):
        """Test assign_project_to_mini_admin successfully."""
        self.client.force_login(self.super_user)
        mock_project_get.return_value = self.project1
        mock_user_get.return_value = self.mini_admin_user
        mock_drive_service_global_instance.permissions.return_value.list.return_value.execute.return_value = {'permissions': []}


        payload = {
            'project_id': self.project1.id_project,
            'assignments': [{'user_id': self.mini_admin_user.cedula, 'role': AssignmentRole.EDITOR}]
        }
        response = self.client.post(reverse('assignments:assign_project_to_mini_admin'), data=json.dumps(payload), content_type='application/json')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(ProjectAssignment.objects.filter(project=self.project1, user=self.mini_admin_user, role=AssignmentRole.EDITOR).exists())
        if self.project1.folder_id: # Drive permission should be updated if folder_id exists
            mock_update_drive.assert_called_with(ANY, self.project1.folder_id, self.mini_admin_user.email, AssignmentRole.EDITOR, ANY)
        
        # Test removing assignment by sending empty role
        payload_remove = {
            'project_id': self.project1.id_project,
            'assignments': [{'user_id': self.mini_admin_user.cedula, 'role': ''}]
        }
        response_remove = self.client.post(reverse('assignments:assign_project_to_mini_admin'), data=json.dumps(payload_remove), content_type='application/json')
        self.assertEqual(response_remove.status_code, 200)
        self.assertFalse(ProjectAssignment.objects.filter(project=self.project1, user=self.mini_admin_user).exists())
        if self.project1.folder_id:
            mock_update_drive.assert_called_with(ANY, self.project1.folder_id, self.mini_admin_user.email, None, ANY) # Role is None for removal

    def test_assign_project_to_mini_admin_bad_requests(self):
        """Test assign_project_to_mini_admin with bad requests."""
        self.client.force_login(self.super_user)
        
        # Not POST
        response_get = self.client.get(reverse('assignments:assign_project_to_mini_admin'))
        self.assertEqual(response_get.status_code, 403) # Method not allowed

        # Invalid JSON
        response_bad_json = self.client.post(reverse('assignments:assign_project_to_mini_admin'), data='{bad json', content_type='application/json')
        self.assertEqual(response_bad_json.status_code, 400)

        # Missing project_id
        response_no_proj = self.client.post(reverse('assignments:assign_project_to_mini_admin'), data=json.dumps({'assignments': []}), content_type='application/json')
        self.assertEqual(response_no_proj.status_code, 400)
        
    @patch('assignments.views.Project.objects.get')
    @patch('assignments.views.User.objects.get')
    def test_assign_project_to_mini_admin_drive_sync_failure(self, mock_user_get, mock_project_get):
        """Test assign_project_to_mini_admin when Drive sync fails initially."""
        self.client.force_login(self.super_user)
        mock_project_get.return_value = self.project1
        mock_user_get.return_value = self.mini_admin_user
        
        # Simulate HttpError when listing permissions
        mock_drive_service_global_instance.permissions.return_value.list.return_value.execute.side_effect = MockHttpError(401, "Auth error")
        
        payload = {'project_id': self.project1.id_project, 'assignments': [{'user_id': self.mini_admin_user.cedula, 'role': AssignmentRole.EDITOR}]}
        response = self.client.post(reverse('assignments:assign_project_to_mini_admin'), data=json.dumps(payload), content_type='application/json')
        self.assertEqual(response.status_code, 200) # Should still succeed for DB
        messages_sent = list(get_messages(response.wsgi_request))
        self.assertTrue(any("CRÍTICO: No se pudo conectar con Google Drive" in str(m) for m in messages_sent))

    @patch('assignments.views.Factor.objects.get')
    @patch('assignments.views.User.objects.get')
    @patch('assignments.views._update_drive_permission')
    @patch('assignments.views.ProjectAssignment.objects.get') # For MiniAdmin permission check
    def test_assign_factor_to_user_success_mini_admin(self, mock_pa_get, mock_update_drive, mock_user_get, mock_factor_get):
        """Test assign_factor_to_user by a MiniAdmin with project editor role."""
        self.client.force_login(self.mini_admin_user)
        mock_factor_get.return_value = self.factor1_p1
        mock_user_get.return_value = self.editor_user # User to assign
        mock_pa_get.return_value = MagicMock(role=AssignmentRole.EDITOR) # MiniAdmin is editor of project
        mock_drive_service_global_instance.permissions.return_value.list.return_value.execute.return_value = {'permissions': []}

        payload = {
            'factor_id': self.factor1_p1.id_factor,
            'assignments': [{'user_id': self.editor_user.cedula, 'role': AssignmentRole.LECTOR}]
        }
        response = self.client.post(reverse('assignments:assign_factor_to_user'), data=json.dumps(payload), content_type='application/json')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(FactorAssignment.objects.filter(factor=self.factor1_p1, user=self.editor_user, role=AssignmentRole.LECTOR).exists())
        if self.factor1_p1.document_id:
             mock_update_drive.assert_called_with(ANY, self.factor1_p1.document_id, self.editor_user.email, AssignmentRole.LECTOR, ANY)

    @patch('assignments.views.Factor.objects.get')
    @patch('assignments.views.ProjectAssignment.objects.get')
    def test_assign_factor_to_user_mini_admin_no_project_permission(self, mock_pa_get, mock_factor_get):
        """Test assign_factor_to_user by MiniAdmin without project editor role."""
        self.client.force_login(self.mini_admin_user)
        mock_factor_get.return_value = self.factor1_p1
        mock_pa_get.return_value = MagicMock(role=AssignmentRole.LECTOR) # MiniAdmin is only Lector

        payload = {'factor_id': self.factor1_p1.id_factor, 'assignments': []}
        response = self.client.post(reverse('assignments:assign_factor_to_user'), data=json.dumps(payload), content_type='application/json')
        self.assertEqual(response.status_code, 403)
        self.assertIn('No tienes permiso de Editor en el proyecto', response.json()['error'])

    def test_assign_factor_to_user_bad_requests(self):
        """Test assign_factor_to_user with bad requests."""
        self.client.force_login(self.super_user)
        response_get = self.client.get(reverse('assignments:assign_factor_to_user'))
        self.assertEqual(response_get.status_code, 403) # Method not POST

        response_bad_json = self.client.post(reverse('assignments:assign_factor_to_user'), data='{bad', content_type='application/json')
        self.assertEqual(response_bad_json.status_code, 400)

        response_no_id = self.client.post(reverse('assignments:assign_factor_to_user'), data=json.dumps({'assignments':[]}), content_type='application/json')
        self.assertEqual(response_no_id.status_code, 400)

    # Test _update_drive_permission helper
    def test_update_drive_permission_remove_permission(self):
        """Test _update_drive_permission to remove an existing permission."""
        mock_drive = MagicMock()
        mock_drive.permissions.return_value.delete.return_value.execute.return_value = None
        existing_perms = {'user@example.com': {'id': 'perm_id_123', 'role': 'writer', 'emailAddress': 'user@example.com'}}
        
        _update_drive_permission(mock_drive, "file_id_test", "user@example.com", None, existing_perms)
        mock_drive.permissions.return_value.delete.assert_called_once_with(fileId="file_id_test", permissionId="perm_id_123")

    def test_update_drive_permission_update_existing(self):
        """Test _update_drive_permission to update an existing permission."""
        mock_drive = MagicMock()
        mock_drive.permissions.return_value.update.return_value.execute.return_value = None
        existing_perms = {'user@example.com': {'id': 'perm_id_abc', 'role': 'reader', 'emailAddress': 'user@example.com'}}

        _update_drive_permission(mock_drive, "file_id_test2", "user@example.com", AssignmentRole.EDITOR, existing_perms)
        mock_drive.permissions.return_value.update.assert_called_once_with(fileId="file_id_test2", permissionId="perm_id_abc", body={'role': 'writer'})
    
    def test_update_drive_permission_create_new(self):
        """Test _update_drive_permission to create a new permission."""
        mock_drive = MagicMock()
        mock_drive.permissions.return_value.create.return_value.execute.return_value = None
        existing_perms = {} # No existing permission for this user

        _update_drive_permission(mock_drive, "file_id_test3", "newuser@example.com", AssignmentRole.LECTOR, existing_perms)
        mock_drive.permissions.return_value.create.assert_called_once_with(
            fileId="file_id_test3",
            body={'type': 'user', 'role': 'reader', 'emailAddress': 'newuser@example.com'},
            sendNotificationEmail=False
        )
        
    def test_update_drive_permission_no_change_needed(self):
        """Test _update_drive_permission when existing permission matches target."""
        mock_drive = MagicMock()
        existing_perms = {'user@example.com': {'id': 'perm_id_xyz', 'role': 'writer', 'emailAddress': 'user@example.com'}}
        
        _update_drive_permission(mock_drive, "file_id_test4", "user@example.com", AssignmentRole.EDITOR, existing_perms)
        mock_drive.permissions.return_value.update.assert_not_called()
        mock_drive.permissions.return_value.create.assert_not_called()
        mock_drive.permissions.return_value.delete.assert_not_called()

    def test_update_drive_permission_http_errors(self):
        """Test _update_drive_permission handling HttpErrors from Drive API."""
        mock_drive_delete_err = MagicMock()
        mock_drive_delete_err.permissions.return_value.delete.return_value.execute.side_effect = MockHttpError(404, "Not Found")
        existing_perms_del = {'del_user@example.com': {'id': 'del_id', 'role': 'reader', 'emailAddress': 'del_user@example.com'}}
        # Expect HttpError to be caught and logged, not re-raised by _update_drive_permission
        _update_drive_permission(mock_drive_delete_err, "f_del", "del_user@example.com", None, existing_perms_del)
        # (Check logs if logging is part of the test requirements, here we just ensure it doesn't crash)

        mock_drive_update_err = MagicMock()
        mock_drive_update_err.permissions.return_value.update.return_value.execute.side_effect = MockHttpError(500, "Server Error")
        existing_perms_upd = {'upd_user@example.com': {'id': 'upd_id', 'role': 'reader', 'emailAddress': 'upd_user@example.com'}}
        _update_drive_permission(mock_drive_update_err, "f_upd", "upd_user@example.com", AssignmentRole.EDITOR, existing_perms_upd)

        mock_drive_create_err = MagicMock()
        mock_drive_create_err.permissions.return_value.create.return_value.execute.side_effect = MockHttpError(403, "Forbidden")
        _update_drive_permission(mock_drive_create_err, "f_crt", "crt_user@example.com", AssignmentRole.LECTOR, {})

