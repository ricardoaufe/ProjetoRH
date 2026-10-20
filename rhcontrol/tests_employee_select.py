from datetime import date

from django.test import TestCase

from rhcontrol.forms import CareerPlanForm, TrainingForm, VacationForm
from rhcontrol.models import Department, Employee, JobTitle, Training, Vacation


class EmployeeSelectTests(TestCase):
    """Campos de funcionário: só ativos, em ordem alfabética, sem quebrar a edição."""

    def setUp(self):
        self.department = Department.objects.create(name='Manutenção')
        job = JobTitle.objects.create(name='Mecânico', department=self.department, base_salary=3000)

        def employee(name, cpf, termination_date=None):
            return Employee.objects.create(
                name=name, cpf=cpf, birth_date=date(1990, 1, 1), department=self.department,
                job_title=job, hire_date=date(2024, 1, 1), termination_date=termination_date,
            )

        self.zeca = employee('ZECA LIMA', '11111111111')
        self.ana = employee('ANA SOUZA', '22222222222')
        self.former = employee('BRUNO DESLIGADO', '33333333333', termination_date=date(2026, 1, 10))

    def _choices(self, form, field):
        return [label for value, label in form.fields[field].choices if value]

    def test_new_forms_list_only_active_in_alphabetical_order(self):
        expected = ['ANA SOUZA · Manutenção', 'ZECA LIMA · Manutenção']
        self.assertEqual(self._choices(VacationForm(), 'employee'), expected)
        self.assertEqual(self._choices(CareerPlanForm(), 'employee'), expected)
        self.assertEqual(self._choices(TrainingForm(), 'scheduled_employees'), expected)
        self.assertEqual(self._choices(TrainingForm(), 'attended_employees'), expected)

    def test_new_vacation_rejects_terminated_employee(self):
        form = VacationForm(data={
            'employee': self.former.pk, 'start_date': '2026-12-15', 'vacation_duration': 10,
        })
        self.assertIn('employee', form.errors)

    def test_vacation_edit_keeps_terminated_employee(self):
        vacation = Vacation.objects.create(
            employee=self.former, start_date=date(2025, 12, 1), vacation_duration=10
        )
        form = VacationForm(instance=vacation, data={
            'employee': self.former.pk, 'start_date': '2025-12-01', 'vacation_duration': 15,
        })
        self.assertTrue(form.is_valid(), form.errors)
        self.assertIn('BRUNO DESLIGADO · Manutenção', self._choices(form, 'employee'))

    def test_training_edit_keeps_terminated_participants(self):
        training = Training.objects.create(
            training_name='NR-12', training_location_type='Interno', training_total_hours=8,
        )
        training.scheduled_employees.add(self.former, self.ana)
        training.attended_employees.add(self.former)

        form = TrainingForm(instance=training)
        self.assertIn('BRUNO DESLIGADO · Manutenção', self._choices(form, 'scheduled_employees'))
        self.assertIn('BRUNO DESLIGADO · Manutenção', self._choices(form, 'attended_employees'))
        # Quem não está neste treinamento continua de fora.
        self.assertNotIn('BRUNO DESLIGADO · Manutenção', self._choices(TrainingForm(), 'scheduled_employees'))

    def test_training_attendance_offers_only_participants(self):
        training = Training.objects.create(
            training_name='NR-10', training_location_type='Interno', training_total_hours=8,
        )
        training.scheduled_employees.add(self.ana)

        form = TrainingForm(instance=training)
        self.assertEqual(self._choices(form, 'attended_employees'), ['ANA SOUZA · Manutenção'])

    def test_training_removed_participant_leaves_attendance(self):
        training = Training.objects.create(
            training_name='NR-10', training_location_type='Interno', training_total_hours=8,
        )
        training.scheduled_employees.add(self.ana, self.zeca)
        training.attended_employees.add(self.ana, self.zeca)

        # Tira o ZECA dos participantes sem mexer na confirmação.
        form = TrainingForm(instance=training, data={
            'training_name': 'NR-10', 'training_location_type': 'Interno', 'training_total_hours': 8,
            'scheduled_employees': [self.ana.pk],
            'attended_employees': [self.ana.pk, self.zeca.pk],
        })
        self.assertTrue(form.is_valid(), form.errors)
        form.save()
        self.assertEqual(list(training.attended_employees.all()), [self.ana])
