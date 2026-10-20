"""Relatório de horas e presença em treinamentos (dropdown Relatórios)."""
from datetime import date

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from rhcontrol.models import Department, Employee, JobTitle, Training
from rhcontrol.services import get_training_attendance_ranking

TODAY = date(2026, 10, 20)


class TrainingAttendanceRankingTests(TestCase):

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

        def training(name, hours, scheduled, attended, start=date(2026, 1, 10), **extra):
            t = Training.objects.create(
                training_name=name, training_total_hours=hours, start_date=start, **extra
            )
            t.scheduled_employees.set(scheduled)
            t.attended_employees.set(attended)
            return t

        training('NR-12', 8, [cls.ana, cls.bruno, cls.former], [cls.ana, cls.former])
        training('NR-35', 4, [cls.ana, cls.bruno], [cls.bruno])
        training('Individual', 2, [cls.ana], [cls.ana])
        # Fora da conta: futuro, fundamental (presença automática) e integração.
        training('Futuro', 40, [cls.ana, cls.bruno], [cls.ana, cls.bruno], start=date(2026, 12, 1))
        training('Fundamental', 40, [cls.bruno], [cls.bruno], is_fundamental=True)
        training('Integração', 40, [cls.bruno], [cls.bruno], is_integration=True)

    def _rows(self):
        return {row['employee'].name: row for row in get_training_attendance_ranking(today=TODAY)}

    def test_counts_only_trainings_each_employee_was_scheduled_for(self):
        rows = self._rows()
        self.assertEqual(
            (rows['Ana']['hours'], rows['Ana']['attended'], rows['Ana']['scheduled'], rows['Ana']['rate']),
            (10, 2, 3, 67),
        )
        self.assertEqual(
            (rows['Bruno']['hours'], rows['Bruno']['attended'], rows['Bruno']['scheduled'], rows['Bruno']['rate']),
            (4, 1, 2, 50),
        )

    def test_active_employee_without_trainings_shows_zero_without_rate(self):
        carla = self._rows()['Carla']
        self.assertEqual((carla['hours'], carla['attended'], carla['scheduled'], carla['rate']), (0, 0, 0, None))

    def test_terminated_employees_are_left_out(self):
        self.assertNotIn('Demitido', self._rows())

    def test_attended_without_being_scheduled_counts_as_scheduled(self):
        # Dados antigos podem ter presença sem previsão: nunca passar de 100%.
        legacy = Training.objects.create(training_name='Antigo', training_total_hours=1, start_date=date(2025, 1, 1))
        legacy.attended_employees.add(self.carla)
        carla = self._rows()['Carla']
        self.assertEqual((carla['attended'], carla['scheduled'], carla['rate']), (1, 1, 100))

    def test_sorted_by_hours_then_rate_then_name(self):
        names = [row['employee'].name for row in get_training_attendance_ranking(today=TODAY)]
        self.assertEqual(names, ['Ana', 'Bruno', 'Carla'])

    def test_pdf_lists_employees_and_menu_links_to_it(self):
        user = User.objects.create_superuser('admin', 'admin@empresa.com', 'senha-forte-123')
        self.client.force_login(user)

        response = self.client.get(reverse('rhcontrol:training_attendance_pdf'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/pdf')

        page = self.client.get(reverse('rhcontrol:training_list'))
        self.assertContains(page, reverse('rhcontrol:training_attendance_pdf'))

    def test_pdf_requires_training_permission(self):
        user = User.objects.create_user('sem_perm', 'x@empresa.com', 'senha-forte-123')
        self.client.force_login(user)
        response = self.client.get(reverse('rhcontrol:training_attendance_pdf'))
        self.assertEqual(response.status_code, 403)
