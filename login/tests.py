# test.py
import os
import tempfile
import mimetypes
from django.test import TestCase, RequestFactory, override_settings
from django.urls import resolve, reverse
from django.http import HttpResponse, Http404
from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core import mail
from django.contrib.messages.storage.fallback import FallbackStorage
from unittest.mock import patch, MagicMock

import login.admin as admin_module
import login.apps as apps_module
import login.backends as backends_module
import login.forms as forms_module
import login.google_service as google_service
import login.models as models_module
import login.urls as urls_module
import login.views as views_module

User = models_module.User
Rol = models_module.Rol


class AdminModuleTests(TestCase):
    def test_import_admin(self):
        # Covers import and registry in admin.py
        __import__('login.admin')


class AppsTests(TestCase):
    def test_app_config(self):
        # Covers AppConfig in apps.py
        cfg = apps_module.LoginConfig('login', 'login')
        self.assertEqual(cfg.name, 'login')
        self.assertEqual(cfg.default_auto_field, 'django.db.models.BigAutoField')


class CedulaBackendTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            cedula='11111111', email='u@gmail.com', password='Pwd123!A',
            first_name='Test', last_name='User'
        )
        self.user.is_active = True
        self.user.save()
        self.backend = backends_module.CedulaBackend()

    def test_authenticate_valid(self):
        # Covers valid authentication
        user = self.backend.authenticate(None, username='11111111', password='Pwd123!A')
        self.assertEqual(user, self.user)

    def test_authenticate_invalid_pass(self):
        # Covers wrong password branch
        self.assertIsNone(self.backend.authenticate(None, username='11111111', password='wrong'))

    def test_authenticate_no_user(self):
        # Covers nonexistent user
        self.assertIsNone(self.backend.authenticate(None, username='00000000', password='Pwd123!A'))

    def test_authenticate_no_cedula(self):
        # Covers no cedula provided
        self.assertIsNone(self.backend.authenticate(None))

    def test_authenticate_kwarg(self):
        # Covers use of cedula kwarg
        user = self.backend.authenticate(None, username=None, password='Pwd123!A', cedula='11111111')
        self.assertEqual(user, self.user)


class FormTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()

    @override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
    def test_register_step1_and_enviar(self):
        # Covers RegisterStep1Form validations and enviar_codigo()
        data = {
            'cedula': '12345678', 'first_name': 'Ana', 'last_name': 'Perez',
            'email': 'ana@gmail.com', 'password1': 'Aa1!aaaa', 'password2': 'Aa1!aaaa'
        }
        form = forms_module.RegisterStep1Form(data)
        self.assertTrue(form.is_valid())
        req = self.factory.post('/')
        req.session = {}
        form.enviar_codigo(req)
        self.assertIn('pending_user', req.session)
        self.assertTrue(req.session.get('codigo_' + data['email']).isdigit())
        self.assertEqual(len(mail.outbox), 1)

    def test_register_step1_invalid(self):
        # Covers invalid RegisterStep1Form paths
        form = forms_module.RegisterStep1Form({
            'cedula': 'abc', 'first_name': '', 'last_name': '',
            'email': 'x@yahoo.com', 'password1': 'weak', 'password2': 'diff'
        })
        self.assertFalse(form.is_valid())
        self.assertIn('cedula', form.errors)
        self.assertIn('email', form.errors)
        self.assertIn('password1', form.errors)
        self.assertIn('password2', form.errors)

    def test_verify_code_form(self):
        # Covers VerifyCodeForm clean_codigo and clean()
        email = 'user@gmail.com'
        session = {'codigo_' + email: '654321'}
        # valid
        form = forms_module.VerifyCodeForm({'codigo': '654321'}, email=email, session=session)
        self.assertTrue(form.is_valid())
        # bad format
        form2 = forms_module.VerifyCodeForm({'codigo': '12a456'}, email=email, session=session)
        self.assertFalse(form2.is_valid())
        # wrong code
        form3 = forms_module.VerifyCodeForm({'codigo': '123456'}, email=email, session=session)
        self.assertFalse(form3.is_valid())

    def test_login_form_branches(self):
        # Covers LoginForm valid and inactive user
        u = User.objects.create_user(
            cedula='22222222', email='a@gmail.com', password='Aa1!aaaa',
            first_name='A', last_name='B'
        )
        u.is_active = True; u.save()
        form = forms_module.LoginForm({'cedula': '22222222', 'password': 'Aa1!aaaa'})
        self.assertTrue(form.is_valid())
        u.is_active = False; u.save()
        form2 = forms_module.LoginForm({'cedula': '22222222', 'password': 'Aa1!aaaa'})
        self.assertFalse(form2.is_valid())

    def test_profile_form_clean(self):
        # Covers ProfileForm clean_first_name and clean_last_name
        user = User(cedula='33333333', email='p@gmail.com', first_name='', last_name='')
        form = forms_module.ProfileForm({'first_name': ' juan ', 'last_name': ' pérez '}, instance=user)
        self.assertTrue(form.is_valid())
        inst = form.save(commit=False)
        self.assertEqual(inst.first_name, 'JUAN')
        self.assertEqual(inst.last_name, 'PÉREZ')
        form2 = forms_module.ProfileForm({'first_name': ' ', 'last_name': ' '}, instance=user)
        self.assertFalse(form2.is_valid())

    def test_avatar_upload_form(self):
        # Covers AvatarUploadForm clean_avatar
        small_png = (
            b'\x89PNG\r\n\x1a\n' + b'a'*100
        )
        good = SimpleUploadedFile('a.png', small_png, content_type='image/png')
        form = forms_module.AvatarUploadForm({}, {'avatar': good})
        self.assertTrue(form.is_valid())
        bad_type = SimpleUploadedFile('b.gif', small_png, content_type='image/gif')
        form2 = forms_module.AvatarUploadForm({}, {'avatar': bad_type})
        self.assertFalse(form2.is_valid())
        big = SimpleUploadedFile('c.png', b'a' * (2*1024*1024+1), content_type='image/png')
        form3 = forms_module.AvatarUploadForm({}, {'avatar': big})
        self.assertFalse(form3.is_valid())


class GoogleServiceTests(TestCase):
    @override_settings(GOOGLE_SERVICE_ACCOUNT_FILE='file.json', GOOGLE_DRIVE_SCOPES=['s1'])
    def test_drive_service(self):
        # Covers _drive_service()
        import google.oauth2.service_account as sc
        with patch.object(sc.Credentials, 'from_service_account_file', return_value='creds') as mock_cred, \
             patch('login.google_service.build', return_value='svc') as mock_build:
            svc = google_service._drive_service()
            self.assertEqual(svc, 'svc')
            mock_cred.assert_called_once_with(settings.GOOGLE_SERVICE_ACCOUNT_FILE, scopes=settings.GOOGLE_DRIVE_SCOPES)
            mock_build.assert_called_once()


class ModelTests(TestCase):
    def test_user_manager_and_save(self):
        # Covers UserManager and User.save() branches
        mgr = User.objects
        u1 = mgr.create_user('44444444', 'ok@gmail.com', 'Aa1!aaaa')
        self.assertFalse(u1.is_active)
        with self.assertRaises(ValueError):
            mgr.create_user('', 'e@gmail.com', 'Aa1!aaaa')
        with self.assertRaises(ValueError):
            mgr.create_user('55555555', 'e@yahoo.com', 'Aa1!aaaa')
        su = mgr.create_superuser('66666666', 'su@gmail.com', 'Aa1!aaaa')
        self.assertTrue(su.is_superuser and su.is_staff and su.is_active and su.rol == Rol.SUPERADMIN)
        with self.assertRaises(ValueError):
            mgr._create_user('77777777', 'f@gmail.com', 'Aa1!aaaa', is_staff=False, is_superuser=True)
        # __str__, properties
        u2 = User(cedula='10101010', email='a@gmail.com', first_name='Ana', last_name='Lopez')
        self.assertEqual(str(u2), 'Ana Lopez (10101010)')
        self.assertEqual(u2.get_full_name, 'Ana Lopez')
        for role, prop in [(Rol.SUPERADMIN, 'is_super_admin_role'),
                           (Rol.MINIADMIN, 'is_mini_admin_role'),
                           (Rol.ACADI, 'is_akadi_role')]:
            setattr(u2, 'rol', role); u2.save()
            self.assertTrue(getattr(u2, prop))
        u2.rol = Rol.LECTOR; u2.save()
        self.assertFalse(u2.has_elevated_permissions)
        u2.is_superuser = True; u2.save()
        self.assertTrue(u2.has_elevated_permissions)


class UrlsTests(TestCase):
    def test_urlpatterns(self):
        # Covers urls.py patterns via resolve()
        match = resolve('/avatar/XYZ/', urlconf=urls_module)
        self.assertEqual(match.func, views_module.avatar_proxy)
        match2 = resolve('/', urlconf=urls_module)
        self.assertEqual(match2.func, views_module.login_view)
        match3 = resolve('/accounts/gestion/toggle/ABC123/', urlconf=urls_module)
        self.assertEqual(match3.func.__wrapped__.__name__, views_module.toggle_active.__name__)


class ViewsUtilityTests(TestCase):
    def test_build_avatar_url(self):
        # Covers _build_avatar_url()
        url = views_module._build_avatar_url('ID')
        self.assertIn('ID', url)

    def test_avatar_proxy(self):
        # Covers avatar_proxy success and 404
        rf = RequestFactory()
        req = rf.get('/avatar/ID/')
        ok = MagicMock(status_code=200, headers={'Content-Type': 'image/png'}, content=b'data')
        with patch('login.views.requests.get', return_value=ok):
            resp = views_module.avatar_proxy(req, 'ID')
            self.assertEqual(resp.status_code, 200)
        nok = MagicMock(status_code=404)
        with patch('login.views.requests.get', return_value=nok):
            with self.assertRaises(Http404):
                views_module.avatar_proxy(req, 'ID')


class RegisterStartViewTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def test_get_register_start(self):
        # GET should render form
        req = self.factory.get('/register/')
        req.session = {}
        with patch('login.views.render', return_value=HttpResponse('OK')) as mock_r:
            resp = views_module.register_start(req)
            mock_r.assert_called_once()
            self.assertEqual(resp.content, b'OK')

    @override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
    def test_post_register_start(self):
        # POST valid path should send code and redirect
        data = {
            'cedula': '12345678', 'first_name': 'A', 'last_name': 'B',
            'email': 'a@gmail.com', 'password1': 'Aa1!aaaa', 'password2': 'Aa1!aaaa'
        }
        req = self.factory.post('/register/', data)
        req.session = {}
        req._messages = FallbackStorage(req)
        with patch('login.views.redirect', return_value=HttpResponse('R')) as mock_red:
            resp = views_module.register_start(req)
            self.assertEqual(resp.content, b'R')
            self.assertIn('pending_user', req.session)
            self.assertEqual(len(mail.outbox), 1)


class RegisterVerifyViewTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def test_redirect_no_pending(self):
        # No pending_user should redirect
        req = self.factory.get('/verify/')
        req.session = {}
        with patch('login.views.redirect', return_value=HttpResponse('R')) as mock_red:
            resp = views_module.register_verify(req)
            mock_red.assert_called_once_with('register_start')
            self.assertEqual(resp.content, b'R')

    def test_get_with_pending(self):
        # GET with pending should render
        req = self.factory.get('/verify/')
        req.session = {'pending_user': {'cedula':'1','email':'e@gmail.com','password':'p','first_name':'F','last_name':'L'}, 'codigo_e@gmail.com':'123456'}
        with patch('login.views.render', return_value=HttpResponse('OK')) as mock_r:
            resp = views_module.register_verify(req)
            mock_r.assert_called_once()
            self.assertEqual(resp.content, b'OK')

    def test_post_valid_verify(self):
        # POST valid code should create user and redirect
        pending = {'cedula':'1','email':'e@gmail.com','password':'Aa1!aaaa','first_name':'F','last_name':'L'}
        req = self.factory.post('/verify/', {'codigo':'654321'})
        req.session = {'pending_user': pending, 'codigo_e@gmail.com':'654321'}
        req._messages = FallbackStorage(req)
        with patch('login.views.redirect', return_value=HttpResponse('L')) as mock_red:
            resp = views_module.register_verify(req)
            self.assertEqual(resp.content, b'L')
            self.assertFalse('pending_user' in req.session)


class AuthViewsTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.user = User.objects.create_user('33333333','u@gmail.com','Aa1!aaaa','F','L')
        self.user.is_active = True; self.user.save()

    def test_login_view_get(self):
        # GET login_view
        req = self.factory.get('/')
        req.session = {}
        with patch('login.views.render', return_value=HttpResponse('G')) as mock_r:
            resp = views_module.login_view(req)
            self.assertEqual(resp.content, b'G')

    def test_login_view_post_valid(self):
        # POST valid login
        data = {'cedula':'33333333','password':'Aa1!aaaa'}
        req = self.factory.post('/', data)
        req.session = {}
        req._messages = FallbackStorage(req)
        with patch('login.views.login') as mock_login, \
             patch('login.views.redirect', return_value=HttpResponse('H')) as mock_red:
            resp = views_module.login_view(req)
            mock_login.assert_called_once()
            self.assertEqual(resp.content, b'H')

    def test_login_view_post_invalid(self):
        # POST invalid login
        req = self.factory.post('/', {'cedula':'wrong','password':'bad'})
        req.session = {}
        with patch('login.views.render', return_value=HttpResponse('I')) as mock_r:
            resp = views_module.login_view(req)
            self.assertEqual(resp.content, b'I')

    def test_logout_view(self):
        # Covers logout_view logic
        req = self.factory.get('/logout/')
        req.user = self.user
        with patch('login.views.logout') as mock_lo, \
             patch('login.views.redirect', return_value=HttpResponse('O')) as mock_red:
            resp = views_module.logout_view.__wrapped__(req)
            mock_lo.assert_called_once_with(req)
            self.assertEqual(resp.content, b'O')


class ProfileAndUpdateTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.user = User.objects.create_user('44444444','p@gmail.com','Aa1!aaaa','F','L')
        self.user.is_active = True; self.user.save()

    def test_profile_view_branches(self):
        # Without and with avatar_drive_id
        req = self.factory.get('/perfil/')
        req.user = self.user; req.session = {}
        with patch('login.views.render', return_value=HttpResponse('P1')) as mock_r:
            resp = views_module.profile_view.__wrapped__(req)
            self.assertEqual(resp.content, b'P1')
        self.user.avatar_drive_id = 'XYZ'; self.user.save()
        req2 = self.factory.get('/perfil/')
        req2.user = self.user; req2.session = {}
        with patch('login.views.render', return_value=HttpResponse('P2')) as mock_r2:
            resp2 = views_module.profile_view.__wrapped__(req2)
            self.assertEqual(resp2.content, b'P2')

    def test_update_profile(self):
        # GET and POST update_profile
        req = self.factory.get('/perfil/editar/')
        req.user = self.user; req.session = {}; req._messages = FallbackStorage(req)
        with patch('login.views.render', return_value=HttpResponse('U1')) as mock_r:
            resp = views_module.update_profile.__wrapped__(req)
            self.assertEqual(resp.content, b'U1')
        data = {'first_name':'New','last_name':'Name'}
        req2 = self.factory.post('/perfil/editar/', data)
        req2.user = self.user; req2.session = {}; req2._messages = FallbackStorage(req2)
        with patch('login.views.redirect', return_value=HttpResponse('U2')) as mock_red:
            resp2 = views_module.update_profile.__wrapped__(req2)
            self.assertEqual(resp2.content, b'U2')


class UploadDeleteAvatarTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.user = User.objects.create_user('55555555','v@gmail.com','Aa1!aaaa','F','L')
        self.user.is_active = True; self.user.save()

    def test_upload_avatar_get(self):
        # GET upload_avatar
        req = self.factory.get('/perfil/avatar/')
        req.user = self.user; req.session = {}
        with patch('login.views.render', return_value=HttpResponse('G')) as mock_r:
            resp = views_module.upload_avatar(req)
            self.assertEqual(resp.content, b'G')

    def test_upload_avatar_post(self):
        # POST valid upload_avatar
        png = b'\x89PNG\r\n\x1a\n' + b'a'*10
        up = SimpleUploadedFile('a.png', png, content_type='image/png')
        req = self.factory.post('/perfil/avatar/', {}, {'avatar': up})
        req.user = self.user; req.session = {}; req._messages = FallbackStorage(req)
        fake_drive = MagicMock()
        fake_files = fake_drive.files.return_value
        fake_files.delete.return_value.execute.return_value = None
        fake_files.create.return_value.execute.return_value = {'id':'NEWID'}
        fake_drive.permissions.return_value.create.return_value.execute.return_value = None
        with patch('login.views._drive_service', return_value=fake_drive):
            with patch('login.views.redirect', return_value=HttpResponse('R')) as mock_red:
                resp = views_module.upload_avatar(req)
                self.assertEqual(resp.content, b'R')
                self.assertEqual(self.user.avatar_drive_id, 'NEWID')

    def test_delete_avatar(self):
        # Covers delete_avatar with and without existing avatar
        req = self.factory.post('/perfil/avatar/delete/')
        req.user = self.user; req.session = {}; req._messages = FallbackStorage(req)
        # no avatar case
        with patch('login.views.redirect', return_value=HttpResponse('D1')):
            resp1 = views_module.delete_avatar.__wrapped__(req)
            self.assertEqual(resp1.content, b'D1')
        # with avatar and exception in delete
        self.user.avatar_drive_id = 'OLD'; self.user.avatar = MagicMock(); self.user.save()
        req2 = self.factory.post('/perfil/avatar/delete/')
        req2.user = self.user; req2.session = {}; req2._messages = FallbackStorage(req2)
        fake_drive = MagicMock()
        fake_drive.files.return_value.delete.return_value.execute.side_effect = Exception()
        with patch('login.views._drive_service', return_value=fake_drive):
            with patch('login.views.redirect', return_value=HttpResponse('D2')):
                resp2 = views_module.delete_avatar.__wrapped__(req2)
                self.assertEqual(resp2.content, b'D2')


class AdminViewsTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.user = User.objects.create_user(
            cedula='66666666', email='mini@gmail.com', password='Aa1!aaaa',
            first_name='Mini', last_name='Admin', rol=Rol.MINIADMIN
        )
        self.user.is_active = True; self.user.save()

    def _add_messages(self, req):
        req.session = {}; req._messages = FallbackStorage(req)

    def test_usuarios_panel(self):
        # GET and POST usuarios_panel
        req = self.factory.get('/usuarios/')
        req.user = self.user; self._add_messages(req)
        with patch('login.views.render', return_value=HttpResponse('VP1')) as mock_r:
            resp = views_module.usuarios_panel.__wrapped__(req)
            self.assertEqual(resp.content, b'VP1')
        # POST toggles active
        other = User.objects.create_user('77777777','o@gmail.com','Aa1!aaaa','O','O')
        req2 = self.factory.post('/usuarios/', {'pk': other.pk})
        req2.user = self.user; self._add_messages(req2)
        with patch('login.views.render', return_value=HttpResponse('VP2')):
            _ = views_module.usuarios_panel.__wrapped__(req2)
            self.assertNotEqual(User.objects.get(pk=other.pk).is_active, other.is_active)

    def test_gestion_cuentas(self):
        # Covers gestion_cuentas with filters
        req = self.factory.get('/accounts/gestion/?estado=activo&rol=acadi')
        req.user = self.user
        with patch('login.views.render', return_value=HttpResponse('G1')):
            resp = views_module.gestion_cuentas.__wrapped__(req)
            self.assertEqual(resp.content, b'G1')
        req2 = self.factory.get('/accounts/gestion/?estado=inactivo&rol=sin_rol')
        req2.user = self.user
        with patch('login.views.render', return_value=HttpResponse('G2')):
            resp2 = views_module.gestion_cuentas.__wrapped__(req2)
            self.assertEqual(resp2.content, b'G2')

    def test_toggle_active(self):
        # Covers toggle_active activate and deactivate
        u = User.objects.create_user('88888888','t@gmail.com','Aa1!aaaa','T','T')
        u.is_active = False; u.save()
        req = self.factory.post('/toggle/88888888/', {'action':'activate'})
        req.user = self.user; req.session = {}; req.META = {'HTTP_REFERER':'/prev'}
        with patch('login.views.send_mail') as mock_mail, \
             patch('login.views.redirect', return_value=HttpResponse('T1')):
            resp = views_module.toggle_active.__wrapped__(req, '88888888')
            self.assertEqual(resp.content, b'T1')
            mock_mail.assert_called_once()
            self.assertTrue(User.objects.get(cedula='88888888').is_active)
        # deactivate
        req2 = self.factory.post('/toggle/88888888/', {'action':'deactivate'})
        req2.user = self.user; req2.session = {}; req2.META = {'HTTP_REFERER':'/prev'}
        with patch('login.views.send_mail') as mock_mail2, \
             patch('login.views.redirect', return_value=HttpResponse('T2')):
            resp2 = views_module.toggle_active.__wrapped__(req2, '88888888')
            self.assertEqual(resp2.content, b'T2')
            self.assertFalse(User.objects.get(cedula='88888888').is_active)

    def test_change_user_rol(self):
        # Covers change_user_rol invalid, same, different
        rf = self.factory.post('/change/88888888/', {'new_rol':'invalid'})
        req = rf; req.user = self.user; self._add_messages(req)
        resp = views_module.change_user_rol.__wrapped__(req, '66666666')
        self.assertIsNotNone(resp)
        rf2 = self.factory.post('/change/66666666/', {'new_rol': Rol.MINIADMIN})
        req2 = rf2; req2.user = self.user; self._add_messages(req2)
        _ = views_module.change_user_rol.__wrapped__(req2, '66666666')
        rf3 = self.factory.post('/change/66666666/', {'new_rol': Rol.SUPERADMIN})
        req3 = rf3; req3.user = self.user; self._add_messages(req3)
        _ = views_module.change_user_rol.__wrapped__(req3, '66666666')
        self.assertEqual(User.objects.get(cedula='66666666').rol, Rol.SUPERADMIN)
