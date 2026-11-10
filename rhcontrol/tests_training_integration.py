"""
Integração centralizada na aba Treinamentos: o cadastro de funcionário não
mexe mais nos treinamentos de integração; quem faz o vínculo é o RH, no
próprio treinamento (inclusive para quem foi admitido antes de ele existir).
"""
from datetime import date

from django.test import TestCase
from django.urls import reverse

from rhcontrol.forms import EmployeeForm, TrainingForm
from rhcontrol.models import Department, Employee, JobTitle, Training
from rhcontrol.tests_security import make_user


class IntegrationTrainingTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        department = Department.objects.create(name='Produção')
        job = JobTitle.objects.create(name='Operador', department=department, base_salary=2500)

        def employee(name, cpf, **extra):
            return Employee.objects.create(
                name=name, cpf=cpf, birth_date=date(1990, 1, 1), department=department,
                job_title=job, current_salary=2500, hire_date=date(2020, 1, 6), **extra,
            )

        cls.ana = employee('Ana', '67134509206')
        cls.bruno = employee('Bruno', '52998224725')
        cls.carla = employee('Carla', '11144477735')
        cls.former = employee('Demitido', '39053344705', termination_date=date(2025, 1, 1))

    def setUp(self):
        self.client.force_login(make_user(
            'rh', 'rhcontrol.add_training', 'rhcontrol.change_training', 'rhcontrol.view_training',
        ))

    def _data(self, employees, **extra):
        data = {
            'training_name': 'Integração de Novos Colaboradores',
            'training_total_hours': '4',
            'training_location_type': 'Interno',
            'is_integration': 'on',
            'scheduled_employees': [e.pk for e in employees],
        }
        data.update(extra)
        return data

    def test_create_links_chosen_employees_as_attended(self):
        response = self.client.post(reverse('rhcontrol:training_create'), self._data([self.ana, self.bruno]))

        self.assertEqual(response.status_code, 302)
        training = Training.objects.get()
        self.assertEqual(set(training.scheduled_employees.all()), {self.ana, self.bruno})
        self.assertEqual(set(training.attended_employees.all()), {self.ana, self.bruno})

    def test_update_adds_employee_without_attendance_confirmation(self):
        training = Training.objects.create(
            training_name='Integração', training_total_hours=4, is_integration=True
        )
        training.scheduled_employees.set([self.ana])
        training.attended_employees.set([self.ana])

        response = self.client.post(
            reverse('rhcontrol:training_update', args=[training.pk]),
            self._data([self.ana, self.carla]),
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(set(training.attended_employees.all()), {self.ana, self.carla})

    def test_normal_training_keeps_attendance_confirmation(self):
        training = Training.objects.create(training_name='NR-12', training_total_hours=8)
        training.scheduled_employees.set([self.ana, self.bruno])

        form = TrainingForm(
            data=self._data([self.ana, self.bruno], is_integration='', attended_employees=[self.ana.pk]),
            instance=training,
        )

        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(list(form.cleaned_data['attended_employees']), [self.ana])

    def test_employees_without_integration_excludes_linked_and_terminated(self):
        other = Training.objects.create(training_name='Integração antiga', training_total_hours=4, is_integration=True)
        other.scheduled_employees.set([self.bruno])
        normal = Training.objects.create(training_name='NR-12', training_total_hours=8)
        normal.scheduled_employees.set([self.carla])

        ids = TrainingForm().employees_without_integration

        # Carla só fez um treinamento comum: continua sem integração.
        self.assertEqual(sorted(ids), sorted([self.ana.pk, self.carla.pk]))

    def test_form_page_has_button_and_ids(self):
        response = self.client.get(reverse('rhcontrol:training_create'))

        self.assertContains(response, 'id="btn_without_integration"')
        self.assertContains(response, 'id="employees-without-integration"')
        self.assertContains(response, 'id="div_scheduled_employees"')


class EmployeeFormIntegrationTests(TestCase):
    def test_employee_form_has_no_integration_checkbox(self):
        self.assertNotIn('completed_integration_trainings', EmployeeForm().fields)

    def test_saving_employee_does_not_change_integration_trainings(self):
        department = Department.objects.create(name='Produção')
        job = JobTitle.objects.create(name='Operador', department=department, base_salary=2500)
        employee = Employee.objects.create(
            name='Ana', cpf='67134509206', birth_date=date(1990, 1, 1), department=department,
            job_title=job, current_salary=2500, hire_date=date(2020, 1, 6),
        )
        linked = Training.objects.create(training_name='Integração A', training_total_hours=4, is_integration=True)
        linked.scheduled_employees.set([employee])
        linked.attended_employees.set([employee])
        Training.objects.create(training_name='Integração B', training_total_hours=4, is_integration=True)

        form = EmployeeForm(instance=employee)
        data = {name: form[name].value() for name in form.fields}
        data = {k: ('' if v is None else v) for k, v in data.items() if not isinstance(v, bool) or v}
        bound = EmployeeForm(data=data, instance=employee)
        self.assertTrue(bound.is_valid(), bound.errors)
        bound.save()

        self.assertEqual(list(employee.scheduled_trainings.values_list('training_name', flat=True)), ['Integração A'])
        self.assertEqual(list(employee.attended_trainings.values_list('training_name', flat=True)), ['Integração A'])
