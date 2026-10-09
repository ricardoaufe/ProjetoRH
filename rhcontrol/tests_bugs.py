"""
Testes de regressão dos bugs corrigidos na Etapa 2 da auditoria.
"""
from datetime import date, timedelta

from django.core import mail
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from rhcontrol.models import (
    CareerPlan,
    Department,
    Employee,
    EventTypes,
    JobTitle,
    NotificationRecipient,
    NotificationRule,
    Occurrence,
)
from rhcontrol.services import process_career_plans
from rhcontrol.tests_security import make_user


def make_department_and_job():
    department = Department.objects.create(name='Produção')
    job_title = JobTitle.objects.create(name='Operador', department=department, base_salary=2500)
    return department, job_title


class EmployeeStatusFilterTests(TestCase):
    """Os filtros Ativos/Demitidos da lista usam os mesmos valores dos links do template."""

    def setUp(self):
        self.client.force_login(make_user('rh', 'rhcontrol.view_employee'))
        department, job_title = make_department_and_job()
        common = {'birth_date': date(1990, 1, 1), 'department': department, 'job_title': job_title}
        self.active = Employee.objects.create(name='Ativo', cpf='11111111111', **common)
        self.terminated = Employee.objects.create(
            name='Demitido', cpf='22222222222', termination_date=date(2025, 12, 31), **common
        )

    def _listed(self, status):
        response = self.client.get(reverse('rhcontrol:employee_list'), {'status': status})
        return list(response.context['object_list'])

    def test_terminated_filter(self):
        self.assertEqual(self._listed('terminated'), [self.terminated])

    def test_active_filter(self):
        self.assertEqual(self._listed('active'), [self.active])

    def test_template_links_use_filter_values(self):
        response = self.client.get(reverse('rhcontrol:employee_list'))
        self.assertContains(response, '?status=terminated')
        self.assertContains(response, '?status=active')

    def test_sort_by_mobile_phone(self):
        self.active.mobile_phone = '(11) 99999-0000'
        self.active.save()
        self.terminated.mobile_phone = '(11) 90000-0000'
        self.terminated.save()
        response = self.client.get(reverse('rhcontrol:employee_list'), {'sort': 'mobile_phone'})
        self.assertEqual(list(response.context['object_list']), [self.terminated, self.active])


def make_employee(**extra):
    department, job_title = make_department_and_job()
    return Employee.objects.create(
        name='Carlos Silva', cpf='67134509206', birth_date=date(1988, 7, 10),
        department=department, job_title=job_title, **extra,
    )


class AbsenceDurationTests(TestCase):
    """Afastamento sem data de fim conta os dias até hoje (antes dava erro e virava 0)."""

    def test_open_absence_counts_until_today(self):
        occurrence = Occurrence.objects.create(
            employee=make_employee(), title='Atestado', description='-',
            is_absence=True, occurrence_date=timezone.localdate() - timedelta(days=4),
        )
        self.assertEqual(occurrence.absence_duration, 5)

    def test_closed_absence_counts_inclusive_days(self):
        start = timezone.localdate() - timedelta(days=10)
        occurrence = Occurrence.objects.create(
            employee=make_employee(), title='Atestado', description='-',
            is_absence=True, occurrence_date=start, end_date=start + timedelta(days=2),
        )
        self.assertEqual(occurrence.absence_duration, 3)


class EmployeeSalaryChangeTests(TestCase):
    """Editar o salário gera histórico sem erro, inclusive quando ainda não havia salário."""

    def setUp(self):
        self.client.force_login(make_user('rh', 'rhcontrol.change_employee'))

    def _post_salary(self, employee, salary):
        url = reverse('rhcontrol:employee_update', kwargs={'pk': employee.pk})
        prefix = self.client.get(url).context['dependent_formset'].prefix
        return self.client.post(url, {
            'name': employee.name, 'cpf': employee.cpf, 'birth_date': '1988-07-10',
            'department': employee.department_id, 'job_title': employee.job_title_id,
            'current_salary': salary,
            f'{prefix}-TOTAL_FORMS': '0', f'{prefix}-INITIAL_FORMS': '0',
            f'{prefix}-MIN_NUM_FORMS': '0', f'{prefix}-MAX_NUM_FORMS': '1000',
        })

    def test_setting_salary_for_the_first_time(self):
        employee = make_employee()
        response = self._post_salary(employee, '3000.00')
        self.assertEqual(response.status_code, 302)
        self.assertEqual(employee.history.get().reason, 'Definição de Salário')

    def test_raise_is_merit(self):
        employee = make_employee(current_salary=2000)
        self._post_salary(employee, '3000.00')
        self.assertEqual(employee.history.get().reason, 'Mérito')


class AnonymousRedirectTests(TestCase):
    """Usuário deslogado é mandado para o login em todas as páginas (antes recebia 403)."""

    PUBLIC = {'login', 'login_create'}

    def test_every_page_redirects_anonymous_to_login(self):
        from django.urls import get_resolver

        employee = make_employee()
        kwargs_by_name = {'pk': employee.pk, 'employee_id': employee.pk}
        login_url = reverse('rhcontrol:login')
        resolver = get_resolver().url_patterns
        app_patterns = next(p for p in resolver if getattr(p, 'app_name', None) == 'rhcontrol')

        for pattern in app_patterns.url_patterns:
            if pattern.name in self.PUBLIC:
                continue
            kwargs = {k: kwargs_by_name[k] for k in pattern.pattern.converters}
            url = reverse(f'rhcontrol:{pattern.name}', kwargs=kwargs)
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(response.status_code, 302)
                self.assertTrue(response['Location'].startswith(login_url))

    def test_logged_user_without_permission_still_gets_403(self):
        employee = make_employee()
        self.client.force_login(make_user('sem-permissao'))
        for url in [
            reverse('rhcontrol:employee_list'),
            reverse('rhcontrol:occurrence_list', kwargs={'employee_id': employee.pk}),
        ]:
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 403)


class DismissalCancelsCareerPlanEmailTests(TestCase):
    """O RH é avisado por e-mail quando um plano é cancelado porque o funcionário foi desligado."""

    def setUp(self):
        NotificationRecipient.objects.create(
            name='RH', email='rh@empresa.com', is_active=True, receive_all_events=True
        )
        self.employee = make_employee(current_salary=2500)
        self.plan = CareerPlan.objects.create(
            employee=self.employee,
            proposed_job=self.employee.job_title,
            proposed_salary=3000,
            promotion_date=timezone.localdate() + timedelta(days=10),
        )
        self.employee.termination_date = timezone.localdate()
        self.employee.save(update_fields=['termination_date'])

    def test_cancellation_email_is_sent(self):
        NotificationRule.objects.create(
            event_type=EventTypes.CAREER_PLAN_CANCELLED, is_active=True, days_in_advance=0
        )
        process_career_plans()
        self.plan.refresh_from_db()
        self.assertEqual(self.plan.status, CareerPlan.PlanStatus.CANCELLED)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('Funcionário desligado', mail.outbox[0].body)

    def test_other_events_for_terminated_employee_stay_silent(self):
        NotificationRule.objects.create(
            event_type=EventTypes.CAREER_PLAN_REMINDER, is_active=True, days_in_advance=0
        )
        from rhcontrol.services import notify_career_plan_event
        notify_career_plan_event(self.plan, EventTypes.CAREER_PLAN_REMINDER)
        self.assertEqual(len(mail.outbox), 0)


class UpcomingPromotionFilterTests(TestCase):
    """Filtrar os próximos eventos por funcionário não pode esconder a promoção."""

    def test_promotion_shown_when_filtering_by_employee_or_department(self):
        from rhcontrol.models import CareerPlan
        from rhcontrol.services import get_upcoming_events

        employee = make_employee()
        senior = JobTitle.objects.create(
            name='Operador Sênior', department=employee.department, base_salary=3500
        )
        today = timezone.localdate()
        CareerPlan.objects.create(
            employee=employee, proposed_job=senior, proposed_salary=3500,
            promotion_date=today + timedelta(days=10),
        )

        for filters in ({}, {'employee_id': employee.pk}, {'department_id': employee.department_id}):
            with self.subTest(filters=filters):
                events = get_upcoming_events(
                    start_date=today, end_date=today + timedelta(days=30), **filters
                )
                categories = [e['category'] for e in events]
                self.assertIn('CAREER_PLAN_PROMOTION_DATE', categories)
