"""
Testes de regressão das correções de segurança (Etapa 1 da auditoria).
"""
import importlib
from datetime import date

from django.contrib.auth.models import Permission, User
from django.test import TestCase, override_settings
from django.urls import Resolver404, reverse
from django.urls.resolvers import RegexPattern, URLResolver

import rh.urls
from rhcontrol.models import Department, Employee, EmployeeHistory, JobTitle


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
