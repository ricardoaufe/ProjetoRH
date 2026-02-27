from django.urls import path
from django.contrib import admin

from . import views

app_name = 'rhcontrol'
urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.dashboard_view, name='dashboard'),
    path('profile/', views.profile_view, name='profile'),
    path('profile/password/', views.change_password, name='change_password'),

    #EMPLOYEES
    path('employees/', views.employee_view, name='employee_list'),
    path('employees/create/', views.employee_create, name='employee_create'),
    path('employees/<int:pk>/edit/', views.employee_update, name='employee_update'),
    path('employees/<int:pk>/delete/', views.employee_delete, name='employee_delete'),
    path('employee/history/delete/<int:pk>/', views.delete_history_log, name='history_delete'),

    #CAREER PLAN
    path('ajax/load-employee-data/', views.ajax_load_employee_data, name='ajax_load_employee_data'),
    path('ajax/load-jobs-by-department/', views.ajax_load_jobs_by_department, name='ajax_load_jobs_by_department'),
    path('career/', views.career_plan_list, name='career_plan_list'),
    path('career/create/', views.career_plan_create, name='career_plan_create'),
    path('career/<int:pk>/edit/', views.career_plan_update, name='career_plan_update'),
    path('career-de-carreira/<int:pk>/confirm/', views.confirm_career_plan_action, name='career_plan_confirm'),
    path('career/<int:pk>/cancel/', views.cancel_career_plan, name='career_plan_cancel'),
    path('career/<int:pk>/delete/', views.career_plan_delete, name='career_plan_delete'),

    #VACATIONS
    path('vacations/', views.vacation_view, name='vacation_list'),
    path('vacations/create/', views.vacation_create, name='vacation_create'),
    path('vacations/<int:pk>/edit/', views.vacation_update, name='vacation_update'),
    path('vacations/<int:pk>/delete/', views.vacation_delete, name='vacation_delete'),
    
    #TRAININGS
    path('trainings/', views.training_view, name='training_list'),
    path('trainings/create/', views.training_create, name='training_create'),
    path('trainings/<int:pk>/edit/', views.training_update, name='training_update'),
    path('trainings/<int:pk>/delete/', views.training_delete, name='training_delete'),

    #DEPARTMENTS
    path('departments/', views.department_list, name='department_list'),
    path('departments/create/', views.department_create, name='department_create'),
    path('departments/<int:pk>/edit/', views.department_update, name='department_update'),
    path('departments/<int:pk>/delete/', views.department_delete, name='department_delete'),

    #LOGIN
    path('login/', views.login_view, name='login'),
    path('login/create/', views.login_create, name='login_create'),
    path('logout/', views.logout_view, name='logout'),

    path('ajax/load-job-titles/', views.load_job_titles, name='ajax_load_job_titles'),
    path('ajax/get-job-salary/', views.get_job_salary, name='ajax_get_job_salary'),

    #PDFs
    path('employees/pdf/', views.create_employee_list_pdf, name='employee_list_pdf'),
    path('employees/<int:pk>/registration-form/', views.create_employee_registration_pdf, name='employee_registration_pdf'),
    path('employees/<int:pk>/confidenciality-term/', views.create_confidenciality_pdf, name='confidenciality_term_pdf'),
    path('employees/<int:pk>/bank-presentation/', views.create_bank_presentation_pdf, name='bank_presentation_pdf'),
    path('employees/<int:pk>/personal-data-consent/', views.create_personal_data_consent_pdf, name='personal_data_consent_pdf'),
    path('employees/<int:pk>/term-of-commitment/', views.create_commitment_term_pdf, name='term_of_commitment_pdf'),
    path('employees/<int:pk>/term-of-consent/', views.create_image_consent_pdf, name='term_of_consent_pdf'),
    path('employees/<int:pk>/benefits-acquisition/', views.create_benefits_acquisition_pdf, name='benefits_acquisition_pdf'),
    path('employees/<int:pk>/internal-regulation/', views.create_internal_regulation_pdf, name='internal_regulation_pdf'),
    path('departments/pdf/department-and-jobtitles/', views.create_department_and_jobtitle_pdf, name='department_and_jobtitles_pdf'),
    path('departments/pdf/employees-department/', views.create_employees_department_pdf, name='employees_department_pdf'),
    path('vacation/pdf/', views.create_vacation_list_pdf, name='vacation_list_pdf'),
]