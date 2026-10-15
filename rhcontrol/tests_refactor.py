"""
Testes de caracterização da Etapa 4 (redundâncias).

Antes de unificar código duplicado, estes testes fixam o comportamento atual
das telas e dos PDFs, para garantir que a refatoração não muda nada que o
usuário vê.
"""
from datetime import date, timedelta
from unittest import mock

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
            'personal_data_consent_pdf': 'termo_de_consentimento_dados_pessoais_',
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
            reverse('rhcontrol:department_and_jobtitles_pdf'): 'filename="setores_e_cargos.pdf"',
            reverse('rhcontrol:employees_department_pdf'): 'funcionarios_por_setor',
            reverse('rhcontrol:create_vacation_list_pdf'): 'lista_de_ferias',
            reverse('rhcontrol:training_list_pdf'): 'lista_de_treinamentos',
            reverse('rhcontrol:occurrence_list_pdf', kwargs={'employee_id': self.employee.pk}): 'Ocorrencias_',
        }
        for url, filename_part in cases.items():
            with self.subTest(url=url):
                self._assert_pdf(url, filename_part)

    def test_pdf_footer_has_company_data(self):
        # O rodapé do base_pdf.html usa company_* dos context processors; os
        # PDFs renderizados sem o request saíam com o rodapé vazio.
        from django.conf import settings
        for url in [
            reverse('rhcontrol:employee_list_pdf'),
            reverse('rhcontrol:training_list_pdf'),
            reverse('rhcontrol:occurrence_list_pdf', kwargs={'employee_id': self.employee.pk}),
        ]:
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(response.context['company_address'], settings.COMPANY_ADDRESS)

    def test_accented_name_in_filename(self):
        response = self._assert_pdf(
            reverse('rhcontrol:employee_registration_pdf', kwargs={'pk': self.employee.pk}), 'ficha_cadastral_'
        )
        # RFC 5987: nomes com acento vão codificados em filename*=utf-8''...
        self.assertIn("Jos%C3%A9_da_Silva", response['Content-Disposition'])


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


class VacationFormTests(TestCase):
    """Datas calculadas só no model e duração validada no cadastro e na edição."""

    def setUp(self):
        self.client.force_login(
            User.objects.create_superuser('admin', 'admin@empresa.com', 'senha-forte-123')
        )
        department = Department.objects.create(name='Produção')
        job = JobTitle.objects.create(name='Operador', department=department, base_salary=2500)
        self.employee = Employee.objects.create(
            name='Ana Souza', cpf='67134509206', birth_date=date(1990, 3, 2),
            department=department, job_title=job, hire_date=date(2024, 1, 1),
        )

    def test_create_skips_holiday_on_return_date(self):
        # Fim em 24/12/2026: 25/12 é Natal (sexta), então o retorno é 28/12 (segunda).
        response = self.client.post(reverse('rhcontrol:vacation_create'), {
            'employee': self.employee.pk, 'start_date': '2026-12-15', 'vacation_duration': 10,
        })
        self.assertRedirects(response, reverse('rhcontrol:vacation_list'))
        vacation = Vacation.objects.get()
        self.assertEqual(vacation.end_date, date(2026, 12, 24))
        self.assertEqual(vacation.return_date, date(2026, 12, 28))

    def test_create_rejects_zero_duration(self):
        response = self.client.post(reverse('rhcontrol:vacation_create'), {
            'employee': self.employee.pk, 'start_date': '2026-12-15', 'vacation_duration': 0,
        })
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Vacation.objects.exists())

    def test_update_rejects_negative_duration(self):
        vacation = Vacation.objects.create(
            employee=self.employee, start_date=date(2026, 12, 15), vacation_duration=10
        )
        response = self.client.post(reverse('rhcontrol:vacation_update', args=[vacation.pk]), {
            'employee': self.employee.pk, 'start_date': '2026-12-15', 'vacation_duration': -5,
        })
        self.assertEqual(response.status_code, 200)
        vacation.refresh_from_db()
        self.assertEqual(vacation.vacation_duration, 10)


class DashboardTests(TestCase):
    def test_card_and_chart_count_only_active(self):
        self.client.force_login(
            User.objects.create_superuser('admin', 'admin@empresa.com', 'senha-forte-123')
        )
        today = timezone.localdate()
        cpfs = iter(['67134509206', '52998224725', '11144477735', '39053344705'])
        department = Department.objects.create(name='Produção')
        job = JobTitle.objects.create(name='Operador', department=department, base_salary=2500)

        def employee(hired_days_ago, terminated=False):
            return Employee.objects.create(
                name=f'Func {hired_days_ago}', cpf=next(cpfs), birth_date=date(1990, 1, 1),
                department=department, job_title=job,
                hire_date=today - timedelta(days=hired_days_ago),
                termination_date=today if terminated else None,
            )

        employee(100)                    # < 1 ano
        employee(800)                    # 1 a 3 anos
        employee(800, terminated=True)   # demitido: fora do card e do gráfico
        employee(365 * 20)               # 15+ anos

        response = self.client.get(reverse('rhcontrol:dashboard'))
        self.assertEqual(response.context['active_employees_count'], 3)
        self.assertEqual(response.context['chart_data'], [1, 1, 0, 0, 0, 1])


class CareerPlanPdfContentTests(TestCase):
    """
    O template do plano de carreira lê as chaves de cada linha (row.salary,
    row.job_title...). Se a view e o template divergirem, o Django imprime
    vazio sem dar erro, então o teste confere o HTML gerado.
    """

    def test_rows_show_salary_insalubrity_and_job(self):
        self.client.force_login(
            User.objects.create_superuser('admin', 'admin@empresa.com', 'senha-forte-123')
        )
        department = Department.objects.create(name='Produção')
        job = JobTitle.objects.create(name='operador', department=department, base_salary=2500)
        senior = JobTitle.objects.create(name='operador sênior', department=department, base_salary=3500)
        employee = Employee.objects.create(
            name='José da Silva', cpf='67134509206', birth_date=date(1988, 7, 10),
            department=department, job_title=job, current_salary=2500, hire_date=date(2020, 1, 6),
        )
        EmployeeHistory.objects.create(
            employee=employee, date_changed=date(2020, 1, 6), new_job_title='operador',
            new_salary=2500, reason='Admissão',
        )
        CareerPlan.objects.create(
            employee=employee, proposed_job=senior, proposed_salary=3500, promotion_date=date(2030, 3, 1),
        )

        with mock.patch('rhcontrol.views.pdf.HTML') as html:
            html.return_value.write_pdf.return_value = b'%PDF'
            self.client.get(reverse('rhcontrol:employee_career_plan_pdf', args=[employee.pk]))
        rendered = html.call_args.kwargs['string']

        self.assertIn('06/jan/2020', rendered)
        self.assertIn('R$ 2.500,00', rendered)
        self.assertIn('R$ 209,00', rendered)      # 20% do salário mínimo de 2020 (R$ 1.045)
        self.assertIn('R$ 2.709,00', rendered)
        self.assertIn('Operador Sênior', rendered)
