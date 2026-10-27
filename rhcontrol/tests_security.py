"""
Testes de regressão das correções de segurança (Etapa 1 da auditoria).
"""
import importlib
from datetime import date

from django.contrib.auth.models import Group, Permission, User
from django.core.cache import cache
from django.test import TestCase, override_settings
from django.urls import Resolver404, reverse
from django.urls.resolvers import RegexPattern, URLResolver

import rh.urls
from rhcontrol.models import Department, Employee, EmployeeHistory, JobTitle
from rhcontrol.views.auth import LOGIN_MAX_ATTEMPTS, LOGIN_MAX_ATTEMPTS_PER_IP


class ProjectFilesExposureTests(TestCase):
    """Com DEBUG=1 nenhuma URL pode servir arquivos da raiz do projeto."""

    def tearDown(self):
        importlib.reload(rh.urls)

    @override_settings(DEBUG=True)
    def test_project_files_are_not_routable_in_debug(self):
        resolver = URLResolver(RegexPattern(r'^/'), importlib.reload(rh.urls))
        for path in ['/.env', '/db.sqlite3', '/rh/settings.py', '/manage.py']:
            with self.subTest(path=path), self.assertRaises(Resolver404):
                resolver.resolve(path)


def make_employee():
    department = Department.objects.create(name='Produção')
    job_title = JobTitle.objects.create(name='Operador', department=department, base_salary=2500)
    return Employee.objects.create(
        name='Carlos Silva', cpf='67134509206', birth_date=date(1988, 7, 10),
        department=department, job_title=job_title,
    )


def make_user(username, *perms):
    user = User.objects.create_user(username=username, password='senha-forte-123')
    for perm in perms:
        app_label, codename = perm.split('.')
        user.user_permissions.add(
            Permission.objects.get(content_type__app_label=app_label, codename=codename)
        )
    return user


class HistoryDeleteRequiresPostTests(TestCase):
    """Excluir histórico só por POST: um GET (link, <img>) não pode apagar dados."""

    def setUp(self):
        self.user = make_user('rh', 'rhcontrol.change_employee')
        self.client.force_login(self.user)
        self.history = EmployeeHistory.objects.create(employee=make_employee(), reason='Admissão')
        self.url = reverse('rhcontrol:history_delete', kwargs={'pk': self.history.pk})

    def test_get_does_not_delete(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 405)
        self.assertTrue(EmployeeHistory.objects.filter(pk=self.history.pk).exists())

    def test_post_deletes(self):
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, 302)
        self.assertFalse(EmployeeHistory.objects.filter(pk=self.history.pk).exists())


class RolePermissionWhitelistTests(TestCase):
    """Perfis só recebem permissões da RH_PERMISSION_MATRIX, mesmo com POST adulterado."""

    def setUp(self):
        self.user = make_user('gestor', 'auth.add_group', 'auth.change_group')
        self.client.force_login(self.user)

    def test_create_ignores_permissions_outside_matrix(self):
        self.client.post(reverse('rhcontrol:role_create'), {
            'name': 'Perfil Teste',
            'permissions': ['view_employee', 'delete_session', 'add_permission', 'change_logentry'],
        })
        group = Group.objects.get(name='Perfil Teste')
        self.assertEqual(
            set(group.permissions.values_list('content_type__app_label', 'codename')),
            {('rhcontrol', 'view_employee')},
        )

    def test_update_ignores_permissions_outside_matrix(self):
        group = Group.objects.create(name='Perfil Teste')
        self.client.post(reverse('rhcontrol:role_update', kwargs={'pk': group.pk}), {
            'name': 'Perfil Teste',
            'permissions': ['change_user', 'delete_session'],
        })
        self.assertEqual(
            set(group.permissions.values_list('content_type__app_label', 'codename')),
            {('auth', 'change_user')},
        )

    def test_update_with_nothing_selected_clears_permissions(self):
        group = Group.objects.create(name='Perfil Teste')
        group.permissions.add(Permission.objects.get(codename='view_employee'))
        self.client.post(reverse('rhcontrol:role_update', kwargs={'pk': group.pk}), {'name': 'Perfil Teste'})
        self.assertFalse(group.permissions.exists())


class SelfRoleChangeTests(TestCase):
    """Um usuário não pode trocar o próprio perfil de acesso."""

    def setUp(self):
        self.basic = Group.objects.create(name='Consulta')
        self.admin_group = Group.objects.create(name='RhAdmin')
        self.user = make_user('operador', 'auth.change_user')
        self.user.groups.add(self.basic)
        self.client.force_login(self.user)

    def _post(self, target, role):
        return self.client.post(reverse('rhcontrol:user_update', kwargs={'pk': target.pk}), {
            'first_name': target.first_name, 'last_name': target.last_name,
            'email': target.email, 'username': target.username, 'role': role.pk,
        })

    def test_cannot_promote_self(self):
        self._post(self.user, self.admin_group)
        self.assertEqual(list(self.user.groups.all()), [self.basic])

    def test_can_still_change_other_users_role(self):
        other = User.objects.create_user(username='outro', password='senha-forte-123')
        other.groups.add(self.basic)
        self._post(other, self.admin_group)
        self.assertEqual(list(other.groups.all()), [self.admin_group])


class LoginRateLimitTests(TestCase):
    """Depois de várias senhas erradas o login é bloqueado temporariamente."""

    def setUp(self):
        cache.clear()
        self.user = User.objects.create_user(
            username='ana', email='ana@empresa.com', password='senha-correta-123'
        )
        self.url = reverse('rhcontrol:login_create')

    def tearDown(self):
        cache.clear()

    def _login(self, login, password, ip='10.0.0.1'):
        return self.client.post(self.url, {'email': login, 'password': password}, REMOTE_ADDR=ip)

    def test_locks_account_after_max_failures(self):
        for _ in range(LOGIN_MAX_ATTEMPTS):
            self.assertEqual(self._login('ana', 'errada').status_code, 200)
        # Mesmo com a senha certa, a conta fica bloqueada durante a janela.
        response = self._login('ana', 'senha-correta-123')
        self.assertEqual(response.status_code, 429)
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_lock_counts_username_and_email_case_insensitively(self):
        for _ in range(LOGIN_MAX_ATTEMPTS):
            self._login('ANA', 'errada')
        self.assertEqual(self._login('ana', 'senha-correta-123').status_code, 429)

    def test_success_resets_counter(self):
        for _ in range(LOGIN_MAX_ATTEMPTS - 1):
            self._login('ana', 'errada')
        self.assertEqual(self._login('ana', 'senha-correta-123').status_code, 302)
        self.client.logout()
        self.assertEqual(self._login('ana', 'errada').status_code, 200)

    def test_locks_ip_trying_many_accounts(self):
        for i in range(LOGIN_MAX_ATTEMPTS_PER_IP):
            self._login(f'usuario{i}', 'errada')
        self.assertEqual(self._login('ana', 'senha-correta-123').status_code, 429)
        # Outro IP não é afetado.
        self.assertEqual(self._login('ana', 'senha-correta-123', ip='10.0.0.2').status_code, 302)


class AdminAccessTests(TestCase):
    """O admin usa o login do sistema (com bloqueio) e o endereço vem do .env."""

    def tearDown(self):
        importlib.reload(rh.urls)

    def test_admin_login_redirects_to_system_login(self):
        response = self.client.get('/admin/login/')
        self.assertRedirects(response, reverse('rhcontrol:login'), fetch_redirect_response=False)

    def test_admin_requires_login_through_system_login(self):
        response = self.client.get('/admin/', follow=True)
        self.assertEqual(response.redirect_chain[-1][0], reverse('rhcontrol:login'))

    def test_staff_user_logged_in_by_system_can_use_admin(self):
        user = User.objects.create_superuser('chefe', 'chefe@empresa.com', 'senha-forte-123')
        self.client.force_login(user)
        self.assertEqual(self.client.get('/admin/').status_code, 200)

    @override_settings(ADMIN_URL='painel-x7k2/')
    def test_admin_url_comes_from_settings(self):
        resolver = URLResolver(RegexPattern(r'^/'), importlib.reload(rh.urls))
        resolver.resolve('/painel-x7k2/')
        with self.assertRaises(Resolver404):
            resolver.resolve('/admin/')
