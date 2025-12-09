"""
URL configuration for rh project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
from rhcontrol import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.dashboard_view, name='dashboard'),

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

    #LOGIN
    path('login/', views.login_view, name='login'),
    path('login/create/', views.login_create, name='login_create'),
    path('logout/', views.logout_view, name='logout'),

    path('ajax/load-job-titles/', views.load_job_titles, name='ajax_load_job_titles'),
    path('ajax/get-job-salary/', views.get_job_salary, name='ajax_get_job_salary'),
]
