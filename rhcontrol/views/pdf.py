from django.conf import settings
from django.contrib.auth.decorators import login_required, permission_required
from django.db.models import Count, Prefetch
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.template.loader import render_to_string
from django.utils import timezone
from weasyprint import HTML

from rhcontrol.filters import filter_employees, filter_occurrences, filter_trainings, filter_vacations
from rhcontrol.models import (
    Department,
    Employee,
    EmployeeHistory,
    JobTitle,
    Occurrence,
    Training,
    Vacation,
)
from rhcontrol.services import get_historical_minimum_wage


@login_required
@permission_required('rhcontrol.view_employee', raise_exception=True)
def create_employee_list_pdf(request):
    employee_list = filter_employees(Employee.objects.select_related('department'), request.GET)
    query = request.GET.get('search', '')
    status_filter = request.GET.get('status', 'todos')

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
@permission_required('rhcontrol.view_employee', raise_exception=True)
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
@permission_required('rhcontrol.view_employee', raise_exception=True)
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
@permission_required('rhcontrol.view_employee', raise_exception=True)
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
@permission_required('rhcontrol.view_employee', raise_exception=True)
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
@permission_required('rhcontrol.view_employee', raise_exception=True)
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
@permission_required('rhcontrol.view_employee', raise_exception=True)
def create_responsible_term_pdf(request, pk):
    employee = get_object_or_404(Employee, pk=pk)
    context = {
        'employee': employee,
        'user': request.user,
        'generated_at': timezone.now(),
        'company_name_settings': settings.COMPANY_NAME,
        'company_city': settings.COMPANY_CITY,
    }

    html_string = render_to_string('dashboard/pages/employee/pdf/responsability_term.html', context, request=request)
    html = HTML(string=html_string, base_url=request.build_absolute_uri())
    pdf = html.write_pdf()

    response = HttpResponse(pdf, content_type='application/pdf')

    safe_name = employee.name.replace(' ', '_')
    filename = f"termo_de_ciencia_e_responsabilidade_ti_{employee.id}_{safe_name}.pdf"
    response['Content-Disposition'] = f'inline; filename="{filename}"'

    return response

@login_required
@permission_required('rhcontrol.view_employee', raise_exception=True)
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
@permission_required('rhcontrol.view_employee', raise_exception=True)
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
@permission_required('rhcontrol.view_employee', raise_exception=True)
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

@login_required
@permission_required('rhcontrol.view_department', raise_exception=True)
def create_department_and_jobtitle_pdf(request):
    ordened_jobtitles = JobTitle.objects.order_by('base_salary')
    departments = Department.objects.prefetch_related(
        Prefetch('job_titles', queryset=ordened_jobtitles)
    ).order_by('name')

    context = {
        'object_list': departments,
        'title': 'Lista de Setores e Cargos',
        'user': request.user,
        'generated_at': timezone.now(),
        'company_name_settings': settings.COMPANY_NAME,
    }

    html_string = render_to_string('dashboard/pages/departments/pdf/department_and_jobtitle.html', context, request=request)
    html = HTML(string=html_string, base_url=request.build_absolute_uri())
    pdf = html.write_pdf()

    response = HttpResponse(pdf, content_type='application/pdf')

    safe_name = "setores_e_cargos"
    filename = f"regimento_interno_de_{safe_name}.pdf"
    response['Content-Disposition'] = f'inline; filename="{filename}"'

    return response

@login_required
@permission_required('rhcontrol.view_employee', raise_exception=True)
def create_employees_department_pdf(request):
    ordened_employees = Employee.objects.select_related('job_title').order_by('job_title__base_salary', 'name')

    departments = Department.objects.filter(
        funcionarios_setor__isnull=False
    ).distinct().prefetch_related(
        Prefetch('funcionarios_setor', queryset=ordened_employees)
    ).order_by('name')

    total_employees = Employee.objects.count()

    context = {
        'object_list': departments,
        'total_employees': total_employees,
        'user': request.user,
        'generated_at': timezone.now(),
        'company_name_settings': settings.COMPANY_NAME,
    }

    html_string = render_to_string('dashboard/pages/departments/pdf/employees_department.html', context, request=request)
    html = HTML(string=html_string, base_url=request.build_absolute_uri())
    pdf = html.write_pdf()

    response = HttpResponse(pdf, content_type='application/pdf')

    filename = "funcionarios_por_setor.pdf"
    response['Content-Disposition'] = f'inline; filename="{filename}"'

    return response

@login_required
@permission_required('rhcontrol.view_vacation', raise_exception=True)
def create_vacation_list_pdf(request):
    vacation_list = filter_vacations(
        Vacation.objects.select_related('employee').order_by('start_date'), request.GET
    )
    status_filter = request.GET.get('status', 'ativas')
    search_query = request.GET.get('search', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')

    context = {
        'vacation': vacation_list,
        'search_query': search_query,
        'date_from': date_from,
        'date_to': date_to,
        'status_filter': status_filter,
        'generated_at': timezone.now(),
        'user': request.user,
        'company_name_settings': settings.COMPANY_NAME,
    }

    html_string = render_to_string('dashboard/pages/vacation/pdf/vacation_list.html', context, request=request)
    html = HTML(string=html_string, base_url=request.build_absolute_uri())
    pdf = html.write_pdf()

    response = HttpResponse(pdf, content_type='application/pdf')
    response['Content-Disposition'] = 'inline; filename="lista_de_ferias.pdf"'

    return response

@login_required
@permission_required('rhcontrol.view_training', raise_exception=True)
def create_training_list_pdf(request):
    training_list = filter_trainings(
        Training.objects.annotate(
            num_attended=Count('attended_employees', distinct=True),
            num_scheduled=Count('scheduled_employees', distinct=True),
        ),
        request.GET,
    )
    query = request.GET.get('search', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    status_filter = request.GET.get('status') or 'todos'

    context = {
        'trainings': training_list,
        'status_filter': status_filter,
        'query': query,
        'date_from': date_from,
        'date_to': date_to,
        'generated_at': timezone.now(),
        'user': request.user,
        'company_name_settings': settings.COMPANY_NAME,
    }

    html_string = render_to_string('dashboard/pages/training/pdf/training_list_pdf.html', context)
    html = HTML(string=html_string, base_url=request.build_absolute_uri())
    pdf = html.write_pdf()
    
    response = HttpResponse(pdf, content_type='application/pdf')
    response['Content-Disposition'] = 'inline; filename="lista_de_treinamentos.pdf"'

    return response

@login_required
@permission_required('rhcontrol.view_occurrence', raise_exception=True)
def create_occurrence_list_pdf(request, employee_id):
    """
    GET employees/<employee_id>/occurrences/pdf/
    Gera um relatório em PDF de todas as ocorrências do funcionário,
    respeitando os filtros ativos na URL.
    """
    employee = get_object_or_404(Employee, pk=employee_id)

    queryset = filter_occurrences(
        Occurrence.objects.filter(employee=employee).select_related('created_by'), request.GET
    )
    search_query = request.GET.get('search', '').strip()
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')

    context = {
        'occurrences': queryset,
        'employee': employee,
        'search_query': search_query,
        'date_from': date_from,
        'date_to': date_to,
        'generated_at': timezone.now(),
        'user': request.user,
        'company_name_settings': settings.COMPANY_NAME,
    }

    html_string = render_to_string('dashboard/pages/occurrence/pdf/occurrence_list_pdf.html', context)
    html = HTML(string=html_string, base_url=request.build_absolute_uri())
    pdf = html.write_pdf()
    
    response = HttpResponse(pdf, content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="Ocorrencias_{employee.name.replace(" ", "_")}.pdf"'
    
    return response

@login_required

@permission_required('rhcontrol.view_careerplan', raise_exception=True)
def employee_career_plan_pdf(request, pk):
    employee = get_object_or_404(Employee, pk=pk)

    is_adm = False
    if employee.department:
        dept_name = employee.department.name.upper().strip()
        palavras_chave_adm = ["ADMINISTRATIVO", "ADMINISTRAÇÃO", "ADM", "ADMINISTRACAO"]
        
        if any(palavra in dept_name for palavra in palavras_chave_adm):
            is_adm = True

    table_data = []

    history_records = EmployeeHistory.objects.filter(
        employee=employee,
        reason__in=['Admissão', 'Promoção', 'Mérito', 'Dissídio']
    ).order_by('date_changed')

    for h in history_records:
        salario_base = float(h.new_salary or h.old_salary or employee.current_salary or 0)
        cargo_linha = h.new_job_title if h.new_job_title else (h.old_job_title if h.old_job_title else employee.job_title.name)

        insalub_str = None
        total_str = None

        if not is_adm:
            ano = h.date_changed.year
            minimo_vigente = get_historical_minimum_wage(ano)
            valor_insalubridade = minimo_vigente * 0.20
            valor_total = salario_base + valor_insalubridade
            insalub_str = f"{valor_insalubridade:,.2f}".replace('.', 'X').replace(',', '.').replace('X', ',')
            total_str = f"{valor_total:,.2f}".replace('.', 'X').replace(',', '.').replace('X', ',')

        table_data.append({
            'ano': h.date_changed.year,
            'data': h.date_changed,
            'salario': salario_base,
            'insalub': insalub_str,
            'v_total': total_str,
            'funcao': cargo_linha,
            'is_future': False
        })

    if hasattr(employee, 'career_plans'):
        active_plans = employee.career_plans.filter(
            status__in=['SCHEDULED', 'AWAITING_CONFIRMATION', 'CONFIRMED']
        ).order_by('promotion_date')
        
        for plan in active_plans:
            salario_base = float(plan.proposed_salary or 0)
            insalub_str = None
            total_str = None

            if not is_adm:
                ano = plan.promotion_date.year
                minimo_vigente = get_historical_minimum_wage(ano)
                valor_insalubridade = minimo_vigente * 0.20
                valor_total = salario_base + valor_insalubridade
                insalub_str = f"{valor_insalubridade:,.2f}".replace('.', 'X').replace(',', '.').replace('X', ',')
                total_str = f"{valor_total:,.2f}".replace('.', 'X').replace(',', '.').replace('X', ',')

            table_data.append({
                'ano': plan.promotion_date.year,
                'data': plan.promotion_date,
                'salario': salario_base,
                'insalub': insalub_str,
                'v_total': total_str,
                'funcao': plan.proposed_job.name if hasattr(plan.proposed_job, 'name') else plan.proposed_job,
                'is_future': True
            })

    context = {
        'employee': employee,
        'table_data': table_data,
        'is_administrative': is_adm,
        'user': request.user,
    }
    
    html_string = render_to_string('dashboard/pages/career/pdf/career_plan_pdf.html', context, request=request)
    html = HTML(string=html_string, base_url=request.build_absolute_uri())
    pdf = html.write_pdf()
    
    response = HttpResponse(pdf, content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="Plano_Carreira_{employee.name.replace(" ", "_")}.pdf"'
    
    return response