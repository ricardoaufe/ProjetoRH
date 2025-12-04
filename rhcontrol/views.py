from django.http import HttpResponse
from django.shortcuts import render
from rhcontrol.models import Employee, Vacation, Training
from django.db.models import Q 
from django.core.paginator import Paginator
from .forms import LoginForm

def login_view(request):
    form = LoginForm()
    return render(request, 'authors/pages/login.html', {
        'form': form,
        })

def login_create(request):
    form = LoginForm()
    return render(request, 'authors/pages/login.html', {
        'form': form,
        })

def dashboard(request):
    return render(request, 'dashboard/pages/dashboard.html')

def employees(request):
    return render(request, 'dashboard/pages/employee-list.html')

def employee_view(request):
    employee_list = Employee.objects.select_related('department').all()

    query = request.GET.get('search', '')
    if query:
        employee_list = employee_list.filter(
            Q(name_icontains=query) | 
            Q(cpf__icontains=query) |
            Q(rg__icontains=query)
        )
    
    status_filter = request.GET.get('status')
    if status_filter == 'ativo':
        employee_list = employee_list.filter(termination_date__isnull=True) 
    elif status_filter == 'demitido':
        employee_list = employee_list.filter(termination_date__isnull=False)

    sort_by = request.GET.get('sort', 'name')
    valid_sort_fields = ['name', 'cpf','department__name']
    if sort_by in valid_sort_fields:
        employee_list = employee_list.order_by(sort_by)
    else:
        employee_list = employee_list.order_by('name')

    paginator = Paginator(employee_list, 15)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'object_list': page_obj,
    }
    return render(request, 'dashboard/pages/employee-list.html', context)

def vacation_view(request):
    vacation_list = Vacation.objects.select_related('employee').all()

    paginator = Paginator(vacation_list, 15)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'object_list': page_obj,
    }
    return render(request, 'dashboard/pages/vacation-list.html', context)

def training_view(request):
    training_list = Training.objects.select_related('employee').all()
    paginator = Paginator(training_list, 15)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'object_list': page_obj,
    }
    return render(request, 'dashboard/pages/training-list.html', context)
    
    


