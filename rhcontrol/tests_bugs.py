"""
Testes de regressão dos bugs corrigidos na Etapa 2 da auditoria.
"""
from datetime import date

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from rhcontrol.models import Department, Employee, JobTitle
from rhcontrol.tests_security import make_user


def make_department_and_job():
    department = Department.objects.create(name='Produção')
    job_title = JobTitle.objects.create(name='Operador', department=department, base_salary=2500)
    return department, job_title


class EmployeeStatusFilterTests(TestCase):
    """Os filtros Ativos/Demitidos da lista usam os mesmos valores dos links do template."""

    def setUp(self):
        self.client.force_login(make_user('rh', 'rhcontrol.view_employee'))
        department, job_title = make_department_and_job()
        common = {'birth_date': date(1990, 1, 1), 'department': department, 'job_title': job_title}
        self.active = Employee.objects.create(name='Ativo', cpf='11111111111', **common)
        self.terminated = Employee.objects.create(
            name='Demitido', cpf='22222222222', termination_date=date(2025, 12, 31), **common
        )

    def _listed(self, status):
        response = self.client.get(reverse('rhcontrol:employee_list'), {'status': status})
        return list(response.context['object_list'])

    def test_terminated_filter(self):
        self.assertEqual(self._listed('terminated'), [self.terminated])

    def test_active_filter(self):
        self.assertEqual(self._listed('active'), [self.active])

    def test_template_links_use_filter_values(self):
        response = self.client.get(reverse('rhcontrol:employee_list'))
        self.assertContains(response, '?status=terminated')
        self.assertContains(response, '?status=active')

    def test_sort_by_mobile_phone(self):
        self.active.mobile_phone = '(11) 99999-0000'
        self.active.save()
        self.terminated.mobile_phone = '(11) 90000-0000'
        self.terminated.save()
        response = self.client.get(reverse('rhcontrol:employee_list'), {'sort': 'mobile_phone'})
        self.assertEqual(list(response.context['object_list']), [self.terminated, self.active])
