from datetime import date
from unittest.mock import patch

from django.core import mail
from django.test import TestCase

from rhcontrol.models import (
    Department,
    Employee,
    EventTypes,
    JobTitle,
    NotificationRecipient,
    NotificationRule,
    Vacation,
)
from rhcontrol.services import get_vacation_deadline, process_notifications


class VacationDeadlineTests(TestCase):
    """Vencimento de férias pela CLT, contado a partir da admissão."""

    def setUp(self):
        dept = Department.objects.create(name='RH')
        job = JobTitle.objects.create(name='Analista', department=dept, base_salary=3000)
        self.employee = Employee.objects.create(
            name='Fulano', cpf='12345678901', birth_date='1990-01-01',
            department=dept, job_title=job, hire_date=date(2025, 10, 14),
        )

    def _vacation(self, start, days):
        Vacation.objects.create(employee=self.employee, start_date=start, vacation_duration=days)

    def test_no_deadline_during_first_year(self):
        self.assertIsNone(get_vacation_deadline(self.employee, date(2026, 10, 13)))

    def test_deadline_and_notice_four_months_before(self):
        result = get_vacation_deadline(self.employee, date(2026, 10, 14))
        self.assertEqual(result['window_start'], date(2026, 10, 14))
        self.assertEqual(result['deadline'], date(2027, 10, 13))
        self.assertEqual(result['notice_date'], date(2027, 6, 13))
        self.assertFalse(result['is_due'])

    def test_is_due_from_notice_date(self):
        self.assertFalse(get_vacation_deadline(self.employee, date(2027, 6, 12))['is_due'])
        self.assertTrue(get_vacation_deadline(self.employee, date(2027, 6, 13))['is_due'])

    def test_split_vacations_cancel_notice_only_when_complete(self):
        self._vacation(date(2027, 3, 1), 20)
        self.assertTrue(get_vacation_deadline(self.employee, date(2027, 6, 13))['is_due'])

        self._vacation(date(2027, 7, 1), 10)
        self.assertFalse(get_vacation_deadline(self.employee, date(2027, 6, 13))['is_due'])

    def test_scheduled_future_vacation_counts(self):
        self._vacation(date(2027, 9, 1), 30)
        self.assertFalse(get_vacation_deadline(self.employee, date(2027, 6, 13))['is_due'])

    def test_vacation_outside_window_does_not_count(self):
        # Férias do 1º período (até 13/10/2027) não contam para o 2º período.
        self._vacation(date(2027, 9, 15), 30)
        result = get_vacation_deadline(self.employee, date(2028, 6, 13))
        self.assertEqual(result['deadline'], date(2028, 10, 13))
        self.assertTrue(result['is_due'])

    def test_terminated_employee_has_no_deadline(self):
        self.employee.termination_date = date(2027, 1, 10)
        self.employee.save()
        self.assertIsNone(get_vacation_deadline(self.employee, date(2027, 6, 13)))


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
        self.assertEqual(mail.outbox[0].to, ['rh@teste.com'])
        self.assertIn('FÉRIAS PARA VENCER em 13/10/2027', mail.outbox[0].subject)
        self.assertIn('Prazo para concessão: 14/10/2026 a 13/10/2027', mail.outbox[0].body)
        self.assertNotIn('Saldo', mail.outbox[0].body)

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
