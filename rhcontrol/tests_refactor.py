"""
Testes de caracterização da Etapa 4 (redundâncias).

Antes de unificar código duplicado, estes testes fixam o comportamento atual
das telas e dos PDFs, para garantir que a refatoração não muda nada que o
usuário vê.
"""
from datetime import date, timedelta

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from rhcontrol.models import (
    CareerPlan,
    Department,
    Employee,
    EmployeeHistory,
    JobTitle,
    Occurrence,
    Training,
    Vacation,
)


class PdfEndpointsTests(TestCase):
    """Todos os PDFs continuam sendo gerados, com o nome de arquivo certo."""

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_superuser('admin', 'admin@empresa.com', 'senha-forte-123')
        department = Department.objects.create(name='Produção')
        job = JobTitle.objects.create(name='Operador', department=department, base_salary=2500)
        senior = JobTitle.objects.create(name='Operador Sênior', department=department, base_salary=3500)
        cls.employee = Employee.objects.create(
            name='José da Silva', cpf='67134509206', birth_date=date(1988, 7, 10),
            department=department, job_title=job, current_salary=2500, hire_date=date(2020, 1, 6),
        )
        EmployeeHistory.objects.create(
            employee=cls.employee, date_changed=date(2020, 1, 6), new_job_title='Operador',
            new_salary=2500, reason='Admissão',
        )
        CareerPlan.objects.create(
            employee=cls.employee, proposed_job=senior, proposed_salary=3500,
            promotion_date=timezone.localdate() + timedelta(days=30),
        )
        Vacation.objects.create(
            employee=cls.employee, start_date=timezone.localdate(), vacation_duration=10
        )
        Training.objects.create(
            training_name='NR-12', start_date=timezone.localdate(), training_provider='SENAI', training_total_hours=8,
        )
        Occurrence.objects.create(
            employee=cls.employee, title='Atestado', description='-',
            occurrence_date=timezone.localdate(),
        )

    def setUp(self):
        self.client.force_login(self.user)

    def _assert_pdf(self, url, filename_part):
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200, url)
        self.assertEqual(response['Content-Type'], 'application/pdf')
        self.assertTrue(response.content.startswith(b'%PDF'))
        self.assertIn(filename_part, response['Content-Disposition'])
        self.assertTrue(response['Content-Disposition'].startswith('inline'))
        return response

    def test_employee_document_pdfs(self):
        pk = self.employee.pk
        cases = {
            'employee_registration_pdf': 'ficha_cadastral_',
            'confidenciality_term_pdf': 'termo_de_confidencialidade_',
            'bank_presentation_pdf': 'apresentacao_bancaria_',
            'personal_data_consent_pdf': f'_{pk}_',
            'term_of_commitment_pdf': 'termo_de_compromisso_',
            'term_of_consent_pdf': 'termo_de_consentimento_uso_imagem_',
            'benefits_acquisition_pdf': 'termo_de_aquisicao_beneficios_',
            'internal_regulation_pdf': 'regimento_interno_',
            'responsible_term_pdf': 'termo_de_ciencia_e_responsabilidade_ti_',
            'employee_career_plan_pdf': 'Plano_Carreira_',
        }
        for name, filename_part in cases.items():
            with self.subTest(name=name):
                self._assert_pdf(reverse(f'rhcontrol:{name}', kwargs={'pk': pk}), filename_part)

    def test_list_pdfs(self):
        cases = {
            reverse('rhcontrol:employee_list_pdf'): 'lista_de_funcionarios',
            reverse('rhcontrol:department_and_jobtitles_pdf'): 'setores_e_cargos',
            reverse('rhcontrol:employees_department_pdf'): 'funcionarios_por_setor',
            reverse('rhcontrol:create_vacation_list_pdf'): 'lista_de_ferias',
            reverse('rhcontrol:training_list_pdf'): 'lista_de_treinamentos',
            reverse('rhcontrol:occurrence_list_pdf', kwargs={'employee_id': self.employee.pk}): 'Ocorrencias_',
        }
        for url, filename_part in cases.items():
            with self.subTest(url=url):
                self._assert_pdf(url, filename_part)


class ListAndPdfShareFiltersTests(TestCase):
    """A lista na tela e o PDF gerado a partir dela usam o mesmo filtro."""

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_superuser('admin', 'admin@empresa.com', 'senha-forte-123')
        cls.department = Department.objects.create(name='Logística')
        job = JobTitle.objects.create(name='Conferente', department=cls.department, base_salary=2000)
        cls.ana = Employee.objects.create(
            name='Ana', cpf='11111111111', birth_date=date(1990, 1, 1),
            department=cls.department, job_title=job, mobile_phone='(11) 90000-0001',
        )
        cls.bruno = Employee.objects.create(
            name='Bruno', cpf='22222222222', birth_date=date(1990, 1, 1),
            department=cls.department, job_title=job, termination_date=date(2025, 1, 1),
        )
        today = timezone.localdate()
        cls.past_training = Training.objects.create(
            training_name='Empilhadeira', start_date=today - timedelta(days=10), training_provider='SENAI', training_total_hours=8,
        )
        cls.next_training = Training.objects.create(
            training_name='Primeiros Socorros', start_date=today + timedelta(days=10), training_provider='Cruz Vermelha', training_total_hours=4,
        )

    def setUp(self):
        self.client.force_login(self.user)

    def test_employee_list_search_matches_department_and_phone(self):
        for term in ['Logística', '90000-0001']:
            with self.subTest(term=term):
                response = self.client.get(reverse('rhcontrol:employee_list'), {'search': term, 'status': 'active'})
                self.assertEqual(list(response.context['object_list']), [self.ana])

    def test_employee_pdf_uses_same_filters_as_list(self):
        response = self.client.get(reverse('rhcontrol:employee_list_pdf'), {'search': '90000-0001'})
        self.assertEqual(list(response.context['employees']), [self.ana])
        response = self.client.get(reverse('rhcontrol:employee_list_pdf'), {'status': 'terminated'})
        self.assertEqual(list(response.context['employees']), [self.bruno])

    def test_training_list_status_and_sort(self):
        response = self.client.get(reverse('rhcontrol:training_list'), {'status': 'proximos'})
        self.assertEqual(list(response.context['object_list']), [self.next_training])
        response = self.client.get(reverse('rhcontrol:training_list'), {'sort': 'training_name'})
        self.assertEqual(list(response.context['object_list']), [self.past_training, self.next_training])

    def test_training_pdf_status_filter(self):
        response = self.client.get(reverse('rhcontrol:training_list_pdf'), {'status': 'pendentes'})
        self.assertEqual(list(response.context['trainings']), [self.past_training])
