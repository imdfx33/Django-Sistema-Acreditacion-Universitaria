# reports/tests.py

import io
import json
import locale
from datetime import datetime
from django.test import TestCase, Client
from django.urls import reverse, resolve
from django.core.management import call_command, CommandError
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.core.management.base import BaseCommand
from django.http import HttpResponseNotAllowed
from unittest.mock import patch, MagicMock

from googleapiclient.errors import HttpError

import reports.google_utils as google_utils
import reports.views as views_mod
import reports.admin as admin_mod
from reports.models import FinalReport
from reports.admin import FinalReportAdmin
from reports.management.commands.generar_informe import Command as GenerateReportCommand
from projects.models import Project

User = get_user_model()


class AdminTests(TestCase):
    def test_generated_by_display_with_user(self):
        # Covers FinalReportAdmin.generated_by_display when user exists
        user = User.objects.create_user(cedula='123', email='a@a.com', password='pw')
        user.first_name, user.last_name = 'First', 'Last'
        user.save()
        report = FinalReport(pdf_url='', generated_by=user)
        admin = FinalReportAdmin(FinalReport, admin_mod.admin.site)
        self.assertEqual(admin.generated_by_display(report), user.get_full_name())

    def test_generated_by_display_without_user(self):
        # Covers FinalReportAdmin.generated_by_display when no user
        report = FinalReport(pdf_url='', generated_by=None)
        admin = FinalReportAdmin(FinalReport, admin_mod.admin.site)
        self.assertEqual(admin.generated_by_display(report), "Sistema")

    def test_pdf_url_link_with_url(self):
        # Covers FinalReportAdmin.pdf_url_link when pdf_url present
        report = FinalReport(pdf_url='http://example.com/doc.pdf')
        admin = FinalReportAdmin(FinalReport, admin_mod.admin.site)
        html = admin.pdf_url_link(report)
        self.assertIn('Ver PDF', str(html))

    def test_pdf_url_link_without_url(self):
        # Covers FinalReportAdmin.pdf_url_link when pdf_url empty
        report = FinalReport(pdf_url='')
        admin = FinalReportAdmin(FinalReport, admin_mod.admin.site)
        self.assertEqual(admin.pdf_url_link(report), "N/A")


class GoogleUtilsTests(TestCase):
    def test_get_google_service_success(self):
        # Covers get_google_service success path
        with patch('reports.google_utils.service_account.Credentials.from_service_account_file') as from_file, \
             patch('reports.google_utils.build') as build_mock:
            from_file.return_value = 'creds'
            build_mock.return_value = 'service'
            svc = google_utils.get_google_service('drive', 'v3', ['scope'])
            self.assertEqual(svc, 'service')
            from_file.assert_called_with(google_utils.SERVICE_ACCOUNT_FILE, scopes=['scope'])
            build_mock.assert_called_with('drive', 'v3', credentials='creds', cache_discovery=False)

    def test_get_google_service_error(self):
        # Covers get_google_service exception path
        with patch('reports.google_utils.service_account.Credentials.from_service_account_file', side_effect=Exception('fail')):
            svc = google_utils.get_google_service('docs', 'v1', ['scope'])
            self.assertIsNone(svc)

    def test_get_drive_and_docs_service(self):
        # Covers get_drive_service and get_docs_service delegations
        with patch.object(google_utils, 'get_google_service') as get_svc:
            get_svc.side_effect = ['drive_svc', 'docs_svc']
            self.assertEqual(google_utils.get_drive_service(), 'drive_svc')
            self.assertEqual(google_utils.get_docs_service(), 'docs_svc')

    def test_list_files_in_folder_pagination_and_mime(self):
        # Covers list_files_in_folder normal loop
        drive = MagicMock()
        # First page
        drive.files.return_value.list.return_value.execute.side_effect = [
            {'files': [{'id': '1'}], 'nextPageToken': 'tok'},
            {'files': [{'id': '2'}], 'nextPageToken': None},
        ]
        files = google_utils.list_files_in_folder(drive, 'fid', mime_type='type')
        self.assertEqual(files, [{'id': '1'}, {'id': '2'}])

    def test_list_files_in_folder_error(self):
        # Covers exception branch in list_files_in_folder
        drive = MagicMock()
        drive.files.return_value.list.return_value.execute.side_effect = HttpError(resp=None, content=b'err')
        files = google_utils.list_files_in_folder(drive, 'fid')
        self.assertEqual(files, [])

    def test_download_google_doc_content_success(self):
        # Covers download_google_doc_content normal extraction
        docs = MagicMock()
        docs.documents.return_value.get.return_value.execute.return_value = {
            'body': {'content': [
                {'paragraph': {'elements': [{'textRun': {'content': 'Hello'}}]}},
                {'other': {}},
            ]}
        }
        text = google_utils.download_google_doc_content(docs, 'docid')
        self.assertIn('Hello', text)

    def test_download_google_doc_content_http_error_and_generic(self):
        # Covers both HttpError and generic exceptions
        docs = MagicMock()
        # HttpError path
        docs.documents.return_value.get.return_value.execute.side_effect = HttpError(resp=None, content=b'')
        self.assertEqual(google_utils.download_google_doc_content(docs, 'docid'), "")
        # Generic exception path
        docs.documents.return_value.get.return_value.execute.side_effect = Exception('oops')
        self.assertEqual(google_utils.download_google_doc_content(docs, 'docid'), "")

    def test_create_google_doc_without_and_with_parent(self):
        # Covers create_google_doc success paths
        docs = MagicMock()
        docs.documents.return_value.create.return_value.execute.return_value = {'documentId': 'd1'}
        # Without parent
        doc = google_utils.create_google_doc(docs, 'Title')
        self.assertEqual(doc, {'documentId': 'd1'})
        # With parent
        drive = MagicMock()
        drive.files.return_value.get.return_value.execute.return_value = {'parents': ['root']}
        drive.files.return_value.update.return_value.execute.return_value = None
        with patch('reports.google_utils.get_drive_service', return_value=drive):
            doc2 = google_utils.create_google_doc(docs, 'Title2', parent_folder_id='pf')
            self.assertEqual(doc2, {'documentId': 'd1'})

    def test_create_google_doc_error(self):
        # Covers exception in create_google_doc
        docs = MagicMock()
        docs.documents.return_value.create.return_value.execute.side_effect = HttpError(resp=None, content=b'')
        self.assertIsNone(google_utils.create_google_doc(docs, 'T'))

    def test_batch_update_google_doc(self):
        # Covers batch_update_google_doc empty, success, and error
        docs = MagicMock()
        self.assertTrue(google_utils.batch_update_google_doc(docs, 'id', []))
        docs.documents.return_value.batchUpdate.return_value.execute.return_value = None
        self.assertTrue(google_utils.batch_update_google_doc(docs, 'id', [{'r': 1}]))
        docs.documents.return_value.batchUpdate.return_value.execute.side_effect = HttpError(resp=None, content=b'')
        self.assertFalse(google_utils.batch_update_google_doc(docs, 'id', [{'r': 2}]))

    def test_export_doc_as_pdf_success_and_error(self):
        # Covers export_doc_as_pdf normal and exception paths
        drive = MagicMock()
        drive.files.return_value.export_media.return_value = 'req'
        # Dummy downloader stub
        class DummyStatus:
            def progress(self): return 0.5
        class DummyDownloader:
            def __init__(self, fh, req):
                self.fh = fh
                self.req = req
            def next_chunk(self):
                return DummyStatus(), True
        with patch('reports.google_utils.MediaIoBaseDownload', DummyDownloader):
            pdf = google_utils.export_doc_as_pdf(drive, 'd')
            self.assertIsInstance(pdf, bytes)
        # Generic exception
        with patch('reports.google_utils.MediaIoBaseDownload', side_effect=Exception('err')):
            self.assertIsNone(google_utils.export_doc_as_pdf(drive, 'd'))

    def test_upload_file_to_drive_success_and_errors(self):
        # Covers upload_file_to_drive success, HttpError, and generic exception
        drive = MagicMock()
        drive.files.return_value.create.return_value.execute.return_value = {
            'id': 'fid', 'webViewLink': 'link'
        }
        class DummyMedia:
            def __init__(self, fd, mimetype, resumable): pass
        with patch('reports.google_utils.MediaIoBaseUpload', DummyMedia):
            res = google_utils.upload_file_to_drive(drive, 'f', 'm', b'bytes', 'pf')
            self.assertEqual(res['id'], 'fid')
        # HttpError path
        drive.files.return_value.create.return_value.execute.side_effect = HttpError(resp=None, content=b'')
        with patch('reports.google_utils.MediaIoBaseUpload', DummyMedia):
            self.assertIsNone(google_utils.upload_file_to_drive(drive, 'f', 'm', b'bytes', 'pf'))
        # Generic exception in MediaIoBaseUpload
        with patch('reports.google_utils.MediaIoBaseUpload', side_effect=Exception('oops')):
            self.assertIsNone(google_utils.upload_file_to_drive(drive, 'f', 'm', b'bytes', 'pf'))

    def test_set_file_public_readable(self):
        # Covers set_file_public_readable success and error
        drive = MagicMock()
        drive.permissions.return_value.create.return_value.execute.return_value = None
        self.assertTrue(google_utils.set_file_public_readable(drive, 'fid'))
        drive.permissions.return_value.create.return_value.execute.side_effect = HttpError(resp=None, content=b'')
        self.assertFalse(google_utils.set_file_public_readable(drive, 'fid'))


class ModelTests(TestCase):
    def test_str_with_and_without_user(self):
        # Covers FinalReport.__str__
        user = User.objects.create_user(cedula='999', email='u@u.com', password='pw')
        user.first_name, user.last_name = 'A', 'B'
        user.save()
        r1 = FinalReport.objects.create(pdf_url='u', generated_by=user)
        self.assertIn('por A B', str(r1))
        r2 = FinalReport.objects.create(pdf_url='u', generated_by=None)
        self.assertIn('por Sistema', str(r2))


class ViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.url = reverse('reports:generate_final_report')
        # Create a normal user
        self.user = User.objects.create_user(cedula='555', email='test@t.com', password='pw')

    def test_login_required_and_method_not_allowed(self):
        # GET => 405 Method Not Allowed
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 405)
        # Anonymous POST => redirect to login
        resp2 = Client().post(self.url)
        self.assertEqual(resp2.status_code, 302)

    def test_permission_forbidden(self):
        # Logged in non-superuser without elevated rol
        self.client.force_login(self.user)
        resp = self.client.post(self.url)
        self.assertEqual(resp.status_code, 403)

    def test_bad_request_when_projects_in_progress(self):
        # Make user superuser to bypass permission
        self.user.is_superuser = True
        self.user.save()
        Project.objects.create(name='P', start_date=timezone.now().date(), end_date=timezone.now().date())
        self.client.force_login(self.user)
        resp = self.client.post(self.url)
        self.assertEqual(resp.status_code, 400)
        self.assertIn('error', resp.json())

    @patch('reports.views.call_command')
    def test_generate_success(self, mock_call):
        # All projects finalized => success
        self.user.is_superuser = True
        self.user.save()
        Project.objects.create(name='P2', start_date=timezone.now().date(), end_date=timezone.now().date(), progress=100)
        self.client.force_login(self.user)
        resp = self.client.post(self.url)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data.get('status'), 'ok')

    @patch('reports.views.call_command', side_effect=Exception('fail'))
    def test_generate_internal_error(self, mock_call):
        # call_command raises => 500
        self.user.is_superuser = True
        self.user.save()
        Project.objects.create(name='P3', start_date=timezone.now().date(), end_date=timezone.now().date(), progress=100)
        self.client.force_login(self.user)
        resp = self.client.post(self.url)
        self.assertEqual(resp.status_code, 500)
        data = resp.json()
        self.assertEqual(data.get('status'), 'error')

    def test_url_resolution(self):
        # Covers URL routing for generate_final_report
        resolver = resolve('/generate-final-report/')
        self.assertEqual(resolver.view_name, 'reports:generate_final_report')


class HelperTests(TestCase):
    def test_user_and_projects_helpers(self):
        # Covers _user_can_generate_report and _all_projects_are_finalized
        from reports.views import _user_can_generate_report, _all_projects_are_finalized
        # Anonymous user
        anon = type('U', (), {'is_authenticated': False})
        self.assertFalse(_user_can_generate_report(anon))
        # Superuser
        sup = User.objects.create_user(cedula='1', email='x@x.com', password='pw')
        sup.is_superuser = True
        sup.save()
        self.assertTrue(_user_can_generate_report(sup))
        # No projects => all finalized
        Project.objects.all().delete()
        self.assertTrue(_all_projects_are_finalized())
        # One non-finalized project => False
        Project.objects.create(name='NP', start_date=timezone.now().date(), end_date=timezone.now().date())
        self.assertFalse(_all_projects_are_finalized())


class CommandTests(TestCase):
    def test_add_text_request(self):
        # Covers Command._add_text_request styling options
        cmd = GenerateReportCommand()
        # Empty text => no requests
        self.assertEqual(cmd._add_text_request('', heading_level=1), [])
        # With all styles
        reqs = cmd._add_text_request("Hi", heading_level=2, bold=True, italic=True, underline=True, bullet=True)
        # Should have multiple requests: insertText + styles + bullets
        self.assertTrue(any(r.get('insertText') for r in reqs))
        self.assertTrue(any('updateParagraphStyle' in r for r in reqs))
        self.assertTrue(any('updateTextStyle' in r for r in reqs))
        self.assertTrue(any('createParagraphBullets' in r for r in reqs))

    @patch('reports.management.commands.generar_informe.get_drive_service', return_value=None)
    @patch('reports.management.commands.generar_informe.get_docs_service', return_value=None)
    def test_handle_fails_services(self, docs_svc, drive_svc):
        # Covers handle failure when services not initialized
        cmd = GenerateReportCommand()
        with self.assertRaises(CommandError):
            cmd.handle(user_id=None)

    def test_handle_no_projects(self):
        # Covers handle branch when no finalized projects => just warning and return
        cmd = GenerateReportCommand()
        # Stub services to dummy
        with patch('reports.management.commands.generar_informe.get_drive_service', return_value=MagicMock()), \
             patch('reports.management.commands.generar_informe.get_docs_service', return_value=MagicMock()):
            out = io.StringIO()
            cmd.stdout = out
            cmd.style = cmd.style  # ensure style exists
            # Ensure no projects exist
            Project.objects.all().delete()
            # Should return None without raising
            result = cmd.handle(user_id=None)
            self.assertIsNone(result)
            self.assertIn("No hay proyectos finalizados", out.getvalue())

    def test_handle_full_flow(self):
        # Covers main handle full success path
        # Create a finalized project with nested objects
        p = Project.objects.create(
            name='Full', start_date=timezone.now().date(),
            end_date=timezone.now().date(), progress=100
        )
        # Stub google_utils methods to no-ops/returns
        with patch('reports.management.commands.generar_informe.get_drive_service', return_value=MagicMock()), \
             patch('reports.management.commands.generar_informe.get_docs_service', return_value=MagicMock()), \
             patch('reports.management.commands.generar_informe.create_google_doc', return_value={'documentId': 'doc1'}), \
             patch('reports.management.commands.generar_informe.batch_update_google_doc', return_value=True), \
             patch('reports.management.commands.generar_informe.export_doc_as_pdf', return_value=b'pdfbytes'), \
             patch('reports.management.commands.generar_informe.upload_file_to_drive', return_value={'id': 'pdfid', 'webViewLink': 'link'}), \
             patch('reports.management.commands.generar_informe.set_file_public_readable', return_value=True), \
             patch('reports.management.commands.generar_informe.User.objects.get', side_effect=User.DoesNotExist), \
             patch('reports.management.commands.generar_informe.locale.setlocale'), \
             patch('reports.management.commands.generar_informe.locale.getlocale', return_value=('C', 'UTF-8')):
            cmd = GenerateReportCommand()
            out = io.StringIO()
            cmd.stdout = out
            cmd.style = cmd.style
            # Execute command; should complete without error
            cmd.handle(user_id=None)
            self.assertTrue(FinalReport.objects.exists())
            self.assertIn("Informe Final generado", out.getvalue())
