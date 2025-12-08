from django.http import HttpResponse, Http404, JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from rhcontrol.models import Employee, Vacation, Training, JobTitle
from django.db.models import Q 
from django.core.paginator import Paginator
from .forms import LoginForm, EmployeeForm
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.contrib import messages 

def login_view(request):
    
    if request.user.is_authenticated:
        return redirect('dashboard') 

    form = LoginForm()
    
    return render(request, 'authors/pages/login.html', {
        'form': form,
        'form_action': reverse('login_create'),
    })

def login_create(request):
    if request.method != 'POST':
        raise Http404()

    form = LoginForm(request.POST)

    if form.is_valid():
        login_input = form.cleaned_data.get('email', '').strip()
        password = form.cleaned_data.get('password', '')

        user = authenticate(request, username=login_input, password=password)

        if user is None:
            try:
                user_obj = User.objects.filter(email__iexact=login_input).first()
                if user_obj:
                    user = authenticate(request, username=user_obj.username, password=password)
            except:
                pass

        if user is not None:
            messages.success(request, 'Logado com sucesso!')
            login(request, user)
            return redirect('dashboard')
        else:
            messages.error(request, 'Usuário ou senha incorretos.')
    else:
        messages.error(request, 'Erro de validação.')

    return render(request, 'authors/pages/login.html', {
        'form': form,
        'form_action': reverse('login_create')
    })

@login_required
def logout_view(request):
    if request.method != 'POST':
        return redirect('login')

    logout(request)
    return redirect('login')
        
@login_required
def dashboard_view(request):
    return render(request, 'dashboard/pages/dashboard.html')

#Funcionários
@login_required
def employees(request):
    return render(request, 'dashboard/pages/employee-list.html')

@login_required
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

@login_required
def employee_create(request):
    if request.method == 'POST':
        form = EmployeeForm(request.POST)
        
        if form.is_valid():
            form.save()
            messages.success(request, 'Funcionário cadastrado com sucesso!')
            return redirect('employee_list') 
        else:
            messages.error(request, 'Erro ao cadastrar. Verifique os campos abaixo.')
    
    else:
        form = EmployeeForm()

    return render(request, 'dashboard/pages/employee-form.html', {
        'form': form,
        'title': 'Cadastrar Funcionário'
    })

def load_job_titles(request):
    department_id = request.GET.get('department_id')

    if not department_id:
        return JsonResponse([], safe=False)

    jobs = JobTitle.objects.filter(department_id=department_id).order_by('name')

    return JsonResponse(list(jobs.values('id', 'name', 'base_salary')), safe=False)

def get_job_salary(request):
    job_id = request.GET.get('job_id')
    
    if not job_id:
        return JsonResponse({'salary': 0})

    job = get_object_or_404(JobTitle, pk=job_id)

    return JsonResponse({'salary': job.base_salary})

#Férias
def vacation_view(request):
    vacation_list = Vacation.objects.select_related('employee').all()

    paginator = Paginator(vacation_list, 5)
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
    
    


