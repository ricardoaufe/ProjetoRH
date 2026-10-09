from datetime import date, timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from rhcontrol.forms import DependentFormSet, EmployeeForm, EmployeeHistoryForm
from rhcontrol.models import Employee, EmployeeHistory, JobTitle


@permission_required('rhcontrol.view_employee', raise_exception=True)
@login_required
def employees(request):
    return render(request, 'dashboard/pages/employee/list.html')

@permission_required('rhcontrol.view_employee', raise_exception=True)
@login_required
def employee_view(request):
    limit_date = timezone.now().date() - timedelta(days=366)
    
    expired_employees = Employee.objects.filter(
        is_cipa_member=True,
        cipa_mandate_end_date__lt=limit_date
    )
    
    for emp in expired_employees:
        emp.check_cipa_expiration()

    employee_list = Employee.objects.select_related('department').all().order_by('name')

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
    
    # CORREÇÃO: Alterado de 'ativo' para 'active' para bater com o HTML
    if status_filter == 'active':
        employee_list = employee_list.filter(termination_date__isnull=True) 
    elif status_filter == 'demitido':
        employee_list = employee_list.filter(termination_date__isnull=False)

    sort_by = request.GET.get('sort', 'name')
    valid_sort_fields = ['name', 'cpf','department__name']
    if sort_by in valid_sort_fields:
        employee_list = employee_list.order_by(sort_by)
    else:
        employee_list = employee_list.order_by('name')

    paginator = Paginator(employee_list, 40)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'object_list': page_obj,
    }
    return render(request, 'dashboard/pages/employee/list.html', context)

@permission_required('rhcontrol.add_employee', raise_exception=True)
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
                old_job_title=None,    
                new_job_title=str(employee.job_title),
                old_salary=None,       
                new_salary=employee.current_salary,
                reason="Admissão"      
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

@permission_required('rhcontrol.change_employee', raise_exception=True)
@login_required
def employee_update(request, pk):
    employee = get_object_or_404(Employee, pk=pk)

    old_job = employee.job_title
    old_salary = employee.current_salary
    old_cipa_role = employee.cipa_role 
    job_titles = JobTitle.objects.all()

    form = EmployeeForm(request.POST or None, instance=employee)
    formset = DependentFormSet(request.POST or None, instance=employee)

    if form.is_valid() and formset.is_valid():
        new_employee = form.save(commit=False)

        if new_employee.is_cipa_member and new_employee.cipa_mandate_start_date and not new_employee.cipa_mandate_end_date:
            new_employee.cipa_mandate_end_date = new_employee.cipa_mandate_start_date + timedelta(days=365)

        new_employee.save()
        form.save_m2m()
        formset.save()

        has_job_change = str(old_job) != str(new_employee.job_title)
        has_salary_change = old_salary != new_employee.current_salary
        has_cipa_change = old_cipa_role != new_employee.cipa_role
        
        if has_job_change or has_salary_change or has_cipa_change:
            custom_date = form.cleaned_data.get('change_date')
            custom_reason = form.cleaned_data.get('change_reason')

            final_date = timezone.now()
            
            if custom_date:
                final_date = custom_date
            elif has_cipa_change and new_employee.cipa_mandate_start_date:
                final_date = new_employee.cipa_mandate_start_date

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

            h_old_job = old_job.name if (old_job and has_job_change) else None
            h_new_job = new_employee.job_title.name if (new_employee.job_title and has_job_change) else None
            
            h_old_salary = old_salary if has_salary_change else None
            h_new_salary = new_employee.current_salary if has_salary_change else None

            EmployeeHistory.objects.create(
                employee=employee,
                date_changed=final_date,

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

    scheduled = employee.scheduled_trainings.all()
    attended = employee.attended_trainings.all().order_by('-start_date')
    history_log = employee.history.all().order_by('-date_changed')
    total_hours = sum(t.training_total_hours or 0 for t in attended)

    today = timezone.localdate()
    vacations = employee.vacations.filter(start_date__lte=today)
    absences = employee.occurrences.filter(is_absence=True)

    leaves_history = []

    for v in vacations:
        leaves_history.append({
            'type': 'Férias',
            'start_date': v.start_date,
            'end_date': v.end_date,
            'duration': getattr(v, 'vacation_duration', 0),
            'icon': '🏖️',
            'border_color': '#20c997' 
        })

    for a in absences:
        leaves_history.append({
            'type': 'Afastamento',
            'title': a.title,
            'start_date': a.occurrence_date,
            'end_date': a.end_date,
            'duration': getattr(a, 'absence_duration', 0),
            'border_color': '#dc3545' 
        })

    leaves_history.sort(key=lambda x: x['start_date'], reverse=True)

    occurrences_top5 = (
        employee.occurrences
        .order_by('-occurrence_date', '-created_at')[:5]
    )
    is_rh_admin = request.user.groups.filter(name='RhAdmin').exists()

    return render(request, 'dashboard/pages/employee/form.html', {
        'form': form,
        'dependent_formset': formset,
        'title': 'Editar Funcionário',
        'history_enabled': True,
        'trainings': attended.distinct().order_by('-start_date'),
        'history_log': history_log,
        'leaves_history': leaves_history,
        'total_hours': total_hours,
        'occurrences_top5': occurrences_top5,
        'is_rh_admin': is_rh_admin,
        'job_titles': job_titles,
    })

@login_required
@permission_required('rhcontrol.change_employee', raise_exception=True)
def history_create_view(request, employee_id):
    employee = get_object_or_404(Employee, pk=employee_id)
    if request.method == 'POST':
        form = EmployeeHistoryForm(request.POST)
        
        # Trava: Não permite datas no futuro
        data_input = request.POST.get('date_changed')
        if data_input:
            try:
                parsed_date = date.fromisoformat(data_input)
                if parsed_date > timezone.localdate():
                    messages.error(request, 'Não é possível registrar históricos no futuro.')
                    return redirect('rhcontrol:employee_update', pk=employee_id)
            except ValueError:
                messages.error(request, 'Formato de data inválido.')
                return redirect('rhcontrol:employee_update', pk=employee_id)

        if form.is_valid():
            history = form.save(commit=False)
            history.employee = employee
            history.save()
            messages.success(request, 'Registro de histórico adicionado com sucesso.')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"Erro em {field}: {error}")
                    
    return redirect('rhcontrol:employee_update', pk=employee_id)

@login_required
@permission_required('rhcontrol.change_employee', raise_exception=True)
def history_edit_view(request, pk):
    history = get_object_or_404(EmployeeHistory, pk=pk)
    employee_id = history.employee.id
    if request.method == 'POST':
        
        data_input = request.POST.get('date_changed')
        if data_input:
            try:
                parsed_date = date.fromisoformat(data_input)
                if parsed_date > timezone.localdate():
                    messages.error(request, 'A data do histórico não pode ser no futuro.')
                    return redirect('rhcontrol:employee_update', pk=employee_id)
            except ValueError:
                messages.error(request, 'Formato de data inválido.')
                return redirect('rhcontrol:employee_update', pk=employee_id)

        form = EmployeeHistoryForm(request.POST, instance=history)
        if form.is_valid():
            form.save()
            messages.success(request, 'Registro de histórico atualizado.')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"Erro em {field}: {error}")
                    
    return redirect('rhcontrol:employee_update', pk=employee_id)

@login_required
@permission_required('rhcontrol.change_employee', raise_exception=True)
@require_POST
def delete_history_log(request, pk):
    log = get_object_or_404(EmployeeHistory, pk=pk)
    employee_id = log.employee.pk # Guarda o ID pra voltar pra página certa
    log.delete()
    messages.success(request, 'Registro de histórico removido.')
    
    # Redireciona de volta para a edição do funcionário
    return redirect('rhcontrol:employee_update', pk=employee_id)

@permission_required('rhcontrol.delete_employee', raise_exception=True)
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

@login_required
@permission_required('rhcontrol.view_employee', raise_exception=True)
def ajax_load_employee_data(request):
    employee_id = request.GET.get('employee_id')
    if employee_id:
        try:
            employee = Employee.objects.get(id=employee_id)
            department = employee.department
            
            return JsonResponse({
                'success': True,
                'department_name': department.name if department else 'Nenhum',
                'department_id': department.id if department else '', # IMPORTANTE PARA A CASCATA
                'current_job_name': employee.job_title.name if employee.job_title else 'Nenhum',
                'current_salary': str(employee.current_salary) if employee.current_salary else '0.00',
            })
        except Employee.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Funcionário não encontrado'})
            
    return JsonResponse({'success': False, 'error': 'ID não fornecido'})