from datetime import date
from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from rhcontrol.forms import VacationForm
from rhcontrol.models import Department, Employee, JobTitle, Vacation
from rhcontrol.services import get_vacation_periods


# Nestes testes o controle começa antes da admissão, para todo período contar.
ALL_PERIODS_TRACKED = patch('rhcontrol.services.VACATION_TRACKING_START', date(2000, 1, 1))


@ALL_PERIODS_TRACKED
class VacationRulesTests(TestCase):
    """
    Regras da CLT no cadastro de férias. Admissão em 04/03/2024: o 1º período
    libera em 04/03/2025 e vence em 03/03/2026; o 2º libera em 04/03/2026.
    """

    def setUp(self):
        dept = Department.objects.create(name='RH')
        job = JobTitle.objects.create(name='Analista', department=dept, base_salary=3000)
        self.employee = Employee.objects.create(
            name='Fulano', cpf='12345678901', birth_date='1990-01-01',
            department=dept, job_title=job, hire_date=date(2024, 3, 4),
        )

    def _vacation(self, start, days, cash_bonus=False):
        return Vacation.objects.create(
            employee=self.employee, start_date=start, vacation_duration=days, cash_bonus=cash_bonus,
        )

    def _form(self, start, days, cash_bonus=False, instance=None):
        data = {'employee': self.employee.pk, 'start_date': start, 'vacation_duration': days}
        if cash_bonus:
            data['cash_bonus'] = 'on'
        return VacationForm(data=data, instance=instance)

    def _error(self, form, field):
        self.assertFalse(form.is_valid())
        return ' '.join(form.errors[field])

    # Período aquisitivo (art. 130)

    def test_blocks_before_twelve_months(self):
        form = self._form('2025-02-03', 30)
        self.assertIn('Só a partir de 04/03/2025', self._error(form, 'start_date'))

    def test_next_period_not_acquired_yet(self):
        self._vacation(date(2025, 6, 2), 30)
        form = self._form('2025-10-06', 10)
        self.assertIn('Só a partir de 04/03/2026', self._error(form, 'start_date'))

    def test_requires_hire_date(self):
        self.employee.hire_date = None
        self.employee.save()
        self.assertIn('data de admissão', self._error(self._form('2025-06-02', 30), 'employee'))

    # Início (art. 134 §3º)

    def test_blocks_start_two_days_before_sunday(self):
        # 09/05/2025 é sexta: o domingo cai 2 dias depois.
        self.assertIn('domingo', self._error(self._form('2025-05-09', 30), 'start_date'))

    def test_blocks_start_two_days_before_holiday(self):
        # 23/12/2025 é terça e 25/12 é Natal.
        self.assertIn('feriado', self._error(self._form('2025-12-23', 30), 'start_date'))

    def test_blocks_overlap_and_after_termination(self):
        vacation = self._vacation(date(2025, 6, 2), 15)
        self.assertIn('Já há férias', self._error(self._form('2025-06-10', 15), 'start_date'))

        # Desligado só continua na lista ao editar férias já cadastradas.
        self.employee.termination_date = date(2025, 9, 10)
        self.employee.save()
        form = self._form('2025-09-01', 15, instance=vacation)
        self.assertIn('desligado', self._error(form, 'start_date'))

    # Duração e fracionamento (art. 134 §1º)

    def test_blocks_more_than_thirty_days_per_period(self):
        self._vacation(date(2025, 6, 2), 20)
        self.assertIn('Restam 10 dias', self._error(self._form('2025-08-04', 15), 'vacation_duration'))

    def test_blocks_part_under_five_days(self):
        self.assertIn('pelo menos 5 dias', self._error(self._form('2025-06-02', 4), 'vacation_duration'))

    def test_requires_one_part_with_fourteen_days(self):
        self._vacation(date(2025, 6, 2), 10)
        self.assertIn('14 dias', self._error(self._form('2025-08-04', 10), 'vacation_duration'))

    def test_accepts_three_parts(self):
        self._vacation(date(2025, 6, 2), 14)
        self._vacation(date(2025, 8, 4), 8)
        self.assertTrue(self._form('2025-10-06', 8).is_valid())

    def test_blocks_leftover_that_cannot_be_taken(self):
        self.assertIn('Sobrariam 3 dias', self._error(self._form('2025-06-02', 27), 'vacation_duration'))

        self._vacation(date(2025, 6, 2), 14)
        self._vacation(date(2025, 8, 4), 5)
        self.assertIn('após a 3ª parte', self._error(self._form('2025-10-06', 5), 'vacation_duration'))

    # Abono pecuniário (art. 143)

    def test_cash_bonus_sells_the_rest(self):
        self.assertTrue(self._form('2025-06-02', 20, cash_bonus=True).is_valid())

        self._vacation(date(2025, 6, 2), 15)
        self.assertTrue(self._form('2025-08-04', 5, cash_bonus=True).is_valid())

    def test_cash_bonus_needs_something_to_sell(self):
        form = self._form('2025-06-02', 30, cash_bonus=True)
        self.assertIn('Não sobra saldo', self._error(form, 'cash_bonus'))

    def test_cash_bonus_limited_to_one_third(self):
        form = self._form('2025-06-02', 15, cash_bonus=True)
        self.assertIn('até 10', self._error(form, 'cash_bonus'))

    def test_cash_bonus_requires_part_with_fourteen_days(self):
        self._vacation(date(2025, 6, 2), 10)
        form = self._form('2025-08-04', 10, cash_bonus=True)
        self.assertIn('14 dias', self._error(form, 'vacation_duration'))

    # Edição e vencimento (art. 137)

    def test_edit_ignores_the_vacation_itself(self):
        vacation = self._vacation(date(2025, 6, 2), 30)
        self.assertTrue(self._form('2025-08-04', 30, instance=vacation).is_valid())

    def test_late_vacation_is_allowed_but_flagged(self):
        self._vacation(date(2025, 6, 2), 15)
        form = self._form('2026-04-06', 15)
        self.assertTrue(form.is_valid())
        self.assertTrue(form.is_late)
        self.assertEqual(form.period['number'], 1)

    def test_late_vacation_shows_warning(self):
        self.client.force_login(User.objects.create_superuser('admin', 'admin@empresa.com', 'senha-forte-123'))
        self._vacation(date(2025, 6, 2), 15)
        response = self.client.post(reverse('rhcontrol:vacation_create'), {
            'employee': self.employee.pk, 'start_date': '2026-04-06', 'vacation_duration': 15,
        }, follow=True)
        self.assertContains(response, 'devem ser pagas em dobro')


@ALL_PERIODS_TRACKED
class VacationBalanceTests(TestCase):
    """Saldo por período: só cai quando as férias começam."""

    def setUp(self):
        dept = Department.objects.create(name='RH')
        job = JobTitle.objects.create(name='Analista', department=dept, base_salary=3000)
        self.employee = Employee.objects.create(
            name='Fulano', cpf='12345678901', birth_date='1990-01-01',
            department=dept, job_title=job, hire_date=date(2024, 3, 4),
        )

    def _period(self, today, number=1):
        return get_vacation_periods(self.employee, today)[number - 1]

    def test_scheduled_vacation_does_not_reduce_balance_until_it_starts(self):
        Vacation.objects.create(
            employee=self.employee, start_date=date(2025, 6, 2), vacation_duration=20, cash_bonus=True,
        )
        before = self._period(date(2025, 5, 1))
        self.assertEqual((before['balance'], before['scheduled_days'], before['free_days']), (30, 20, 0))

        started = self._period(date(2025, 6, 2))
        self.assertEqual((started['balance'], started['sold_days']), (0, 10))

    def test_vacations_consume_oldest_period_first(self):
        Vacation.objects.create(employee=self.employee, start_date=date(2025, 6, 2), vacation_duration=10)
        Vacation.objects.create(employee=self.employee, start_date=date(2026, 4, 6), vacation_duration=20)
        periods = get_vacation_periods(self.employee, date(2026, 5, 1))
        self.assertEqual(periods[0]['balance'], 0)
        self.assertEqual(periods[0]['expired_days'], 20)
        self.assertEqual(periods[1]['balance'], 30)

    def test_periods_before_first_registered_vacation_are_settled(self):
        # Admitido em 2015 com férias cadastradas só a partir de 2025.
        self.employee.hire_date = date(2015, 3, 2)
        self.employee.save()
        Vacation.objects.create(employee=self.employee, start_date=date(2025, 6, 2), vacation_duration=30)
        periods = get_vacation_periods(self.employee, date(2025, 12, 1))
        self.assertTrue(all(p['is_settled'] for p in periods[:9]))
        self.assertFalse(any(p['balance'] or p['expired_days'] for p in periods[:10]))
        self.assertEqual(periods[9]['vacations'][0].start_date, date(2025, 6, 2))

    def test_without_vacations_every_period_is_open(self):
        periods = get_vacation_periods(self.employee, date(2026, 5, 1))
        self.assertEqual(periods[0]['expired_days'], 30)

    def test_accrued_days_of_period_in_progress(self):
        # 2º período começou em 04/03/2025: em 20/10/2025 são 7 meses e 16 dias.
        period = self._period(date(2025, 10, 20), number=2)
        self.assertEqual(period['accrued_days'], 20)

    def test_employee_page_shows_balance(self):
        self.client.force_login(User.objects.create_superuser('admin', 'admin@empresa.com', 'senha-forte-123'))
        Vacation.objects.create(employee=self.employee, start_date=date(2025, 6, 2), vacation_duration=20)
        with patch('django.utils.timezone.localdate', return_value=date(2025, 12, 1)):
            response = self.client.get(reverse('rhcontrol:employee_update', args=[self.employee.pk]))
        self.assertContains(response, 'Saldo de férias')
        self.assertContains(response, '04/03/2024 a 03/03/2025: <strong>10 dias</strong>', html=False)
        self.assertContains(response, 'Em aquisição: 22,5 dias (libera em 04/03/2026)')


class VacationTrackingStartTests(TestCase):
    """Períodos iniciados antes de 01/02/2025 já foram resolvidos fora do sistema."""

    def setUp(self):
        dept = Department.objects.create(name='RH')
        job = JobTitle.objects.create(name='Analista', department=dept, base_salary=3000)
        self.employee = Employee.objects.create(
            name='Fulano', cpf='12345678901', birth_date='1990-01-01',
            department=dept, job_title=job, hire_date=date(2022, 5, 2),
        )

    def test_periods_started_before_tracking_are_settled(self):
        periods = get_vacation_periods(self.employee, date(2026, 6, 1))
        self.assertTrue(all(p['is_settled'] for p in periods[:3]))
        self.assertFalse(any(p['expired_days'] for p in periods))
        self.assertEqual((periods[3]['start'], periods[3]['balance']), (date(2025, 5, 2), 30))

    def test_vacation_of_settled_period_is_history_only(self):
        form = VacationForm(data={
            'employee': self.employee.pk, 'start_date': '2025-06-02', 'vacation_duration': 30,
        })
        self.assertTrue(form.is_valid(), form.errors)
        self.assertIsNone(form.period)
        form.save()
        self.assertEqual(get_vacation_periods(self.employee, date(2026, 6, 1))[3]['balance'], 30)
