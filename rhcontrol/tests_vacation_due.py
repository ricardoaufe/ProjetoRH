from datetime import date
from unittest.mock import patch

from django.contrib.auth.models import Permission, User
from django.core import mail
from django.test import TestCase
from django.urls import reverse

from rhcontrol.models import (
    Department,
    Employee,
    EventTypes,
    JobTitle,
    NotificationRecipient,
    NotificationRule,
    Vacation,
)
from rhcontrol.services import get_vacation_balance, process_notifications


class VacationBalanceTests(TestCase):
    """Saldo e vencimento de férias pela CLT, contados a partir da admissão."""

    def setUp(self):
        dept = Department.objects.create(name='RH')
        job = JobTitle.objects.create(name='Analista', department=dept, base_salary=3000)
        self.employee = Employee.objects.create(
            name='Fulano', cpf='12345678901', birth_date='1990-01-01',
            department=dept, job_title=job, hire_date=date(2025, 10, 14),
        )

    def _vacation(self, start, days):
        Vacation.objects.create(employee=self.employee, start_date=start, vacation_duration=days)

    def test_first_year_only_shows_when_vacation_becomes_available(self):
        result = get_vacation_balance(self.employee, date(2026, 10, 13))
        self.assertEqual(result, {'available_from': date(2026, 10, 14)})

    def test_deadline_and_notice_four_months_before(self):
        result = get_vacation_balance(self.employee, date(2026, 10, 14))
        self.assertEqual(result['window_start'], date(2026, 10, 14))
        self.assertEqual(result['deadline'], date(2027, 10, 13))
        self.assertEqual(result['notice_date'], date(2027, 6, 13))
        self.assertEqual(result['balance'], 30)
        self.assertFalse(result['is_due'])

    def test_is_due_from_notice_date(self):
        self.assertFalse(get_vacation_balance(self.employee, date(2027, 6, 12))['is_due'])
        self.assertTrue(get_vacation_balance(self.employee, date(2027, 6, 13))['is_due'])

    def test_split_vacations_reduce_balance(self):
        self._vacation(date(2027, 3, 1), 20)
        self.assertEqual(get_vacation_balance(self.employee, date(2027, 6, 13))['balance'], 10)

        self._vacation(date(2027, 7, 1), 10)
        result = get_vacation_balance(self.employee, date(2027, 6, 13))
        self.assertEqual(result['balance'], 0)
        self.assertFalse(result['is_due'])

    def test_scheduled_future_vacation_counts(self):
        self._vacation(date(2027, 9, 1), 30)
        self.assertEqual(get_vacation_balance(self.employee, date(2027, 6, 13))['balance'], 0)

    def test_vacation_outside_window_does_not_count(self):
        # Férias do 1º período (até 13/10/2027) não abatem o 2º período.
        self._vacation(date(2027, 9, 15), 30)
        result = get_vacation_balance(self.employee, date(2027, 10, 14))
        self.assertEqual(result['deadline'], date(2028, 10, 13))
        self.assertEqual(result['balance'], 30)

    def test_terminated_employee_has_no_balance(self):
        self.employee.termination_date = date(2027, 1, 10)
        self.employee.save()
        self.assertIsNone(get_vacation_balance(self.employee, date(2027, 6, 13)))


class VacationDueNotificationTests(TestCase):

    def setUp(self):
        dept = Department.objects.create(name='RH')
        job = JobTitle.objects.create(name='Analista', department=dept, base_salary=3000)
        self.employee = Employee.objects.create(
            name='Fulano', cpf='12345678901', birth_date='1990-01-01',
            department=dept, job_title=job, hire_date=date(2025, 10, 14),
        )
        NotificationRule.objects.create(event_type=EventTypes.VACATION_DUE, days_in_advance=0)
        NotificationRecipient.objects.create(name='RH', email='rh@teste.com', receive_all_events=True)

    def _run_on(self, day):
        with patch('rhcontrol.services.timezone.localdate', return_value=day):
            process_notifications()

    def test_email_sent_four_months_before_deadline(self):
        self._run_on(date(2027, 6, 13))
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('FÉRIAS PARA VENCER em 13/10/2027', mail.outbox[0].subject)
        self.assertIn('Saldo: 30 dia(s)', mail.outbox[0].body)

    def test_no_email_before_notice_date(self):
        self._run_on(date(2027, 6, 12))
        self.assertEqual(len(mail.outbox), 0)

    def test_late_run_still_sends_only_once(self):
        # Cron parado no dia do aviso: envia no dia seguinte, e não repete.
        self._run_on(date(2027, 6, 14))
        self._run_on(date(2027, 6, 15))
        self.assertEqual(len(mail.outbox), 1)

    def test_no_email_when_vacation_already_taken(self):
        Vacation.objects.create(employee=self.employee, start_date=date(2027, 3, 1), vacation_duration=30)
        self._run_on(date(2027, 6, 13))
        self.assertEqual(len(mail.outbox), 0)

    def test_no_email_without_active_rule(self):
        NotificationRule.objects.update(is_active=False)
        self._run_on(date(2027, 6, 13))
        self.assertEqual(len(mail.outbox), 0)


class VacationBalanceScreenTests(TestCase):

    def test_employee_page_shows_balance(self):
        user = User.objects.create_user(username='rh', password='senha123')
        user.user_permissions.add(*Permission.objects.filter(
            content_type__app_label='rhcontrol', codename__in=['view_employee', 'change_employee']
        ))
        self.client.login(username='rh', password='senha123')

        dept = Department.objects.create(name='RH')
        job = JobTitle.objects.create(name='Analista', department=dept, base_salary=3000)
        employee = Employee.objects.create(
            name='Fulano', cpf='12345678901', birth_date='1990-01-01',
            department=dept, job_title=job, hire_date=date(2024, 1, 10),
        )

        with patch('rhcontrol.services.timezone.localdate', return_value=date(2025, 6, 1)), \
             patch('rhcontrol.views.employee.timezone.localdate', return_value=date(2025, 6, 1)):
            response = self.client.get(reverse('rhcontrol:employee_update', args=[employee.pk]))

        self.assertContains(response, 'Saldo de férias')
        self.assertContains(response, '09/01/2026')
