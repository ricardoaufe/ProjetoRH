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

    #VACATIONS
    path('vacations/', views.vacation_view, name='vacation_list'),
    path('vacations/create/', views.vacation_create, name='vacation_create'),
    
    #TRAININGS
    path('trainings/', views.training_view, name='training_list'),
    path('trainings/create/', views.training_create, name='training_create'),
    path('trainings/<int:pk>/edit/', views.training_update, name='training_update'),

    #LOGIN
    path('login/', views.login_view, name='login'),
    path('login/create/', views.login_create, name='login_create'),
    path('logout/', views.logout_view, name='logout'),

    path('ajax/load-job-titles/', views.load_job_titles, name='ajax_load_job_titles'),
    path('ajax/get-job-salary/', views.get_job_salary, name='ajax_get_job_salary'),
]