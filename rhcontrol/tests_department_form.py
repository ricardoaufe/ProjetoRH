"""
Cadastro de setor com cargos: descrição do cargo é opcional, salário base é
obrigatório e qualquer erro aparece para o usuário (antes a tela só recarregava).
"""
from django.contrib.messages import get_messages
from django.test import TestCase
from django.urls import reverse

from rhcontrol.models import Department, JobTitle
from rhcontrol.tests_security import make_user


class DepartmentFormTests(TestCase):
    def setUp(self):
        self.client.force_login(make_user('rh', 'rhcontrol.add_department'))
        self.url = reverse('rhcontrol:department_create')

    def _post(self, department_name='BANHO PARADO NOTURNO', job=None):
        data = {
            'name': department_name, 'description': '',
            'job_titles-TOTAL_FORMS': '1' if job else '0', 'job_titles-INITIAL_FORMS': '0',
            'job_titles-MIN_NUM_FORMS': '0', 'job_titles-MAX_NUM_FORMS': '1000',
        }
        for field, value in (job or {}).items():
            data[f'job_titles-0-{field}'] = value
        return self.client.post(self.url, data)

    def _job(self, base_salary='2.500,00'):
        return {'name': 'OPERADOR', 'base_salary': base_salary, 'description': ''}

    def _errors(self, response):
        return [str(m) for m in get_messages(response.wsgi_request) if m.level_tag == 'error']

    def test_job_without_description_is_saved(self):
        response = self._post(job=self._job())
        self.assertRedirects(response, reverse('rhcontrol:department_list'), fetch_redirect_response=False)
        self.assertEqual(JobTitle.objects.get(name='OPERADOR').description, '')

    def test_missing_salary_shows_error_message(self):
        response = self._post(job=self._job(base_salary=''))
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Department.objects.exists())
        errors = self._errors(response)
        self.assertEqual(len(errors), 1)
        self.assertIn('Cargo OPERADOR', errors[0])
        self.assertIn('Salário Base', errors[0])

    def test_job_card_with_error_is_expanded(self):
        response = self._post(job=self._job(base_salary=''))
        self.assertContains(response, 'fa-chevron-down job-arrow')

    def test_missing_department_name_shows_error_message(self):
        response = self._post(department_name='')
        self.assertEqual(response.status_code, 200)
        self.assertIn('Nome do Setor', self._errors(response)[0])
