from pydoc import html
from django.conf import settings
from django.http import HttpResponse, Http404, JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from rhcontrol.models import Employee, EmployeeHistory, Vacation, Training, JobTitle, Department
from django.db.models import Q 
from django.core.paginator import Paginator
from rhcontrol.forms import DependentFormSet, LoginForm, UserUpdateForm, EmployeeForm, VacationForm, TrainingForm, DepartmentForm, JobTitleFormSet
from django.contrib.auth.forms import AuthenticationForm, PasswordChangeForm
from django.contrib.auth import login, authenticate, logout, update_session_auth_hash
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.contrib import messages 
from datetime import timedelta, timezone
from django.utils import timezone
from django.template.loader import render_to_string
from weasyprint import HTML

def login_view(request):
    
    if request.user.is_authenticated:
        return redirect('rhcontrol:dashboard') 

    form = LoginForm()
    
    return render(request, 'authors/pages/login.html', {
        'form': form,
        'form_action': reverse('rhcontrol:login_create'),
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
            return redirect('rhcontrol:dashboard')
        else:
            messages.error(request, 'Usuário ou senha incorretos.')
    else:
        messages.error(request, 'Erro de validação.')

    return render(request, 'authors/pages/login.html', {
        'form': form,
        'form_action': reverse('rhcontrol:login_create')
    })

@login_required
def logout_view(request):
    if request.method != 'POST':
        return redirect('rhcontrol:login')

    logout(request)
    return redirect('rhcontrol:login')
        
@login_required
def dashboard_view(request):

    employees_count = Employee.objects.count()
    vacations_count = Vacation.objects.count()

    context = {
        'employees_count': employees_count,
        'vacations_count': vacations_count,
    }

    return render(request, 'dashboard/pages/dashboard.html', context)

@login_required
def profile_view(request):
    if request.method == 'POST':
        form = UserUpdateForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Perfil atualizado com sucesso!')
            return redirect('rhcontrol:profile')
        else:
            messages.error(request, 'Erro ao atualizar perfil.')

    form = UserUpdateForm(instance=request.user)

    return render(request, 'authors/pages/profile.html', {
        'form': form,
        'title': 'Meu Perfil'
    })

@login_required
def change_password(request):
    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user) 
            messages.success(request, 'Sua senha foi alterada com sucesso!')
            return redirect('rhcontrol:profile')
        else:
            messages.error(request, 'Erro ao alterar a senha. Verifique os campos.')
    else:
        form = PasswordChangeForm(request.user)
        
    return render(request, 'authors/pages/password_change.html', {
        'form': form,
        'title': 'Alterar Senha'
    })

#Funcionários
@login_required
def employees(request):
    return render(request, 'dashboard/pages/employee/list.html')

@login_required
def employee_view(request):
    limit_date = timezone.now().date() - timedelta(days=366)
    
    expired_employees = Employee.objects.filter(
        is_cipa_member=True,
        cipa_mandate_end_date__lt=limit_date # Data fim MENOR que (Hoje - 366 dias)
    )
    
    for emp in expired_employees:
        emp.check_cipa_expiration()

    employee_list = Employee.objects.select_related('department').all()

    query = request.GET.get('search', '')
    if query:
        employee_list = employee_list.filter(
            Q(name__icontains=query) | 
            Q(cpf__icontains=query) |
            Q(email__icontains=query) |
            Q(department__name__icontains=query) |
            Q(mobile_phone__icontains=query)
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
    return render(request, 'dashboard/pages/employee/list.html', context)

@login_required
def employee_create(request):
    if request.method == 'POST':
        form = EmployeeForm(request.POST)
        formset = DependentFormSet(request.POST)
        
        if form.is_valid() and formset.is_valid():
            employee = form.save()

            formset.instance = employee
            formset.save()
            
            data_admissao = employee.hire_date if employee.hire_date else timezone.now().date()
            EmployeeHistory.objects.create(
                employee=employee,
                date_changed=data_admissao,
                old_job_title=None,    # Admissão não tem cargo anterior
                new_job_title=str(employee.job_title),
                old_salary=None,       # Admissão não tem salário anterior
                new_salary=employee.current_salary,
                reason="Admissão"      # Motivo fixo
            )

            messages.success(request, 'Funcionário cadastrado com sucesso!')
            return redirect('rhcontrol:employee_list') 
        else:
            messages.error(request, 'Erro ao cadastrar. Verifique os campos abaixo.')
    
    else:
        form = EmployeeForm()
        formset = DependentFormSet()
    return render(request, 'dashboard/pages/employee/form.html', {
        'form': form,
        'dependent_formset': formset,
        'title': 'Cadastrar Funcionário'
    })

@login_required
def employee_update(request, pk):
    employee = get_object_or_404(Employee, pk=pk)

    # 1. Snapshots (Guardar estado anterior)
    old_job = employee.job_title
    old_salary = employee.current_salary
    old_cipa_role = employee.cipa_role 

    form = EmployeeForm(request.POST or None, instance=employee)
    formset = DependentFormSet(request.POST or None, instance=employee)

    if form.is_valid() and formset.is_valid():
        new_employee = form.save(commit=False)

        # Lógica Automática: Calcula Fim do Mandato (1 ano) se não preenchido
        if new_employee.is_cipa_member and new_employee.cipa_mandate_start_date and not new_employee.cipa_mandate_end_date:
            new_employee.cipa_mandate_end_date = new_employee.cipa_mandate_start_date + timedelta(days=365)

        new_employee.save()
        formset.save()
        
        # 2. Detecção de Mudanças
        has_job_change = str(old_job) != str(new_employee.job_title)
        has_salary_change = old_salary != new_employee.current_salary
        has_cipa_change = old_cipa_role != new_employee.cipa_role
        
        if has_job_change or has_salary_change or has_cipa_change:
            custom_date = form.cleaned_data.get('change_date')
            custom_reason = form.cleaned_data.get('change_reason')
            
            # --- CORREÇÃO DA DATA ---
            # Prioridade: 1. Data Personalizada (Se digitou) -> 2. Início do Mandato (Se for CIPA) -> 3. Hoje
            final_date = timezone.now()
            
            if custom_date:
                final_date = custom_date
            elif has_cipa_change and new_employee.cipa_mandate_start_date:
                # Se mudou a CIPA, a data do histórico DEVE ser o início do mandato
                final_date = new_employee.cipa_mandate_start_date

            # Lógica do Motivo
            auto_reason = ""
            if custom_reason:
                auto_reason = custom_reason
            elif has_cipa_change:
                if new_employee.is_cipa_member and new_employee.cipa_role:
                    auto_reason = f"CIPA: {new_employee.cipa_role}"
                else:
                    auto_reason = "Fim de CIPA"
            elif has_job_change:
                auto_reason = "Promoção"
            elif has_salary_change:
                if new_employee.current_salary > old_salary:
                    auto_reason = "Mérito"
                else:
                    auto_reason = "Reajuste"

            # --- CORREÇÃO DA SUJEIRA NO HISTÓRICO ---
            # Só preenchemos os campos no histórico se eles realmente mudaram.
            # Se não mudaram, passamos None, e o template vai esconder automaticamente.

            h_old_job = str(old_job) if (old_job and has_job_change) else None
            h_new_job = str(new_employee.job_title) if has_job_change else None
            
            h_old_salary = old_salary if has_salary_change else None
            h_new_salary = new_employee.current_salary if has_salary_change else None

            EmployeeHistory.objects.create(
                employee=employee,
                date_changed=final_date,
                
                # Campos limpos (só salva se mudou)
                old_job_title=h_old_job,
                new_job_title=h_new_job,
                old_salary=h_old_salary,
                new_salary=h_new_salary,
                
                old_cipa_role=old_cipa_role,
                new_cipa_role=new_employee.cipa_role,
                
                reason=auto_reason
            )

        messages.success(request, 'Funcionário atualizado com sucesso!')
        return redirect('rhcontrol:employee_list')
    
    # Contexto para renderização (Mantido igual)
    scheduled = employee.scheduled_trainings.all()
    attended = employee.attended_trainings.all().order_by('-training_date')
    history_log = employee.history.all().order_by('-date_changed')
    vacations = employee.vacations.all().order_by('-start_date')
    total_hours = sum(t.training_duration for t in scheduled | attended)

    return render(request, 'dashboard/pages/employee/form.html', {
        'form': form,
        'dependent_formset': formset,
        'title': 'Editar Funcionário',
        'history_enabled': True,
        'trainings': attended.distinct().order_by('-training_date'),
        'history_log': history_log,
        'vacations': vacations,
        'total_hours': total_hours
    })

@login_required
def delete_history_log(request, pk):
    log = get_object_or_404(EmployeeHistory, pk=pk)
    employee_id = log.employee.pk # Guarda o ID pra voltar pra página certa
    log.delete()
    messages.success(request, 'Registro de histórico removido.')
    
    # Redireciona de volta para a edição do funcionário
    return redirect('rhcontrol:employee_update', pk=employee_id)

@login_required
def employee_delete(request, pk):
    employee = get_object_or_404(Employee, pk=pk)

    if request.method == 'POST':
        employee.delete()
        messages.success(request, 'Funcionário excluído com sucesso!')
        return redirect('rhcontrol:employee_list')

    return render(request, 'dashboard/pages/employee/delete.html', {
        'employee': employee
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

#VACATIONS
@login_required
def vacation_view(request):
    vacation_list = Vacation.objects.select_related('employee').all()

    paginator = Paginator(vacation_list, 5)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'object_list': page_obj,
    }
    return render(request, 'dashboard/pages/vacation/list.html', context)

@login_required
def vacation_create(request):
    if request.method == 'POST':
        form = VacationForm(request.POST)
        
        if form.is_valid():
            employee = form.cleaned_data['employee']
            start_date = form.cleaned_data['start_date']
            duration = form.cleaned_data['vacation_duration']
        
            end_date = start_date + timedelta(days=duration - 1)

            return_date = end_date + timedelta(days=1)

            while return_date.weekday() >= 5:
                return_date += timedelta(days=1)

            Vacation.objects.create(
                employee=employee,
                start_date=start_date,
                end_date=end_date,               
                vacation_duration=duration,      
                return_date=return_date          
            )

            messages.success(request, 'Férias cadastradas com sucesso!')
            return redirect('rhcontrol:vacation_list') 
        else:
            messages.error(request, 'Erro ao cadastrar. Verifique os campos abaixo.')
    
    else:
        form = VacationForm()

    return render(request, 'dashboard/pages/vacation/form.html', {
        'form': form,
        'title': 'Cadastrar Férias'
    })

@login_required
def vacation_update(request, pk):
    vacation = get_object_or_404(Vacation, pk=pk)
    form = VacationForm(request.POST or None, instance=vacation)

    if form.is_valid():
        form.save()
        messages.success(request, 'Férias atualizadas com sucesso!')
        return redirect('rhcontrol:vacation_list')

    return render(request, 'dashboard/pages/vacation/form.html', {
        'form': form,
        'title': 'Editar Férias'
    })

@login_required
def vacation_delete(request, pk):
    vacation = get_object_or_404(Vacation, pk=pk)

    if request.method == 'POST':
        vacation.delete()
        messages.success(request, 'Férias excluídas com sucesso!')
        return redirect('rhcontrol:vacation_list')

    return render(request, 'dashboard/pages/vacation/delete.html', {
        'vacation': vacation
    })

#TRAINING
@login_required
def training_view(request):
    training_list = Training.objects.all().order_by('-training_date')
    paginator = Paginator(training_list, 15)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'object_list': page_obj,
    }
    return render(request, 'dashboard/pages/training/list.html', context)

@login_required
def training_create(request):
    if request.method == 'POST':
        form = TrainingForm(request.POST)
        if form.is_valid():
            training = form.save(commit=False)
            training.save() 
            
            is_fundamental = form.cleaned_data.get('is_fundamental')
            all_depts = form.cleaned_data.get('all_departments')
            target_dept = form.cleaned_data.get('target_department')

            if is_fundamental:
                if all_depts:
                    employees_to_add = Employee.objects.filter(termination_date__isnull=True)
                elif target_dept:
                    employees_to_add = Employee.objects.filter(department=target_dept, termination_date__isnull=True)
                else:
                    employees_to_add = []

                training.scheduled_employees.set(employees_to_add)
                training.attended_employees.set(employees_to_add)
            
            else:
                form.save_m2m() 

            messages.success(request, 'Treinamento criado com sucesso!')
            return redirect('rhcontrol:training_list')
    else:
        form = TrainingForm()
    
    return render(request, 'dashboard/pages/training/form.html', {'form': form})

@login_required
def training_update(request, pk):
    training = get_object_or_404(Training, pk=pk)
    form = TrainingForm(request.POST or None, instance=training)

    if form.is_valid():
        form.save()
        messages.success(request, 'Treinamento atualizado com sucesso!')
        return redirect('rhcontrol:training_list')

    return render(request, 'dashboard/pages/training/form.html', {
        'form': form,
        'title': 'Editar Treinamento'
    })    

@login_required
def training_delete(request, pk):
    training = get_object_or_404(Training, pk=pk)

    if request.method == 'POST':
        training.delete()
        messages.success(request, 'Treinamento excluído com sucesso!')
        return redirect('rhcontrol:training_list')

    return render(request, 'dashboard/pages/training/delete.html', {
        'training': training
    })

@login_required
def department_list(request):
    departments = Department.objects.all().order_by('name') 
    
    context = {
        'object_list': departments, 
        'title': 'Lista de Setores'
    }
    
    return render(request, 'dashboard/pages/departments/list.html', context)

@login_required
def department_create(request):
    if request.method == 'POST':
        form = DepartmentForm(request.POST)
        formset = JobTitleFormSet(request.POST)

        if form.is_valid() and formset.is_valid():
            department = form.save()
            formset.instance = department 
            formset.save()

            messages.success(request, 'Setor criado com sucesso!')
            return redirect('rhcontrol:department_list')
    else:
        form = DepartmentForm()
        formset = JobTitleFormSet()

    return render(request, 'dashboard/pages/departments/form.html', {
        'form': form,
        'formset': formset,
        'title': 'Cadastrar Setores'
    })

@login_required
def department_update(request, pk):
    department = get_object_or_404(Department, pk=pk)

    if request.method == 'POST':
        form = DepartmentForm(request.POST or None, instance=department)
        formset = JobTitleFormSet(request.POST or None, instance=department)

        if form.is_valid() and formset.is_valid():
            form.save()
            formset.save()
            messages.success(request, 'Setor atualizado com sucesso!')
            return redirect('rhcontrol:department_list')

    else:
        form = DepartmentForm(instance=department)
        formset = JobTitleFormSet(instance=department)

    return render(request, 'dashboard/pages/departments/form.html', {
        'form': form,
        'formset': formset,
        'title': 'Editar Setor'
    })    

@login_required
def department_delete(request, pk):
    department = get_object_or_404(Department, pk=pk)

    if request.method == 'POST':
        department.delete()
        messages.success(request, 'Setor excluído com sucesso!')
        return redirect('rhcontrol:department_list')

    return render(request, 'dashboard/pages/departments/delete.html', {
        'department': department
    })

# ========= PDFs =========
@login_required
def create_employee_list_pdf(request):
    employee_list = Employee.objects.select_related('department').all()
    
    query = request.GET.get('search', '')
    if query:
        employee_list = employee_list.filter(
            Q(name__icontains=query) | 
            Q(cpf__icontains=query) | 
            Q(email__icontains=query)
        )
    
    status_filter = request.GET.get('status', 'todos')
    if status_filter == 'ativo':
        employee_list = employee_list.filter(termination_date__isnull=True)
    elif status_filter == 'demitido':
        employee_list = employee_list.filter(termination_date__isnull=False)
    
    sort_by = request.GET.get('sort', 'name')
    valid_sort_fields = ['name', 'cpf', 'department__name']
    
    if sort_by in valid_sort_fields:
        employee_list = employee_list.order_by(sort_by)
    else:
        employee_list = employee_list.order_by('name')

    context = {
        'employees': employee_list,
        'status_filter': status_filter,
        'query': query,
        'generated_at': timezone.now(),
        'user': request.user,
        'company_name_settings': settings.COMPANY_NAME,
    }
    
    html_string = render_to_string('dashboard/pages/employee/pdf/list.html', context)
    
    html = HTML(string=html_string, base_url=request.build_absolute_uri())
    
    pdf = html.write_pdf()
    
    response = HttpResponse(pdf, content_type='application/pdf')
    response['Content-Disposition'] = 'inline; filename="lista_de_funcionarios.pdf"'
    return response 

@login_required
def create_employee_registration_pdf(request, pk):
    employee = get_object_or_404(Employee, pk=pk)
    
    context = {
        'employee': employee,
        'user': request.user,
        'generated_at': timezone.now(),
        'company_name_settings': settings.COMPANY_NAME,
    }
    
    html_string = render_to_string('dashboard/pages/employee/pdf/registration_form.html', context, request=request)
    
    html = HTML(string=html_string, base_url=request.build_absolute_uri())
    pdf = html.write_pdf()
    
    response = HttpResponse(pdf, content_type='application/pdf')
    
    safe_name = employee.name.replace(' ', '_')
    filename = f"ficha_cadastral_{employee.id}_{safe_name}.pdf"
    response['Content-Disposition'] = f'inline; filename="{filename}"'
    
    return response

@login_required
def create_confidenciality_pdf(request, pk):
    employee = get_object_or_404(Employee, pk=pk)
    context = {'employee': employee,
               'user': request.user,
               'generated_at': timezone.now(),
               'company_name_settings': settings.COMPANY_NAME,
               }

    html_string = render_to_string('dashboard/pages/employee/pdf/confidentiality_term.html', context, request=request)
    html = HTML(string=html_string, base_url=request.build_absolute_uri())
    pdf = html.write_pdf()

    response = HttpResponse(pdf, content_type='application/pdf')

    safe_name = employee.name.replace(' ', '_')
    filename = f"termo_de_confidencialidade_{employee.id}_{safe_name}.pdf"
    response['Content-Disposition'] = f'inline; filename="{filename}"'
    
    return response

@login_required
def create_bank_presentation_pdf(request, pk):
    employee = get_object_or_404(Employee, pk=pk)
    context = {'employee': employee,
               'user': request.user,
               'generated_at': timezone.now(),
               'company_name_settings': settings.COMPANY_NAME,
               }

    html_string = render_to_string('dashboard/pages/employee/pdf/bank_presentation.html', context, request=request)
    html = HTML(string=html_string, base_url=request.build_absolute_uri())
    pdf = html.write_pdf()

    response = HttpResponse(pdf, content_type='application/pdf')

    safe_name = employee.name.replace(' ', '_')
    filename = f"apresentacao_bancaria_{employee.id}_{safe_name}.pdf"
    response['Content-Disposition'] = f'inline; filename="{filename}"'
    
    return response

@login_required
def create_personal_data_consent_pdf(request, pk):
    employee = get_object_or_404(Employee, pk=pk)
    context = {
        'employee': employee,
        'user': request.user,
        'generated_at': timezone.now(),
        'company_name_settings': settings.COMPANY_NAME,
    }

    html_string = render_to_string('dashboard/pages/employee/pdf/personal_data_consent.html', context, request=request)
    html = HTML(string=html_string, base_url=request.build_absolute_uri())
    pdf = html.write_pdf()

    response = HttpResponse(pdf, content_type='application/pdf')

    safe_name = employee.name.replace(' ', '_')
    filename = f"termo_de_compromisso_{employee.id}_{safe_name}.pdf"
    response['Content-Disposition'] = f'inline; filename="{filename}"'
    
    return response

@login_required
def create_commitment_term_pdf(request, pk):
    employee = get_object_or_404(Employee, pk=pk)
    context = {
        'employee': employee,
        'user': request.user,
        'generated_at': timezone.now(),
        'company_name_settings': settings.COMPANY_NAME,
    }

    html_string = render_to_string('dashboard/pages/employee/pdf/commitment_term.html', context, request=request)
    html = HTML(string=html_string, base_url=request.build_absolute_uri())
    pdf = html.write_pdf()

    response = HttpResponse(pdf, content_type='application/pdf')

    safe_name = employee.name.replace(' ', '_')
    filename = f"termo_de_compromisso_{employee.id}_{safe_name}.pdf"
    response['Content-Disposition'] = f'inline; filename="{filename}"'
    
    return response

@login_required
def create_image_consent_pdf(request, pk):
    employee = get_object_or_404(Employee, pk=pk)
    context = {
        'employee': employee,
        'user': request.user,
        'generated_at': timezone.now(),
        'company_name_settings': settings.COMPANY_NAME,
    }

    html_string = render_to_string('dashboard/pages/employee/pdf/image_consent.html', context, request=request)
    html = HTML(string=html_string, base_url=request.build_absolute_uri())
    pdf = html.write_pdf()

    response = HttpResponse(pdf, content_type='application/pdf')

    safe_name = employee.name.replace(' ', '_')
    filename = f"termo_de_consentimento_uso_imagem_{employee.id}_{safe_name}.pdf"
    response['Content-Disposition'] = f'inline; filename="{filename}"'
    
    return response

@login_required
def create_benefits_acquisition_pdf(request, pk):
    employee = get_object_or_404(Employee, pk=pk)
    context = {
        'employee': employee,
        'user': request.user,
        'generated_at': timezone.now(),
        'company_name_settings': settings.COMPANY_NAME,
    }

    html_string = render_to_string('dashboard/pages/employee/pdf/benefits_acquisition.html', context, request=request)
    html = HTML(string=html_string, base_url=request.build_absolute_uri())
    pdf = html.write_pdf()

    response = HttpResponse(pdf, content_type='application/pdf')

    safe_name = employee.name.replace(' ', '_')
    filename = f"termo_de_aquisicao_beneficios_{employee.id}_{safe_name}.pdf"
    response['Content-Disposition'] = f'inline; filename="{filename}"'
    
    return response

@login_required
def create_internal_regulation_pdf(request, pk):
    employee = get_object_or_404(Employee, pk=pk)
    context = {
        'employee': employee,
        'user': request.user,
        'generated_at': timezone.now(),
        'company_name_settings': settings.COMPANY_NAME,
    }

    html_string = render_to_string('dashboard/pages/employee/pdf/internal_regulation.html', context, request=request)
    html = HTML(string=html_string, base_url=request.build_absolute_uri())
    pdf = html.write_pdf()

    response = HttpResponse(pdf, content_type='application/pdf')

    safe_name = employee.name.replace(' ', '_')
    filename = f"regimento_interno_{employee.id}_{safe_name}.pdf"
    response['Content-Disposition'] = f'inline; filename="{filename}"'
    
    return response