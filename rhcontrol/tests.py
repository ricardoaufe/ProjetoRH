from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from rhcontrol.models import Employee, JobTitle, Training, Vacation, Department
from rhcontrol.forms import EmployeeForm
from datetime import datetime, timedelta

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
            'cpf': '11122233344',
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
            cpf='11122233344', 
            birth_date='1990-01-01',
            department=self.department,
            job_title=self.job_title
        )
        
        # Tenta criar o segundo com mesmo CPF via formulário
        form_data = {
            'name': 'Impostor',
            'cpf': '11122233344', # Mesmo CPF
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
        form_data = {
            'name': 'Carlos Silva',
            'cpf': '55566677788',
            'birth_date': '1988-07-10',
            'department': self.department.id,
            'job_title': self.job_title.id,
        }
        response = self.client.post(
            reverse('rhcontrol:employee_create'),
            form_data
        )
        # Should redirect after successful creation
        self.assertEqual(response.status_code, 302)
        # Employee should exist in database
        self.assertTrue(Employee.objects.filter(cpf='55566677788').exists())
    
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
            cpf='44433322211',
            birth_date='1985-02-14',
            department=self.department,
            job_title=self.job_title
        )
        form_data = {
            'name': 'Roberto Lima Atualizado',
            'cpf': '44433322211',
            'birth_date': '1985-02-14',
            'department': self.department.id,
            'job_title': self.job_title.id,
        }
        response = self.client.post(
            reverse('rhcontrol:employee_update', args=[employee.id]),
            form_data
        )
        employee.refresh_from_db()
        self.assertEqual(employee.name, 'Roberto Lima Atualizado')
    
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