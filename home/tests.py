# test.py
import sys
import types
from django.test import TestCase, RequestFactory, override_settings
from django.urls import resolve
from django.http import HttpResponse
from unittest.mock import patch

# Ensure include() imports won’t fail
for mod in [
    'projects.urls', 'factorList.urls', 'factorManager.urls',
    'traitList.urls', 'traitManager.urls', 'aspectList.urls',
    'aspectManager.urls', 'assignments.urls', 'strategicAnalysis.urls'
]:
    if mod not in sys.modules:
        m = types.ModuleType(mod)
        m.urlpatterns = []
        sys.modules[mod] = m

# Import app modules
import home.admin as admin_module
import home.apps as apps_module
import home.models as models_module
import home.views as views_module
import home.urls as urls_module


class ModuleImportTests(TestCase):
    def test_import_admin_module(self):
        """Cubre la importación de admin.py"""
        __import__('home.admin')

    def test_import_models_module(self):
        """Cubre la importación de models.py (aunque esté vacío)"""
        __import__('home.models')

    def test_app_config(self):
        """Cubre HomeConfig en apps.py"""
        cfg = apps_module.HomeConfig('home', 'home')
        self.assertEqual(cfg.name, 'home')
        self.assertEqual(cfg.default_auto_field, 'django.db.models.BigAutoField')


class UrlsModuleTests(TestCase):
    def setUp(self):
        self.urlpatterns = urls_module.urlpatterns

    def test_urlpatterns_count(self):
        """Cubre la lista urlpatterns en urls.py"""
        self.assertEqual(len(self.urlpatterns), 12)

    def test_home_url_resolves(self):
        """Cubre resolución de la ruta '' -> homeView"""
        match = resolve('/')
        self.assertEqual(match.func, views_module.homeView)
        self.assertEqual(match.url_name, 'home')

    def test_etapa3_url_resolves(self):
        """Cubre resolución de '/etapa3/' -> etapa_3_view"""
        match = resolve('/etapa3/')
        self.assertEqual(match.func, views_module.etapa_3_view)
        self.assertEqual(match.url_name, 'etapa_3')

    def test_etapa4_url_resolves(self):
        """Cubre resolución de '/etapa4/' -> etapa4_view"""
        match = resolve('/etapa4/')
        self.assertEqual(match.func, views_module.etapa4_view)
        self.assertEqual(match.url_name, 'etapa_4')


class ViewsTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def test_homeView_renders(self):
        """Cubre homeView en views.py"""
        req = self.factory.get('/')
        with patch('home.views.render', return_value=HttpResponse('OK')) as mock_render:
            resp = views_module.homeView(req)
            mock_render.assert_called_once_with(req, 'home/home.html')
            self.assertEqual(resp.content, b'OK')

    def test_etapa3_view_renders(self):
        """Cubre etapa_3_view en views.py"""
        req = self.factory.get('/etapa3/')
        with patch('home.views.render', return_value=HttpResponse('OK3')) as mock_render:
            resp = views_module.etapa_3_view(req)
            mock_render.assert_called_once_with(req, 'home/etapa3.html')
            self.assertEqual(resp.content, b'OK3')

    def test_etapa4_view_renders(self):
        """Cubre etapa4_view en views.py"""
        req = self.factory.get('/etapa4/')
        with patch('home.views.render', return_value=HttpResponse('OK4')) as mock_render:
            resp = views_module.etapa4_view(req)
            mock_render.assert_called_once_with(req, 'home/etapa4.html')
            self.assertEqual(resp.content, b'OK4')
