"""
Exportação da lista de funcionários em Excel (.xlsx).

A planilha deve ter as mesmas colunas e respeitar os mesmos filtros do PDF.
"""
from datetime import date, datetime
from io import BytesIO

from django.contrib.auth.models import Permission, User
from django.test import TestCase
from django.urls import reverse
from openpyxl import load_workbook

from rhcontrol.models import Department, Employee, JobTitle


class EmployeeListXlsxTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_superuser('admin', 'admin@empresa.com', 'senha-forte-123')
        department = Department.objects.create(name='Logística')
        job = JobTitle.objects.create(name='Conferente', department=department, base_salary=2000)
        cls.ana = Employee.objects.create(
            name='Ana', cpf='11111111111', birth_date=date(1990, 1, 1), hire_date=date(2021, 3, 15),
            department=department, job_title=job, is_cipa_member=True,
        )
        cls.bruno = Employee.objects.create(
            name='Bruno', cpf='22222222222', birth_date=date(1990, 1, 1), hire_date=date(2019, 5, 2),
            department=department, job_title=job, termination_date=date(2025, 1, 1),
        )

    def setUp(self):
        self.client.force_login(self.user)

    def _get_rows(self, params=None):
        response = self.client.get(reverse('rhcontrol:employee_list_xlsx'), params or {})
        self.assertEqual(response.status_code, 200)
        sheet = load_workbook(BytesIO(response.content)).active
        return list(sheet.iter_rows(values_only=True))

    def test_download_headers(self):
        response = self.client.get(reverse('rhcontrol:employee_list_xlsx'))
        self.assertEqual(
            response['Content-Type'],
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        )
        self.assertEqual(
            response['Content-Disposition'], 'attachment; filename="lista_de_funcionarios.xlsx"'
        )

    def test_same_columns_as_pdf(self):
        rows = self._get_rows({'status': 'active'})
        self.assertEqual(rows[0], ('Colaborador', 'Data de Admissão', 'Setor', 'Cargo', 'Status'))
        self.assertEqual(
            rows[1], ('Ana (CIPA)', datetime(2021, 3, 15), 'Logística', 'Conferente', 'ATIVO')
        )

    def test_same_filters_as_pdf(self):
        for params in [{'status': 'terminated'}, {'search': 'Bruno'}, {}]:
            with self.subTest(params=params):
                pdf = self.client.get(reverse('rhcontrol:employee_list_pdf'), params)
                expected = [e.name for e in pdf.context['employees']]
                names = [row[0].replace(' (CIPA)', '') for row in self._get_rows(params)[1:]]
                self.assertEqual(names, expected)

    def test_requires_view_employee_permission(self):
        user = User.objects.create_user('sem_permissao', password='senha-forte-123')
        self.client.force_login(user)
        response = self.client.get(reverse('rhcontrol:employee_list_xlsx'))
        self.assertEqual(response.status_code, 403)

        user.user_permissions.add(Permission.objects.get(codename='view_employee'))
        response = self.client.get(reverse('rhcontrol:employee_list_xlsx'))
        self.assertEqual(response.status_code, 200)

    def test_list_page_has_excel_button_keeping_filters(self):
        response = self.client.get(reverse('rhcontrol:employee_list'), {'status': 'active'})
        self.assertContains(response, reverse('rhcontrol:employee_list_xlsx') + '?status=active')
