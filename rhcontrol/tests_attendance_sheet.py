"""
Lista de presença (Form40B) em Excel: o modelo é preenchido editando o XML
do .xlsx, sem passar pelo openpyxl na escrita (que apagaria o logo do modelo
real). Aqui o openpyxl só LÊ o resultado, para conferir o que o Excel verá.
"""
import re
import zipfile
from datetime import date
from io import BytesIO
from types import SimpleNamespace
from xml.dom import minidom

from django.conf import settings
from django.test import TestCase
from django.urls import reverse
from openpyxl import load_workbook

from rhcontrol.attendance_sheet import _fill_participants, build_attendance_sheet
from rhcontrol.models import Department, Employee, JobTitle, Training
from rhcontrol.tests_security import make_user


def valid_cpfs():
    """CPFs válidos gerados na hora, para cadastrar muitos funcionários."""
    def digit(numbers):
        total = sum(int(n) * w for n, w in zip(numbers, range(len(numbers) + 1, 1, -1), strict=True))
        rest = total * 10 % 11
        return '0' if rest == 10 else str(rest)

    for base in range(100000001, 999999999):
        numbers = str(base)
        if len(set(numbers)) == 1:
            continue
        numbers += digit(numbers)
        yield numbers + digit(numbers)


class AttendanceSheetTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.production = Department.objects.create(name='Produção')
        cls.job = JobTitle.objects.create(name='Operador', department=cls.production, base_salary=2500)

    def setUp(self):
        self.cpfs = valid_cpfs()

    def employee(self, name, department=None):
        return Employee.objects.create(
            name=name, cpf=next(self.cpfs), birth_date=date(1990, 1, 1),
            department=department or self.production,
            job_title=self.job, current_salary=2500, hire_date=date(2020, 1, 6),
        )

    def training(self, employees=(), **extra):
        data = {
            'training_name': 'NR-12 Segurança em Máquinas',
            'training_description': 'Operar com segurança',
            'training_total_hours': 8,
            'start_date': date(2026, 11, 10),
        }
        data.update(extra)
        training = Training.objects.create(**data)
        training.scheduled_employees.set(employees)
        return training

    def build(self, training):
        return build_attendance_sheet(training)

    def front(self, content):
        return load_workbook(BytesIO(content))['FRENTE']


class HeaderTests(AttendanceSheetTestCase):
    def test_every_part_is_well_formed_and_declared(self):
        content = self.build(self.training([self.employee('Ana')]))

        with zipfile.ZipFile(BytesIO(content)) as package:
            names = set(package.namelist())
            for name in names:
                if name.endswith(('.xml', '.rels')):
                    minidom.parseString(package.read(name))
            types = package.read('[Content_Types].xml').decode()
        for part in re.findall(r'PartName="/([^"]+)"', types):
            self.assertIn(part, names)

    def test_header_values(self):
        sheet = self.front(self.build(self.training()))

        self.assertTrue(sheet['B5'].value.startswith('Tema/ Treinamento: '))
        self.assertTrue(sheet['B5'].value.endswith('NR-12 Segurança em Máquinas'))
        self.assertTrue(sheet['B15'].value.endswith('Operar com segurança'))
        self.assertTrue(sheet['B37'].value.endswith('10/11/2026'))

    def test_date_range(self):
        sheet = self.front(self.build(self.training(end_date=date(2026, 11, 12))))

        self.assertTrue(sheet['B37'].value.endswith('10/11/2026 a 12/11/2026'))

    def test_without_date_and_description_keeps_labels(self):
        sheet = self.front(self.build(self.training(start_date=None, training_description='')))

        self.assertEqual(sheet['B37'].value.strip(), 'Data Realização:')
        self.assertEqual(sheet['B15'].value.strip(), 'Objetivo do Treinamento:')

    def test_internal_location(self):
        location = self.front(self.build(self.training()))['B17'].value

        self.assertIn('☒ Interno', location)
        self.assertIn('☐ Externo', location)

    def test_external_location(self):
        location = self.front(self.build(self.training(training_location_type='Externo')))['B17'].value

        self.assertIn('☐ Interno', location)
        self.assertIn('☒ Externo', location)

    def test_integration(self):
        self.assertEqual(self.front(self.build(self.training()))['J12'].value, '(   )Integração')
        self.assertEqual(
            self.front(self.build(self.training(is_integration=True)))['J12'].value, '( X )Integração'
        )

    def test_special_characters_are_escaped(self):
        content = self.build(self.training(training_name='Água & Óleo <básico>'))

        self.assertTrue(self.front(content)['B5'].value.endswith('Água & Óleo <básico>'))


class SheetsTests(AttendanceSheetTestCase):
    def test_normal_training_has_only_front(self):
        content = self.build(self.training())
        workbook = load_workbook(BytesIO(content))

        self.assertEqual(workbook.sheetnames, ['FRENTE'])
        self.assertIn('☒ Não', workbook['FRENTE']['B25'].value)
        self.assertIn('☐ Sim', workbook['FRENTE']['B25'].value)
        with zipfile.ZipFile(BytesIO(content)) as package:
            app = package.read('docProps/app.xml').decode()
        self.assertNotIn('VERSO', app)
        self.assertNotIn('Plan3', app)

    def test_on_the_job_keeps_back_sheet(self):
        workbook = load_workbook(BytesIO(self.build(self.training(is_on_the_job=True))))

        self.assertEqual(workbook.sheetnames, ['FRENTE', 'VERSO'])
        self.assertIn('☒ Sim', workbook['FRENTE']['B25'].value)
        self.assertIn('☐ Não', workbook['FRENTE']['B25'].value)


class ParticipantsTests(AttendanceSheetTestCase):
    def test_names_in_alphabetical_order_with_department_and_mark(self):
        maintenance = Department.objects.create(name='Manutenção')
        employees = [self.employee('Carla'), self.employee('Ana', maintenance), self.employee('Bruno')]
        sheet = self.front(self.build(self.training(employees)))

        self.assertEqual([sheet[f'B{r}'].value for r in (41, 42, 43)], ['Ana', 'Bruno', 'Carla'])
        self.assertEqual([sheet[f'F{r}'].value for r in (41, 42, 43)], ['Manutenção', 'Produção', 'Produção'])
        self.assertEqual(sheet['H41'].value.strip(), '|  X')
        self.assertIsNone(sheet['B44'].value)
        self.assertEqual(sheet['H44'].value.strip(), '|')

    def test_employee_without_department(self):
        # O cadastro exige setor; o gerador ainda assim não pode quebrar sem ele.
        with zipfile.ZipFile(settings.ATTENDANCE_TEMPLATE_PATH) as package:
            template = package.read('xl/worksheets/sheet1.xml').decode()
        employee = SimpleNamespace(name='Ana', department_id=None, department=None)

        xml, _ = _fill_participants(template, [employee])

        self.assertIn('Ana', re.search(r'<c r="B41".*?</c>', xml).group(0))
        self.assertNotIn('<v>', re.search(r'<c r="F41".*?</c>', xml).group(0))

    def test_attended_but_not_scheduled_is_not_listed(self):
        training = self.training([self.employee('Ana')])
        training.attended_employees.add(self.employee('Zeca'))

        sheet = self.front(self.build(training))

        self.assertEqual(sheet['B41'].value, 'Ana')
        self.assertIsNone(sheet['B42'].value)

    def test_one_page_keeps_template_size(self):
        sheet = self.front(self.build(self.training([self.employee('Ana')])))

        self.assertEqual(sheet.max_row, 91)
        self.assertEqual(len(sheet.row_breaks.brk), 1)

    def test_sixty_participants_add_a_page(self):
        employees = [self.employee(f'Funcionário {n:02d}') for n in range(60)]
        sheet = self.front(self.build(self.training(employees)))

        self.assertEqual(sheet['B41'].value, 'Funcionário 00')
        self.assertEqual(sheet['B100'].value, 'Funcionário 59')
        self.assertIsNone(sheet['B101'].value)
        self.assertEqual(sheet['A142'].value, 102)
        self.assertEqual(sheet['A92'].value, 52)
        self.assertEqual(sheet.max_row, 142)
        merged = {str(r) for r in sheet.merged_cells.ranges}
        self.assertTrue({'B142:E142', 'F142:G142', 'I142:M142', 'B92:E92'} <= merged)
        self.assertEqual([b.id for b in sheet.row_breaks.brk], [39, 91])
        self.assertIn('$M$142', str(sheet.print_area))
        # Do 100 em diante o Nº encolhe para caber na coluna (senão sai "##").
        self.assertTrue(sheet['A140'].alignment.shrink_to_fit)
        self.assertFalse(sheet['A139'].alignment.shrink_to_fit)
        self.assertEqual(sheet['A140'].alignment.horizontal, 'center')


class ViewTests(AttendanceSheetTestCase):
    def setUp(self):
        super().setUp()
        self.item = self.training([self.employee('Ana')])
        self.url = reverse('rhcontrol:training_attendance_sheet', args=[self.item.pk])

    def test_requires_login(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('rhcontrol:login'), response['Location'])

    def test_requires_permission(self):
        self.client.force_login(make_user('sem_acesso'))

        self.assertEqual(self.client.get(self.url).status_code, 403)

    def test_downloads_xlsx(self):
        self.client.force_login(make_user('rh', 'rhcontrol.view_training'))

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response['Content-Type'],
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        )
        self.assertIn('attachment', response['Content-Disposition'])
        self.assertIn('Lista_presenca_nr-12-seguranca-em-maquinas_10-11-2026.xlsx', response['Content-Disposition'])
        self.assertEqual(self.front(response.content)['B41'].value, 'Ana')

    def test_missing_template_shows_message(self):
        self.client.force_login(make_user('rh', 'rhcontrol.view_training'))

        with self.settings(ATTENDANCE_TEMPLATE_PATH='nao-existe.xlsx'):
            response = self.client.get(self.url)

        self.assertRedirects(
            response, reverse('rhcontrol:training_update', args=[self.item.pk]),
            fetch_redirect_response=False,
        )

    def test_buttons_on_list_and_edit_pages(self):
        self.client.force_login(make_user(
            'rh', 'rhcontrol.view_training', 'rhcontrol.change_training',
        ))

        self.assertContains(self.client.get(reverse('rhcontrol:training_list')), self.url)
        self.assertContains(
            self.client.get(reverse('rhcontrol:training_update', args=[self.item.pk])), self.url
        )
