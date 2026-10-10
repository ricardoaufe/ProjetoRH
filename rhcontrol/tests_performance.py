"""
Etapa 6 (desempenho e paginação).

- Todas as listas usam o mesmo paginador e o mesmo rodapé, que mantém
  busca, filtros e ordenação ao trocar de página.
- O número de consultas de uma lista não cresce com o número de linhas
  (sem consultas N+1).
"""
from datetime import date, timedelta
from unittest import mock

from django.contrib.auth.models import Group, User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from rhcontrol.models import (
    CareerPlan,
    Department,
    Employee,
    JobTitle,
    Occurrence,
    Training,
    Vacation,
)
from rhcontrol.views.occurrence import OccurrenceListView


def create_rows(index):
    """Uma linha de cada lista: setor, cargo, funcionário, férias, treinamento etc."""
    today = timezone.localdate()
    department = Department.objects.create(name=f'Setor {index}')
    job = JobTitle.objects.create(name=f'Cargo {index}', department=department, base_salary=2500)
    senior = JobTitle.objects.create(name=f'Cargo Sênior {index}', department=department, base_salary=3500)
    employee = Employee.objects.create(
        name=f'Funcionário {index}', cpf=CPFS[index], birth_date=date(1990, 1, 1),
        department=department, job_title=job, current_salary=2500, hire_date=date(2020, 1, 6),
    )
    CareerPlan.objects.create(
        employee=employee, proposed_job=senior, proposed_salary=3500,
        promotion_date=today + timedelta(days=30),
    )
    Vacation.objects.create(employee=employee, start_date=today, vacation_duration=10)
    Training.objects.create(
        training_name=f'NR-{index}', start_date=today, training_provider='SENAI', training_total_hours=8,
    )
    Occurrence.objects.create(
        employee=employee, title='Afastamento', description='-',
        occurrence_date=today, is_absence=True,
    )
    group = Group.objects.create(name=f'Perfil {index}')
    user = User.objects.create_user(f'usuario{index}', password='senha-forte-123')
    user.groups.add(group)
    return employee


# CPFs válidos (o model valida o dígito verificador).
CPFS = ['67134509206', '52998224725', '11144477735', '39053344705', '12345678909']


class ListPaginationTests(TestCase):
    """Com 2 registros e 1 por página, toda lista mostra o rodapé."""

    @classmethod
    def setUpTestData(cls):
        cls.admin = User.objects.create_superuser('admin', 'admin@empresa.com', 'senha-forte-123')
        cls.employee = create_rows(0)
        create_rows(1)
        # a lista de ocorrências é de um funcionário só: ele precisa de duas
        Occurrence.objects.create(
            employee=cls.employee, title='Advertência', description='-',
            occurrence_date=timezone.localdate() - timedelta(days=5),
        )

    def setUp(self):
        self.client.force_login(self.admin)

    def list_urls(self):
        return {
            'funcionários': reverse('rhcontrol:employee_list'),
            'treinamentos': reverse('rhcontrol:training_list'),
            'férias': reverse('rhcontrol:vacation_list'),
            'plano de carreira': reverse('rhcontrol:career_plan_list'),
            'setores': reverse('rhcontrol:department_list'),
            'usuários': reverse('rhcontrol:user_list'),
            'perfis de acesso': reverse('rhcontrol:role_list'),
            'ocorrências': reverse('rhcontrol:occurrence_list', args=[self.employee.pk]),
        }

    @mock.patch('rhcontrol.pagination.LIST_PAGE_SIZE', 1)
    @mock.patch.object(OccurrenceListView, 'paginate_by', 1)
    def test_every_list_shows_the_standard_footer(self):
        for name, url in self.list_urls().items():
            with self.subTest(lista=name):
                response = self.client.get(url)
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, 'aria-label="Paginação"')
                self.assertContains(response, 'Página 1 de')
                self.assertContains(response, 'Próxima')

    @mock.patch('rhcontrol.pagination.LIST_PAGE_SIZE', 1)
    def test_changing_page_keeps_search_and_sort(self):
        url = reverse('rhcontrol:department_list')
        response = self.client.get(url, {'search': 'Setor', 'page': 2})

        self.assertContains(response, 'Página 2 de 2')
        self.assertContains(response, '?search=Setor&amp;page=1')

    @mock.patch('rhcontrol.pagination.LIST_PAGE_SIZE', 1)
    def test_invalid_page_does_not_break(self):
        url = reverse('rhcontrol:department_list')
        self.assertContains(self.client.get(url, {'page': 'abc'}), 'Página 1 de 2')
        self.assertContains(self.client.get(url, {'page': 999}), 'Página 2 de 2')

    def test_single_page_hides_footer(self):
        response = self.client.get(reverse('rhcontrol:department_list'))
        self.assertNotContains(response, 'aria-label="Paginação"')


class NoNPlusOneTests(TestCase):
    """Uma lista com 5 linhas faz as mesmas consultas que uma com 1 linha."""

    @classmethod
    def setUpTestData(cls):
        cls.admin = User.objects.create_superuser('admin', 'admin@empresa.com', 'senha-forte-123')

    def setUp(self):
        self.client.force_login(self.admin)

    def count_queries(self, url):
        from django.db import connection
        from django.test.utils import CaptureQueriesContext

        with CaptureQueriesContext(connection) as ctx:
            response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        return len(ctx.captured_queries)

    def test_query_count_does_not_grow_with_rows(self):
        urls = [
            reverse('rhcontrol:employee_list'),
            reverse('rhcontrol:career_plan_list'),
            reverse('rhcontrol:user_list'),
            reverse('rhcontrol:employee_list_pdf'),
        ]
        create_rows(0)
        with_one = {url: self.count_queries(url) for url in urls}

        for index in range(1, 5):
            create_rows(index)
        for url in urls:
            with self.subTest(url=url):
                self.assertEqual(self.count_queries(url), with_one[url])

    def test_leave_badge_still_shows(self):
        employee = create_rows(0)
        response = self.client.get(reverse('rhcontrol:employee_list'))
        self.assertContains(response, 'Afastado(a)')
        self.assertTrue(employee.is_on_leave)
