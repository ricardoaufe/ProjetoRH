"""
Mudança de setor/horário no histórico do funcionário
(ex.: Banho Parado -> Banho Parado Noturno).
"""
from django.test import TestCase
from django.urls import reverse

from rhcontrol.models import Department, EmployeeHistory, JobTitle
from rhcontrol.tests_bugs import make_employee
from rhcontrol.tests_security import make_user


class DepartmentChangeHistoryTests(TestCase):
    def setUp(self):
        self.client.force_login(make_user('rh', 'rhcontrol.change_employee'))
        self.employee = make_employee(current_salary=2500)
        self.night_shift = Department.objects.create(name='Produção Noturno')
        # Cada setor tem seus cargos; o do noturno tem o mesmo nome do diurno.
        self.night_job = JobTitle.objects.create(name='Operador', department=self.night_shift, base_salary=2500)

    def _post(self, department, job_title, reason=''):
        url = reverse('rhcontrol:employee_update', kwargs={'pk': self.employee.pk})
        prefix = self.client.get(url).context['dependent_formset'].prefix
        return self.client.post(url, {
            'name': self.employee.name, 'cpf': self.employee.cpf, 'birth_date': '1988-07-10',
            'department': department.pk, 'job_title': job_title.pk,
            'current_salary': '2.500,00', 'change_reason': reason,
            f'{prefix}-TOTAL_FORMS': '0', f'{prefix}-INITIAL_FORMS': '0',
            f'{prefix}-MIN_NUM_FORMS': '0', f'{prefix}-MAX_NUM_FORMS': '1000',
        })

    def test_department_change_creates_history(self):
        response = self._post(self.night_shift, self.night_job)
        self.assertEqual(response.status_code, 302)
        history = self.employee.history.get()
        self.assertEqual(history.reason, 'Mudança de Setor')
        self.assertEqual(history.old_department, 'Produção')
        self.assertEqual(history.new_department, 'Produção Noturno')
        self.assertIsNone(history.new_job_title)
        self.assertIsNone(history.new_salary)

    def test_shift_change_reason_is_kept(self):
        self._post(self.night_shift, self.night_job, reason='Mudança de Horário')
        self.assertEqual(self.employee.history.get().reason, 'Mudança de Horário')

    def test_same_department_creates_no_history(self):
        self._post(self.employee.department, self.employee.job_title)
        self.assertFalse(self.employee.history.exists())

    def test_history_shows_department_change(self):
        EmployeeHistory.objects.create(
            employee=self.employee, reason='Mudança de Horário',
            old_department='Produção', new_department='Produção Noturno',
        )
        url = reverse('rhcontrol:employee_update', kwargs={'pk': self.employee.pk})
        response = self.client.get(url)
        self.assertContains(response, 'Setor:')
        self.assertContains(response, 'Produção Noturno')

    def test_manual_record_saves_departments(self):
        url = reverse('rhcontrol:history_create', kwargs={'employee_id': self.employee.pk})
        self.client.post(url, {
            'date_changed': '2026-01-05', 'reason': 'Mudança de Horário',
            'old_department': 'Produção', 'new_department': 'Produção Noturno',
        })
        history = self.employee.history.get()
        self.assertEqual(history.old_department, 'Produção')
        self.assertEqual(history.new_department, 'Produção Noturno')
