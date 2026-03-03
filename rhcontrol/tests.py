from decimal import Decimal
import inspect

from attrs import inspect
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from django.contrib.staticfiles import finders
from rhcontrol.models import CareerPlan, Employee, EventTypes, JobTitle, NotificationRecipient, NotificationRule,NotificationLog, Training, Vacation, Department
from rhcontrol.forms import EmployeeForm
from datetime import datetime, timedelta
from django.utils import timezone
from django.core import mail
from rhcontrol.services import process_career_plans


class RhcontrolTests(TestCase):
    def test_dashboard_url_working(self):
        dashboard_url = reverse('rhcontrol:dashboard')
        self.assertEqual(dashboard_url, '/')
    
    def test_profile_url_working(self):
        profile_url = reverse('rhcontrol:profile')
        self.assertEqual(profile_url, '/profile/')

    def test_change_password_url_working(self):
        change_password_url = reverse('rhcontrol:change_password')
        self.assertEqual(change_password_url, '/profile/password/') 

class VacationModelTests(TestCase):
    def setUp(self):
        self.department = Department.objects.create(name="HR")
        self.job_title = JobTitle.objects.create(
            name='Developer',
            department=self.department, 
            base_salary=60000
        )
        self.employee = Employee.objects.create(
            name='João Silva',
            cpf='12345678901',
            birth_date='1990-01-01',
            department=self.department,
            job_title=self.job_title
        )
    
    def test_vacation_end_date_calculation(self):
        # Test that end_date is calculated correctly
        vacation = Vacation.objects.create(
            employee=self.employee,
            start_date=datetime(2026, 2, 1).date(),
            vacation_duration=10
        )
        expected_end = datetime(2026, 2, 11).date()
        self.assertEqual(vacation.end_date, expected_end)

    def test_vacation_return_date_skips_weekends(self):
        # If return date falls on weekend, it should skip to Monday
        vacation = Vacation.objects.create(
            employee=self.employee,
            start_date=datetime(2026, 2, 6).date(),  # Friday
            vacation_duration=1
        )
        # Should skip weekend and return on Monday
        self.assertEqual(vacation.return_date.weekday(), 0)  # 0 = Monday
    

class EmployeeFormTests(TestCase):
    def setUp(self):
        self.department = Department.objects.create(name='Vendas')
        self.job_title = JobTitle.objects.create(
            name='Vendedor',
            department=self.department,
            base_salary=3000.00
        )
    
    def test_job_title_queryset_filtered_by_department(self):
        # Test that job_title field only shows jobs from selected department
        form_data = {
            'department': self.department.id,
            'name': 'Pedro',
            'cpf': '98765432101',
            'birth_date': '1995-05-15',
            'job_title': self.job_title.id,
        }
        form = EmployeeForm(data=form_data)
        # Check that job_title queryset contains our job
        self.assertIn(self.job_title, form.fields['job_title'].queryset)
    
    def test_employee_form_valid_data(self):
        form_data = {
            'name': 'Maria Santos',
            'cpf': '67134509206',
            'birth_date': '1992-03-20',
            'department': self.department.id,
            'job_title': self.job_title.id,
        }
        form = EmployeeForm(data=form_data)
        self.assertTrue(form.is_valid())
    
    def test_employee_form_missing_required_field(self):
        form_data = {
            'name': 'Maria Santos',
            # Missing cpf - required field
            'birth_date': '1992-03-20',
        }
        form = EmployeeForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('cpf', form.errors)
    
    def test_employee_create_duplicate_cpf(self):
        # Cria o primeiro
        Employee.objects.create(
            name='Original', 
            cpf='67134509206', 
            birth_date='1990-01-01',
            department=self.department,
            job_title=self.job_title
        )
        
        # Tenta criar o segundo com mesmo CPF via formulário
        form_data = {
            'name': 'Impostor',
            'cpf': '67134509206', # Mesmo CPF
            'birth_date': '1995-01-01',
            'department': self.department.id,
            'job_title': self.job_title.id,
        }
        form = EmployeeForm(data=form_data)
        
        self.assertFalse(form.is_valid())
        self.assertIn('cpf', form.errors) # Deve conter erro no campo CPF

class AuthenticationTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
    
    def test_dashboard_requires_login(self):
        # Unauthenticated user should be redirected
        response = self.client.get(reverse('rhcontrol:dashboard'))
        self.assertEqual(response.status_code, 302)  # Redirect
        self.assertTrue(response.url.startswith('/login'))
    
    def test_dashboard_accessible_when_logged_in(self):
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('rhcontrol:dashboard'))
        self.assertEqual(response.status_code, 200)
    
    def test_login_view_displays_form(self):
        response = self.client.get(reverse('rhcontrol:login'))
        self.assertEqual(response.status_code, 200)
        self.assertIn('form', response.context)

class EmployeeViewTests(TestCase):
    def _employee_payload_for_url(self, url, **overrides):
        get_resp = self.client.get(url)
        formset = get_resp.context['dependent_formset']
        prefix = formset.prefix

        data = {
            'name': 'Carlos Silva',
            'cpf': '67134509206',
            'birth_date': '1988-07-10',
            'department': self.department.id,
            'job_title': self.job_title.id,
            'current_salary': '4000.00',
            'hire_date': '2025-01-01',

            'registration_number': '12345',
            'mother_name': 'Mãe do Carlos',
            'birth_city': 'São Paulo',
            'gender': 'M',
            'marital_status': 'S',
            'ethnicity': 'Branca',
            'education_level': 'Superior Completo',
            'retirement_status': 'N',
            'address': 'Rua de Teste',
            'address_num': '123',
            'neighborhood': 'Bairro Teste',
            'city': 'São Paulo',
            'state_code': 'SP',
            'zip_code': '01234-567',
            'mobile_phone': '(11) 99999-9999',
            'workday_type': 'F - Jornada de semana fixa',

            'change_reason': 'Promoção',
            'change_date': '2025-01-01',
        }

        data.update(overrides)

        data.update({
            f'{prefix}-TOTAL_FORMS': str(formset.total_form_count()),
            f'{prefix}-INITIAL_FORMS': str(formset.initial_form_count()),
            f'{prefix}-MIN_NUM_FORMS': '0',
            f'{prefix}-MAX_NUM_FORMS': '1000',
        })

        return data

    def _valid_employee_form_data(self):
        return self._employee_payload_for_url(reverse('rhcontrol:employee_create'))

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='admin',
            password='admin123'
        )
        self.client.login(username='admin', password='admin123')
        
        self.department = Department.objects.create(name='Produção')
        self.job_title = JobTitle.objects.create(
            name='Operador',
            department=self.department,
            base_salary=2500.00
        )
    
    def test_employee_create_view(self):
        response = self.client.post(
            reverse('rhcontrol:employee_create'),
            self._valid_employee_form_data()
        )

        if response.status_code == 200:
            form = response.context['form']
            formset = response.context['dependent_formset']
            print("FORM ERRORS:", form.errors)
            print("FORMSET ERRORS:", formset.errors)
            print("FORMSET NON_FIELD_ERRORS:", formset.non_form_errors())

        self.assertEqual(response.status_code, 302)
        self.assertTrue(Employee.objects.filter(cpf='67134509206').exists())
    
    def test_employee_list_view(self):
        employee = Employee.objects.create(
            name='Ana Costa',
            cpf='99988877766',
            birth_date='1993-11-25',
            department=self.department,
            job_title=self.job_title
        )
        response = self.client.get(reverse('rhcontrol:employee_list'))
        self.assertEqual(response.status_code, 200)
        self.assertIn(employee, response.context['object_list'])
    
    def test_employee_update_view(self):
        employee = Employee.objects.create(
            name='Roberto Lima',
            cpf='67134509206',
            birth_date='1985-02-14',
            department=self.department,
            job_title=self.job_title
        )

        url = reverse('rhcontrol:employee_update', args=[employee.pk])

        data = self._employee_payload_for_url(
            url,
            name='Roberto Lima Atualizado',
            cpf=employee.cpf,
            birth_date='1985-02-14',
            department=self.department.id,
            job_title=self.job_title.id,
        )

        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 302)

        employee.refresh_from_db()
        self.assertEqual(employee.name, 'ROBERTO LIMA ATUALIZADO')
    
    def test_employee_delete_view(self):
        employee = Employee.objects.create(
            name='Lucia Ferreira',
            cpf='33344455566',
            birth_date='1991-09-30',
            department=self.department,
            job_title=self.job_title
        )
        response = self.client.post(
            reverse('rhcontrol:employee_delete', args=[employee.id])
        )
        self.assertFalse(Employee.objects.filter(id=employee.id).exists())

class EmployeeFilterTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='user', password='pass')
        self.client.login(username='user', password='pass')
        
        self.department = Department.objects.create(name='RH')
        self.job_title = JobTitle.objects.create(
            name='Analista',
            department=self.department,
            base_salary=4000.00
        )
        self.email='teste@gmail.com'
        
        # Create test employees
        self.employee1 = Employee.objects.create(
            name='João Silva',
            cpf='11111111111',
            birth_date='1990-01-01',
            email=self.email,
            department=self.department,
            job_title=self.job_title,
            termination_date=None  # Active
        )
        
        self.employee2 = Employee.objects.create(
            name='Maria Santos',
            cpf='22222222222',
            birth_date='1992-05-15',
            department=self.department,
            job_title=self.job_title,
            termination_date='2025-12-31'  # Terminated
        )
    
    def test_search_by_name(self):
        response = self.client.get(
            reverse('rhcontrol:employee_list'),
            {'search': 'João'}
        )
        self.assertIn(self.employee1, response.context['object_list'])
        self.assertNotIn(self.employee2, response.context['object_list'])
    
    def test_search_by_cpf(self):
        # employee1 cpf='11111111111'
        response = self.client.get(
            reverse('rhcontrol:employee_list'),
            {'search': '11111111111'}
        )
        self.assertIn(self.employee1, response.context['object_list'])
        self.assertNotIn(self.employee2, response.context['object_list'])

    def test_search_by_email(self):
        email_test='teste@gmail.com'
        self.employee1.email=email_test
        self.employee1.save()

        response = self.client.get(
            reverse('rhcontrol:employee_list'),
            {'search': self.email}
        )
        self.assertIn(self.employee1, response.context['object_list'])
    
    def test_filter_by_status_active(self):
        response = self.client.get(
            reverse('rhcontrol:employee_list'),
            {'status': 'ativo'}
        )
        self.assertIn(self.employee1, response.context['object_list'])
        self.assertNotIn(self.employee2, response.context['object_list'])
    
    def test_filter_by_status_terminated(self):
        response = self.client.get(
            reverse('rhcontrol:employee_list'),
            {'status': 'demitido'}
        )
        self.assertNotIn(self.employee1, response.context['object_list'])
        self.assertIn(self.employee2, response.context['object_list'])

class AjaxTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.department = Department.objects.create(name='TI')
        self.job1 = JobTitle.objects.create(
            name='Junior Developer',
            department=self.department,
            base_salary=3000.00
        )
        self.job2 = JobTitle.objects.create(
            name='Senior Developer',
            department=self.department,
            base_salary=6000.00
        )
    
    def test_load_job_titles(self):
        response = self.client.get(
            reverse('rhcontrol:ajax_load_job_titles'),
            {'department_id': self.department.id}
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data), 2)
        self.assertEqual(data[0]['name'], 'Junior Developer')
    
    def test_get_job_salary(self):
        response = self.client.get(
            reverse('rhcontrol:ajax_get_job_salary'),
            {'job_id': self.job1.id}
        )
        data = response.json()
        self.assertEqual(float(data['salary']), 3000.00)

class CipaStabilityTestes(TestCase):
    def setUp(self):

        self.dept = Department.objects.create(name="Setor de Testes")
        
        self.job = JobTitle.objects.create(
            name="Cargo de Teste",
            department=self.dept,
            base_salary=2000.00
        )

        self.employee = Employee.objects.create(
            name="Teste CIPA",
            cpf="12345678900", 
            birth_date="1990-01-01",
            department=self.dept, 
            job_title=self.job    
        )

    def test_cipa_active_mandate(self):
        today = timezone.now().date()
        
        self.employee.is_cipa_member = True
        self.employee.cipa_role = 'Titular'
        self.employee.cipa_mandate_start_date = today - timedelta(days=30)
        self.employee.cipa_mandate_end_date = today + timedelta(days=335)
        self.employee.save()

        self.assertEqual(self.employee.cipa_status, 'active')

    def test_cipa_stability_period(self):
        """Testa se o status é 'stability' logo após o fim do mandato"""
        today = timezone.now().date()
        
        self.employee.is_cipa_member = True
        self.employee.cipa_role = 'Titular'
        # Mandato acabou ontem
        self.employee.cipa_mandate_end_date = today - timedelta(days=1)
        self.employee.save()

        self.assertEqual(self.employee.cipa_status, 'stability')

    def test_cipa_stability_expired(self):
        today = timezone.now().date()
        
        self.employee.is_cipa_member = True
        self.employee.cipa_role = 'Titular'
        self.employee.cipa_mandate_end_date = today - timedelta(days=366)
        self.employee.save()

        self.assertIsNone(self.employee.cipa_status)

    def test_not_cipa_member(self):
        self.employee.is_cipa_member = False
        self.employee.save()
        self.assertIsNone(self.employee.cipa_status)

    def test_cipa_fields_cleared_after_stability(self):
        """
        Test if the fields (is_cipa_member, cipa_role, cipa_mandate_start_date, cipa_mandate_end_date) are cleared 
        after the total end of the period (mandate + stability).
        """
        today = timezone.now().date()
        
        self.employee.is_cipa_member = True
        self.employee.cipa_role = 'Titular'
        
        self.employee.cipa_mandate_end_date = today - timedelta(days=367)
        self.employee.save()

        self.employee.check_cipa_expiration()
        
        self.employee.refresh_from_db()

        self.assertFalse(self.employee.is_cipa_member)
        self.assertIsNone(self.employee.cipa_role)
        self.assertIsNone(self.employee.cipa_mandate_start_date)
        self.assertIsNone(self.employee.cipa_mandate_end_date)

class CareerPlanAutomationsTest(TestCase):
    def setUp(self):
        self.today = timezone.localdate()

        self.dept = Department.objects.create(
            name="TI"
        )
        self.current_job = JobTitle.objects.create(
            name="Desenvolvedor Júnior", 
            department=self.dept,
            base_salary=Decimal("4000.00")
        )
        self.proposed_job = JobTitle.objects.create(
            name="Desenvolvedor Pleno", 
            department=self.dept, 
            base_salary=Decimal("6000.00")
        )

        self.employee = Employee.objects.create(
            name="Teste ",
            cpf="67134509206",
            birth_date="1990-01-01",
            department=self.dept,
            job_title=self.current_job,
            current_salary=Decimal("4000.00"),
        )

        NotificationRule.objects.create(event_type=EventTypes.CAREER_PLAN_REMINDER, is_active=True, days_in_advance=0)
        NotificationRule.objects.create(event_type=EventTypes.CAREER_PLAN_EFFECTIVE, is_active=True, days_in_advance=0)

        NotificationRecipient.objects.create(
            name="RH Teste",
            email="rh@teste.com",
            is_active=True,
            receive_all_events=True
        )

    def test_reminder_email_sent_exactly_at_30_days_window(self):
        plan = CareerPlan.objects.create(
            employee=self.employee,
            proposed_job=self.proposed_job,
            proposed_salary=Decimal("6000.00"),
            promotion_date=self.today + timedelta(days=30),
            status=CareerPlan.PlanStatus.SCHEDULED
        )

        process_career_plans(dry_run=False)
        plan.refresh_from_db()

        self.assertEqual(plan.status, CareerPlan.PlanStatus.AWAITING_CONFIRMATION)
        self.assertIsNotNone(plan.reminder_sent_at)

        self.assertEqual(len(mail.outbox), 1)

    def test_promotion_applied_only_on_exact_date(self):
        plan = CareerPlan.objects.create(
            employee=self.employee,
            proposed_job=self.proposed_job,
            proposed_salary=Decimal("6000.00"),
            promotion_date=self.today + timedelta(days=1),
            status=CareerPlan.PlanStatus.CONFIRMED
        )

        process_career_plans(dry_run=False)
        plan.refresh_from_db()
        self.employee.refresh_from_db()

        self.assertEqual(plan.status, CareerPlan.PlanStatus.CONFIRMED)
        self.assertEqual(self.employee.job_title, self.current_job)
        self.assertEqual(len(mail.outbox), 0)

        plan.promotion_date = self.today
        plan.save(update_fields=["promotion_date"])

        process_career_plans(dry_run=False)
        plan.refresh_from_db()
        self.employee.refresh_from_db()

        self.assertEqual(plan.status, CareerPlan.PlanStatus.EFFECTIVE)
        self.assertEqual(self.employee.job_title, self.proposed_job)
        self.assertEqual(self.employee.current_salary, Decimal("6000.00"))
        self.assertEqual(len(mail.outbox), 1)

    # def test_conflict_aborts_promotion(self):
    #     plan = CareerPlan.objects.create(
    #         employee=self.employee,
    #         proposed_job=self.proposed_job,             
    #         proposed_salary=Decimal("6000.00"),
    #         promotion_date=self.today + timedelta(days=1),
    #         status=CareerPlan.PlanStatus.CONFIRMED,
    #     )

    #     new_dept = Department.objects.create(name="RH")
    #     self.employee.department = new_dept
    #     self.employee.save(update_fields=["department"])

    #     plan.promotion_date = self.today
    #     plan.save(update_fields=["promotion_date"])

    #     process_career_plans(dry_run=False)

    #     plan.refresh_from_db()
    #     self.employee.refresh_from_db()

    #     self.assertEqual(plan.status, CareerPlan.PlanStatus.CANCELLED)
    #     self.assertIn("Conflito", plan.cancellation_reason)
    #     self.assertEqual(self.employee.job_title, self.current_job)

class CareerPlanIdempotencyTests(TestCase):
    def setUp(self):
        self.today = timezone.localdate()

        self.dept = Department.objects.create(name="TI")
        self.current_job = JobTitle.objects.create(
            name="Dev Jr", department=self.dept, base_salary=Decimal("4000.00")
        )
        self.proposed_job = JobTitle.objects.create(
            name="Dev Pl", department=self.dept, base_salary=Decimal("6000.00")
        )

        self.employee = Employee.objects.create(
            name="Teste",
            cpf="67134509206",
            birth_date="1990-01-01",
            department=self.dept,
            job_title=self.current_job,
            current_salary=Decimal("4000.00"),
        )

        NotificationRule.objects.create(
            event_type=EventTypes.CAREER_PLAN_REMINDER, is_active=True, days_in_advance=0
        )
        NotificationRecipient.objects.create(
            name="RH", email="rh@teste.com", is_active=True, receive_all_events=True
        )

    def test_reminder_idempotent_no_duplicate_email_and_log(self):
        plan = CareerPlan.objects.create(
            employee=self.employee,
            proposed_job=self.proposed_job,
            proposed_salary=Decimal("6000.00"),
            promotion_date=self.today + timedelta(days=30),
            status=CareerPlan.PlanStatus.SCHEDULED
        )

        process_career_plans(dry_run=False)
        plan.refresh_from_db()
        self.assertEqual(plan.status, CareerPlan.PlanStatus.AWAITING_CONFIRMATION)
        self.assertIsNotNone(plan.reminder_sent_at)
        self.assertEqual(len(mail.outbox), 1)

        logs_count_1 = NotificationLog.objects.count()

        process_career_plans(dry_run=False)
        plan.refresh_from_db()
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(NotificationLog.objects.count(), logs_count_1)


class CareerPlanDryRunTests(TestCase):
    def setUp(self):
        self.today = timezone.localdate()

        self.dept = Department.objects.create(name="TI")
        self.current_job = JobTitle.objects.create(
            name="Dev Jr", department=self.dept, base_salary=Decimal("4000.00")
        )
        self.proposed_job = JobTitle.objects.create(
            name="Dev Pl", department=self.dept, base_salary=Decimal("6000.00")
        )

        self.employee = Employee.objects.create(
            name="Teste",
            cpf="67134509206",
            birth_date="1990-01-01",
            department=self.dept,
            job_title=self.current_job,
            current_salary=Decimal("4000.00"),
        )

        NotificationRule.objects.create(
            event_type=EventTypes.CAREER_PLAN_REMINDER, is_active=True, days_in_advance=0
        )
        NotificationRecipient.objects.create(
            name="RH", email="rh@teste.com", is_active=True, receive_all_events=True
        )

    def test_dry_run_does_not_send_or_change_state(self):
        """
        Tests that when process_career_plans is called with dry_run=True, 
        it does not send emails or change the state of the plan.

        """
        plan = CareerPlan.objects.create(
            employee=self.employee,
            proposed_job=self.proposed_job,
            proposed_salary=Decimal("6000.00"),
            promotion_date=self.today + timedelta(days=30),
            status=CareerPlan.PlanStatus.SCHEDULED
        )

        process_career_plans(dry_run=True)

        plan.refresh_from_db()
        self.assertEqual(plan.status, CareerPlan.PlanStatus.SCHEDULED)
        self.assertIsNone(plan.reminder_sent_at)
        self.assertEqual(len(mail.outbox), 0)
        self.assertEqual(NotificationLog.objects.count(), 0)

class CareerPlanExpiryTests(TestCase):
    def setUp(self):
        self.today = timezone.localdate()

        self.dept = Department.objects.create(name="TI")
        self.current_job = JobTitle.objects.create(
            name="Dev Jr", department=self.dept, base_salary=Decimal("4000.00")
        )
        self.proposed_job = JobTitle.objects.create(
            name="Dev Pl", department=self.dept, base_salary=Decimal("6000.00")
        )

        self.employee = Employee.objects.create(
            name="Teste",
            cpf="67134509206",
            birth_date="1990-01-01",
            department=self.dept,
            job_title=self.current_job,
            current_salary=Decimal("4000.00"),
        )

        NotificationRule.objects.create(
            event_type=EventTypes.CAREER_PLAN_CANCELLED, is_active=True, days_in_advance=0
        )
        NotificationRecipient.objects.create(
            name="RH", email="rh@teste.com", is_active=True, receive_all_events=True
        )

    class CareerPlanExpiryTests(TestCase):
        def setUp(self):
            self.today = timezone.localdate()

            self.dept = Department.objects.create(name="TI")
            self.current_job = JobTitle.objects.create(
                name="Dev Jr", department=self.dept, base_salary=Decimal("4000.00")
            )
            self.proposed_job = JobTitle.objects.create(
                name="Dev Pl", department=self.dept, base_salary=Decimal("6000.00")
            )

            self.employee = Employee.objects.create(
                name="Teste",
                cpf="67134509206",
                birth_date="1990-01-01",
                department=self.dept,
                job_title=self.current_job,
                current_salary=Decimal("4000.00"),
            )

            NotificationRule.objects.create(
                event_type=EventTypes.CAREER_PLAN_CANCELLED, is_active=True, days_in_advance=0
            )
            NotificationRecipient.objects.create(
                name="RH", email="rh@teste.com", is_active=True, receive_all_events=True
            )

    def test_awaiting_confirmation_expires_and_cancels_on_day_d(self):
        plan = CareerPlan.objects.create(
            employee=self.employee,
            proposed_job=self.proposed_job,
            proposed_salary=Decimal("6000.00"),
            promotion_date=self.today + timedelta(days=10),
            status=CareerPlan.PlanStatus.AWAITING_CONFIRMATION,
        )
        CareerPlan.objects.filter(pk=plan.pk).update(promotion_date=self.today)

        process_career_plans(dry_run=False)

        plan.refresh_from_db()
        self.assertEqual(plan.status, CareerPlan.PlanStatus.CANCELLED)
        self.assertIn("expir", (plan.cancellation_reason or "").lower())
        self.assertEqual(len(mail.outbox), 1)
    
class CareerPlanComaTests(TestCase):
    def setUp(self):
        self.today = timezone.localdate()

        self.dept = Department.objects.create(name="TI")
        self.current_job = JobTitle.objects.create(
            name="Dev Jr", department=self.dept, base_salary=Decimal("4000.00")
        )
        self.proposed_job = JobTitle.objects.create(
            name="Dev Pl", department=self.dept, base_salary=Decimal("6000.00")
        )

        self.employee = Employee.objects.create(
            name="Teste",
            cpf="67134509206",
            birth_date="1990-01-01",
            department=self.dept,
            job_title=self.current_job,
            current_salary=Decimal("4000.00"),
        )

        NotificationRule.objects.create(
            event_type=EventTypes.CAREER_PLAN_CANCELLED, is_active=True, days_in_advance=0
        )
        NotificationRecipient.objects.create(
            name="RH", email="rh@teste.com", is_active=True, receive_all_events=True
        )

    def test_scheduled_plan_with_past_promotion_date_is_cancelled(self):
        plan = CareerPlan.objects.create(
            employee=self.employee,
            proposed_job=self.proposed_job,
            proposed_salary=Decimal("6000.00"),
            promotion_date=self.today + timedelta(days=5),
            status=CareerPlan.PlanStatus.SCHEDULED,
        )
        CareerPlan.objects.filter(pk=plan.pk).update(promotion_date=self.today - timedelta(days=1))

        process_career_plans(dry_run=False)

        plan.refresh_from_db()
        self.assertEqual(plan.status, CareerPlan.PlanStatus.CANCELLED)
        self.assertIn("cron", (plan.cancellation_reason or "").lower())
        self.assertEqual(len(mail.outbox), 1)

class CareerPlanDismissalTests(TestCase):
    def setUp(self):
        self.today = timezone.localdate()

        self.dept = Department.objects.create(name="TI")
        self.current_job = JobTitle.objects.create(
            name="Dev Jr", department=self.dept, base_salary=Decimal("4000.00")
        )
        self.proposed_job = JobTitle.objects.create(
            name="Dev Pl", department=self.dept, base_salary=Decimal("6000.00")
        )

        self.employee = Employee.objects.create(
            name="Teste",
            cpf="67134509206",
            birth_date="1990-01-01",
            department=self.dept,
            job_title=self.current_job,
            current_salary=Decimal("4000.00"),
        )

        NotificationRule.objects.create(
            event_type=EventTypes.CAREER_PLAN_CANCELLED, is_active=True, days_in_advance=0
        )
        NotificationRecipient.objects.create(
            name="RH", email="rh@teste.com", is_active=True, receive_all_events=True
        )

    def test_dismissed_employee_cancels_active_plan(self):
        plan = CareerPlan.objects.create(
            employee=self.employee,
            proposed_job=self.proposed_job,
            proposed_salary=Decimal("6000.00"),
            promotion_date=self.today + timedelta(days=10),
            status=CareerPlan.PlanStatus.SCHEDULED,
        )

        self.employee.termination_date = self.today
        self.employee.save(update_fields=["termination_date"])

        process_career_plans(dry_run=False)

        plan.refresh_from_db()
        self.assertEqual(plan.status, CareerPlan.PlanStatus.CANCELLED)
        self.assertIn("desligado", (plan.cancellation_reason or "").lower())
        self.assertEqual(len(mail.outbox), 1)

class CareerPlanEffectiveTests(TestCase):
    def setUp(self):
        self.today = timezone.localdate()

        self.dept = Department.objects.create(name="TI")

        self.current_job = JobTitle.objects.create(
            name="Dev Jr",
            department=self.dept,
            base_salary=Decimal("4000.00")
        )

        self.proposed_job = JobTitle.objects.create(
            name="Dev Pl",
            department=self.dept,
            base_salary=Decimal("6000.00")
        )

        self.employee = Employee.objects.create(
            name="Teste",
            cpf="67134509206",
            birth_date="1990-01-01",
            department=self.dept,
            job_title=self.current_job,
            current_salary=Decimal("4000.00"),
        )

        NotificationRule.objects.create(
            event_type=EventTypes.CAREER_PLAN_EFFECTIVE,
            is_active=True,
            days_in_advance=0
        )

        NotificationRecipient.objects.create(
            name="RH",
            email="rh@teste.com",
            is_active=True,
            receive_all_events=True
        )

    def test_confirmed_plan_becomes_effective_and_updates_employee_on_day_d(self):
        plan = CareerPlan.objects.create(
            employee=self.employee,
            proposed_job=self.proposed_job,
            proposed_salary=Decimal("6000.00"),
            promotion_date=self.today + timedelta(days=5),
            status=CareerPlan.PlanStatus.CONFIRMED,
        )

        CareerPlan.objects.filter(pk=plan.pk).update(promotion_date=self.today)

        process_career_plans(dry_run=False)

        plan.refresh_from_db()
        self.employee.refresh_from_db()

        self.assertEqual(plan.status, CareerPlan.PlanStatus.EFFECTIVE)
        self.assertIsNotNone(plan.effective_applied_at)

        self.assertEqual(self.employee.job_title, self.proposed_job)
        self.assertEqual(self.employee.current_salary, Decimal("6000.00"))

        self.assertEqual(len(mail.outbox), 1)
        self.assertIn(self.employee.name, mail.outbox[0].subject)

        process_career_plans(dry_run=False)
        self.assertEqual(len(mail.outbox), 1)


class TrainingModelTests(TestCase):
    def setUp(self):
        self.department = Department.objects.create(name="Produção")
        self.job_title = JobTitle.objects.create(
            name="Operador",
            department=self.department,
            base_salary=2500.00
        )
        self.employee = Employee.objects.create(
            name="Funcionário Teste",
            cpf="67134509206",
            birth_date="1990-01-01",
            department=self.department,
            job_title=self.job_title
        )

    def _make_training(self, **kwargs):
        defaults = {
            "training_name": "NR-12 Segurança",
            "start_date": "2026-03-10",
            "training_total_hours": 8,
        }
        defaults.update(kwargs)
        return Training(**defaults)

    def test_training_str_is_correct(self):
        t = Training.objects.create(
            training_name="NR-10",
            start_date="2026-03-01",
            training_total_hours=4,
        )
        self.assertIn("NR-10", str(t))
        self.assertIn("2026-03-01", str(t))

    def test_end_date_before_start_date_raises_validation_error(self):
        from django.core.exceptions import ValidationError
        t = self._make_training(start_date="2026-03-10", end_date="2026-03-05")
        with self.assertRaises(ValidationError) as cm:
            t.full_clean()
        self.assertIn("end_date", cm.exception.message_dict)

    def test_end_date_equal_to_start_date_is_valid(self):
        from django.core.exceptions import ValidationError
        t = self._make_training(start_date="2026-03-10", end_date="2026-03-10")
        try:
            t.full_clean()
        except ValidationError as e:
            if "end_date" in e.message_dict:
                self.fail("ValidationError raised for equal start/end date: " + str(e))

    def test_end_date_after_start_date_is_valid(self):
        from django.core.exceptions import ValidationError
        t = self._make_training(start_date="2026-03-10", end_date="2026-03-20")
        try:
            t.full_clean()
        except ValidationError as e:
            if "end_date" in e.message_dict:
                self.fail("Unexpected end_date ValidationError: " + str(e))

    def test_total_hours_sum_uses_training_total_hours(self):
        t1 = Training.objects.create(
            training_name="NR-10", start_date="2026-03-01", training_total_hours=4
        )
        t2 = Training.objects.create(
            training_name="NR-12", start_date="2026-03-05", training_total_hours=8
        )
        t1.attended_employees.add(self.employee)
        t2.attended_employees.add(self.employee)

        attended = self.employee.attended_trainings.all()
        total = sum(t.training_total_hours or 0 for t in attended)
        self.assertEqual(total, 12)