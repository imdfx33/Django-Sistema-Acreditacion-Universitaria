# aspectList/tests.py

from django.test import TestCase, Client, RequestFactory
from django.urls import reverse
from django.contrib.auth import get_user_model
from datetime import date, timedelta
from unittest.mock import patch

# Import modules to hit admin.py, apps.py, models.py, urls.py
import aspectList.admin    # covers admin.py
import aspectList.apps     # covers apps.py
import aspectList.models   # covers models.py
import aspectList.urls     # covers urls.py

from projects.models      import Project
from factorManager.models import Factor
from traitManager.models  import Trait
from aspectManager.models import Aspect

from assignments.models import AssignmentRole, ProjectAssignment, FactorAssignment
import aspectList.views as views_mod
import core.permissions as perm_mod

User = get_user_model()


class AdminAppsModelsUrlsImportTests(TestCase):
    def test_imports(self):
        """Asegura que los módulos de configuración de la app se importan sin errores."""
        import aspectList.admin, aspectList.apps, aspectList.models, aspectList.urls
        self.assertTrue(True)


class AspectListViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        # Superusuario para cubrir la rama superuser
        self.user = User.objects.create_superuser(
            cedula='00001', email='admin@example.com', password='Aa1!aaaa'
        )
        self.client.force_login(self.user)

        # Creamos datos: proyecto, factor, trait y dos aspectos (uno aprobado y otro no)
        self.project = Project.objects.create(
            name='Proyecto1',
            start_date=date.today(),
            end_date=date.today() + timedelta(days=1)
        )
        self.factor = Factor.objects.create(
            project=self.project,
            name='Factor1',
            start_date=date.today(),
            end_date=date.today() + timedelta(days=1),
            ponderation=10
        )
        self.trait = Trait.objects.create(
            factor=self.factor,
            name='Trait1',
            description='Descripción Trait1'
        )
        # Aspecto no aprobado
        self.aspect1 = Aspect.objects.create(
            trait=self.trait,
            name='Aspecto1',
            description='Desc1',
            acceptance_criteria='Crit1',
            evaluation_rule='Rule1',
            weight=5,
            approved=False
        )
        # Aspecto aprobado
        self.aspect2 = Aspect.objects.create(
            trait=self.trait,
            name='Aspecto2',
            description='Desc2',
            acceptance_criteria='Crit2',
            evaluation_rule='Rule2',
            weight=10,
            approved=True
        )

    def test_list_view_no_filters(self):
        """Cubre get_queryset y get_context_data sin filtros (superuser)."""
        resp = self.client.get(reverse('aspectList:aspect_list'))
        self.assertEqual(resp.status_code, 200)
        aspects = list(resp.context['aspects'])
        self.assertIn(self.aspect1, aspects)
        self.assertIn(self.aspect2, aspects)
        # Contexto superuser
        self.assertTrue(resp.context['can_create_aspect_anywhere'])
        self.assertIn(self.project, resp.context['available_projects'])
        self.assertIn(self.factor, resp.context['available_factors'])
        self.assertIn(self.trait, resp.context['available_traits'])
        self.assertIn(('', 'Todos'), resp.context['approved_choices'])

    def test_search_filter(self):
        """Cubre filtrado por parámetro 'q'."""
        resp = self.client.get(reverse('aspectList:aspect_list') + '?q=Aspecto1')
        aspects = list(resp.context['aspects'])
        self.assertEqual(aspects, [self.aspect1])

    def test_project_filter(self):
        """Cubre filtrado por 'project_id'."""
        resp = self.client.get(reverse('aspectList:aspect_list') + f'?project_id={self.project.pk}')
        aspects = list(resp.context['aspects'])
        self.assertIn(self.aspect1, aspects)
        self.assertIn(self.aspect2, aspects)

    def test_factor_filter(self):
        """Cubre filtrado por 'factor_id'."""
        resp = self.client.get(reverse('aspectList:aspect_list') + f'?factor_id={self.factor.pk}')
        aspects = list(resp.context['aspects'])
        self.assertIn(self.aspect1, aspects)
        self.assertIn(self.aspect2, aspects)

    def test_trait_filter(self):
        """Cubre filtrado por 'trait_id'."""
        resp = self.client.get(reverse('aspectList:aspect_list') + f'?trait_id={self.trait.pk}')
        aspects = list(resp.context['aspects'])
        self.assertEqual(aspects, [self.aspect1, self.aspect2])

    def test_approved_filter_true(self):
        """Cubre filtrado por 'approved=true'."""
        resp = self.client.get(reverse('aspectList:aspect_list') + '?approved=true')
        aspects = list(resp.context['aspects'])
        self.assertEqual(aspects, [self.aspect2])

    def test_approved_filter_false(self):
        """Cubre filtrado por 'approved=false'."""
        resp = self.client.get(reverse('aspectList:aspect_list') + '?approved=false')
        aspects = list(resp.context['aspects'])
        self.assertEqual(aspects, [self.aspect1])


class AspectListViewMiniAdminTests(TestCase):
    def setUp(self):
        self.client = Client()
        # Usuario "mini-admin" para cubrir rama is_mini_admin_role
        self.user = User.objects.create_user(
            cedula='00002', email='mini@example.com', password='Bb2@bbbb'
        )
        self.user.is_mini_admin_role = True
        self.client.force_login(self.user)

        # Datos
        self.project = Project.objects.create(
            name='ProyectoMini',
            start_date=date.today(),
            end_date=date.today() + timedelta(days=2)
        )
        self.factor = Factor.objects.create(
            project=self.project,
            name='FactorMini',
            start_date=date.today(),
            end_date=date.today() + timedelta(days=2),
            ponderation=20
        )
        self.trait = Trait.objects.create(
            factor=self.factor,
            name='TraitMini',
            description='DescMini'
        )
        self.aspect = Aspect.objects.create(
            trait=self.trait,
            name='AspectoMini',
            description='DescAMini',
            acceptance_criteria='CritMini',
            evaluation_rule='RuleMini',
            weight=15,
            approved=False
        )
        # Asignación de proyecto para mini-admin
        ProjectAssignment.objects.create(
            user=self.user,
            project=self.project,
            role=AssignmentRole.EDITOR
        )

    def test_context_mini_admin(self):
        """Cubre get_context_data para usuario mini-admin."""
        resp = self.client.get(reverse('aspectList:aspect_list'))
        self.assertTrue(resp.context['can_create_aspect_anywhere'])
        self.assertIn(self.project, resp.context['available_projects'])
        self.assertIn(self.factor, resp.context['available_factors'])
        self.assertIn(self.trait, resp.context['available_traits'])


class AspectListViewNormalUserTests(TestCase):
    def setUp(self):
        self.client = Client()
        # Usuario normal sin permisos elevados
        self.user = User.objects.create_user(
            cedula='00003', email='norm@example.com', password='Cc3#cccc'
        )
        self.client.force_login(self.user)

        # Datos
        self.project = Project.objects.create(
            name='ProyectoNorm',
            start_date=date.today(),
            end_date=date.today() + timedelta(days=3)
        )
        self.factor = Factor.objects.create(
            project=self.project,
            name='FactorNorm',
            start_date=date.today(),
            end_date=date.today() + timedelta(days=3),
            ponderation=30
        )
        self.trait = Trait.objects.create(
            factor=self.factor,
            name='TraitNorm',
            description='DescNorm'
        )
        self.aspect = Aspect.objects.create(
            trait=self.trait,
            name='AspectoNorm',
            description='DescANorm',
            acceptance_criteria='CritNorm',
            evaluation_rule='RuleNorm',
            weight=20,
            approved=True
        )
        # Asignación directa de factor
        FactorAssignment.objects.create(
            user=self.user,
            factor=self.factor,
            role=AssignmentRole.EDITOR
        )

    def test_context_normal_user(self):
        """Cubre get_context_data para usuario normal con FactorAssignment."""
        resp = self.client.get(reverse('aspectList:aspect_list'))
        self.assertFalse(resp.context['can_create_aspect_anywhere'])
        self.assertIn(self.trait, resp.context['available_traits'])
        self.assertIn(self.factor, resp.context['available_factors'])
        self.assertIn(self.project, resp.context['available_projects'])


class AspectDetailViewUnitTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.user = User.objects.create_user(
            cedula='00004', email='user@example.com', password='Dd4$dddd'
        )
        # Creamos datos relacionados
        self.project = Project.objects.create(
            name='ProjD', start_date=date.today(),
            end_date=date.today() + timedelta(days=1)
        )
        self.factor = Factor.objects.create(
            project=self.project,
            name='FactorD',
            start_date=self.project.start_date,
            end_date=self.project.end_date,
            ponderation=40
        )
        self.trait = Trait.objects.create(
            factor=self.factor, name='TraitD', description='DescD'
        )
        self.aspect = Aspect.objects.create(
            trait=self.trait,
            name='AspectoD',
            description='DescAD',
            acceptance_criteria='CritD',
            evaluation_rule='RuleD',
            weight=25,
            approved=False
        )
        self.request = self.factory.get('/')
        self.request.user = self.user

    def test_get_object_for_permission(self):
        """Cubre get_object_for_permission y caching."""
        view = views_mod.AspectDetailView()
        view.request = self.request
        view.kwargs = {'pk': str(self.aspect.pk)}
        # Patchear get_queryset para que devuelva nuestro modelo
        view.get_queryset = lambda: Aspect.objects.all()
        obj1 = view.get_object_for_permission()
        obj2 = view.get_object_for_permission()
        self.assertEqual(obj1, self.aspect)
        self.assertEqual(obj2, self.aspect)

    def test_get_context_data_without_permission(self):
        """Cubre get_context_data cuando can_edit devuelve False."""
        view = views_mod.AspectDetailView()
        view.object = self.aspect
        view.request = self.request
        # Sin current_permission_role ni patch de can_edit
        context = view.get_context_data()
        self.assertEqual(context['aspect'], self.aspect)
        self.assertFalse(context['can_edit_aspect'])
        self.assertFalse(context['can_delete_aspect'])
        self.assertFalse(context['can_toggle_approval'])
        self.assertEqual(context['trait'], self.trait)
        self.assertEqual(context['factor'], self.factor)
        self.assertEqual(context['project'], self.project)

    def test_get_context_data_with_permission(self):
        """Cubre get_context_data cuando can_edit devuelve True."""
        view = views_mod.AspectDetailView()
        view.object = self.aspect
        view.request = self.request
        view.request.current_permission_role = 'ANY'
        # Patchear can_edit para forzar True
        with patch('core.permissions.can_edit', return_value=True):
            context = view.get_context_data()
            self.assertTrue(context['can_edit_aspect'])
            self.assertTrue(context['can_delete_aspect'])
            self.assertTrue(context['can_toggle_approval'])
