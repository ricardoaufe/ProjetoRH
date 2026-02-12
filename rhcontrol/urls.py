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
    path('employees/<int:pk>/image-consent/', views.create_image_consent_pdf, name='image_consent_pdf'),
]