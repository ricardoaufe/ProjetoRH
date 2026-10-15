from pathlib import Path
from urllib.parse import unquote, urlsplit

from django.conf import settings
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.staticfiles import finders
from django.db.models import Count, Prefetch
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.http import content_disposition_header
from weasyprint import HTML, URLFetcher

from rhcontrol.filters import (
    filter_employees,
    filter_occurrences,
    filter_trainings,
    filter_vacations,
)
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

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class StaticFileFetcher(URLFetcher):
    """
    Lê do disco os arquivos de /static/ (fontes e imagens dos PDFs).

    Sem isso o WeasyPrint baixa cada um por HTTP do próprio servidor; nos
    testes o endereço é "testserver", que não existe, e cada tentativa leva
    segundos até falhar. Arquivo de /static/ que não está no disco também
    não existiria por HTTP, então falha na hora (o PDF sai sem ele, como
    antes). O que não for de /static/ segue pelo HTTP.
    """

    def fetch(self, url, headers=None):
        path = unquote(urlsplit(url).path)
        if not path.startswith(settings.STATIC_URL):
            return super().fetch(url, headers)

        relative = path[len(settings.STATIC_URL):]
        if '..' not in relative:
            # finders acha em dev/testes; STATIC_ROOT é onde o collectstatic copia.
            file_path = finders.find(relative) or Path(settings.STATIC_ROOT) / relative
            if Path(file_path).is_file():
                return super().fetch(Path(file_path).resolve().as_uri())
        raise FileNotFoundError(f'Arquivo estático não encontrado: {path}')


def render_pdf(request, template_name, context, filename):
    """
    Renderiza um template HTML como PDF (WeasyPrint) e devolve a resposta.

    - Passa o request para o template: assim os context processors rodam e
      o rodapé do base_pdf.html recebe os dados da empresa (company_*).
    - Content-Disposition é montado pelo Django, que trata acentos e
      caracteres especiais no nome do arquivo.
    """
    context = {
        "user": request.user,
        "generated_at": timezone.now(),
        **context,
    }
    html_string = render_to_string(template_name, context, request=request)
    pdf = HTML(
        string=html_string,
        base_url=request.build_absolute_uri(),
        url_fetcher=StaticFileFetcher(),
    ).write_pdf()

    response = HttpResponse(pdf, content_type="application/pdf")
    response["Content-Disposition"] = content_disposition_header(
        as_attachment=False, filename=filename
    )
    return response


def _employee_filename(prefix, employee):
    return f"{prefix}_{employee.id}_{employee.name.replace(' ', '_')}.pdf"


def _employee_document_pdf(request, pk, template_name, filename_prefix):
    """Documentos individuais do funcionário (termos, ficha, regimento...)."""
    employee = get_object_or_404(Employee, pk=pk)
    return render_pdf(
        request,
        f"dashboard/pages/employee/pdf/{template_name}",
        {"employee": employee},
        _employee_filename(filename_prefix, employee),
    )


def _format_brl(value):
    """1234.5 -> '1.234,50'"""
    return f"{value:,.2f}".replace(".", "X").replace(",", ".").replace("X", ",")


def _insalubrity_columns(base_salary, year, is_administrative):
    """
    Adicional de insalubridade (20% do salário mínimo vigente no ano) e o total.
    Setores administrativos não recebem: as colunas ficam vazias (None).
    """
    if is_administrative:
        return None, None
    insalubrity = get_historical_minimum_wage(year) * 0.20
    return _format_brl(insalubrity), _format_brl(base_salary + insalubrity)


# ---------------------------------------------------------------------------
# Documentos do funcionário
# ---------------------------------------------------------------------------


@login_required
@permission_required("rhcontrol.view_employee", raise_exception=True)
def create_employee_registration_pdf(request, pk):
    return _employee_document_pdf(
        request, pk, "registration_form.html", "ficha_cadastral"
    )


@login_required
@permission_required("rhcontrol.view_employee", raise_exception=True)
def create_confidenciality_pdf(request, pk):
    return _employee_document_pdf(
        request, pk, "confidentiality_term.html", "termo_de_confidencialidade"
    )


@login_required
@permission_required("rhcontrol.view_employee", raise_exception=True)
def create_bank_presentation_pdf(request, pk):
    return _employee_document_pdf(
        request, pk, "bank_presentation.html", "apresentacao_bancaria"
    )


@login_required
@permission_required("rhcontrol.view_employee", raise_exception=True)
def create_personal_data_consent_pdf(request, pk):
    return _employee_document_pdf(
        request,
        pk,
        "personal_data_consent.html",
        "termo_de_consentimento_dados_pessoais",
    )


@login_required
@permission_required("rhcontrol.view_employee", raise_exception=True)
def create_commitment_term_pdf(request, pk):
    return _employee_document_pdf(
        request, pk, "commitment_term.html", "termo_de_compromisso"
    )


@login_required
@permission_required("rhcontrol.view_employee", raise_exception=True)
def create_responsible_term_pdf(request, pk):
    return _employee_document_pdf(
        request,
        pk,
        "responsability_term.html",
        "termo_de_ciencia_e_responsabilidade_ti",
    )


@login_required
@permission_required("rhcontrol.view_employee", raise_exception=True)
def create_image_consent_pdf(request, pk):
    return _employee_document_pdf(
        request, pk, "image_consent.html", "termo_de_consentimento_uso_imagem"
    )


@login_required
@permission_required("rhcontrol.view_employee", raise_exception=True)
def create_benefits_acquisition_pdf(request, pk):
    return _employee_document_pdf(
        request, pk, "benefits_acquisition.html", "termo_de_aquisicao_beneficios"
    )


@login_required
@permission_required("rhcontrol.view_employee", raise_exception=True)
def create_internal_regulation_pdf(request, pk):
    return _employee_document_pdf(
        request, pk, "internal_regulation.html", "regimento_interno"
    )


# ---------------------------------------------------------------------------
# Relatórios (listas)
# ---------------------------------------------------------------------------


@login_required
@permission_required("rhcontrol.view_employee", raise_exception=True)
def create_employee_list_pdf(request):
    return render_pdf(
        request,
        "dashboard/pages/employee/pdf/list.html",
        {
            "employees": filter_employees(
                Employee.objects.select_related("department", "job_title"), request.GET
            ),
            "status_filter": request.GET.get("status", "todos"),
            "query": request.GET.get("search", ""),
        },
        "lista_de_funcionarios.pdf",
    )


@login_required
@permission_required("rhcontrol.view_department", raise_exception=True)
def create_department_and_jobtitle_pdf(request):
    ordened_jobtitles = JobTitle.objects.order_by("base_salary")
    departments = Department.objects.prefetch_related(
        Prefetch("job_titles", queryset=ordened_jobtitles)
    ).order_by("name")

    return render_pdf(
        request,
        "dashboard/pages/departments/pdf/department_and_jobtitle.html",
        {
            "object_list": departments,
            "title": "Lista de Setores e Cargos",
        },
        "setores_e_cargos.pdf",
    )


@login_required
@permission_required("rhcontrol.view_employee", raise_exception=True)
def create_employees_department_pdf(request):
    ordened_employees = Employee.objects.select_related("job_title").order_by(
        "job_title__base_salary", "name"
    )

    departments = (
        Department.objects.filter(funcionarios_setor__isnull=False)
        .distinct()
        .prefetch_related(Prefetch("funcionarios_setor", queryset=ordened_employees))
        .order_by("name")
    )

    return render_pdf(
        request,
        "dashboard/pages/departments/pdf/employees_department.html",
        {
            "object_list": departments,
            "total_employees": Employee.objects.count(),
        },
        "funcionarios_por_setor.pdf",
    )


@login_required
@permission_required("rhcontrol.view_vacation", raise_exception=True)
def create_vacation_list_pdf(request):
    vacation_list = filter_vacations(
        Vacation.objects.select_related("employee").order_by("start_date"), request.GET
    )
    return render_pdf(
        request,
        "dashboard/pages/vacation/pdf/vacation_list.html",
        {
            "vacation": vacation_list,
            "search_query": request.GET.get("search", ""),
            "date_from": request.GET.get("date_from", ""),
            "date_to": request.GET.get("date_to", ""),
            "status_filter": request.GET.get("status", "ativas"),
        },
        "lista_de_ferias.pdf",
    )


@login_required
@permission_required("rhcontrol.view_training", raise_exception=True)
def create_training_list_pdf(request):
    training_list = filter_trainings(
        Training.objects.annotate(
            num_attended=Count("attended_employees", distinct=True),
            num_scheduled=Count("scheduled_employees", distinct=True),
        ),
        request.GET,
    )
    return render_pdf(
        request,
        "dashboard/pages/training/pdf/training_list_pdf.html",
        {
            "trainings": training_list,
            "status_filter": request.GET.get("status") or "todos",
            "query": request.GET.get("search", ""),
            "date_from": request.GET.get("date_from", ""),
            "date_to": request.GET.get("date_to", ""),
        },
        "lista_de_treinamentos.pdf",
    )


@login_required
@permission_required("rhcontrol.view_occurrence", raise_exception=True)
def create_occurrence_list_pdf(request, employee_id):
    """
    GET employees/<employee_id>/occurrences/pdf/
    Gera um relatório em PDF de todas as ocorrências do funcionário,
    respeitando os filtros ativos na URL.
    """
    employee = get_object_or_404(Employee, pk=employee_id)
    occurrences = filter_occurrences(
        Occurrence.objects.filter(employee=employee).select_related("created_by"),
        request.GET,
    )
    return render_pdf(
        request,
        "dashboard/pages/occurrence/pdf/occurrence_list_pdf.html",
        {
            "occurrences": occurrences,
            "employee": employee,
            "search_query": request.GET.get("search", "").strip(),
            "date_from": request.GET.get("date_from"),
            "date_to": request.GET.get("date_to"),
        },
        f"Ocorrencias_{employee.name.replace(' ', '_')}.pdf",
    )


# ---------------------------------------------------------------------------
# Plano de carreira
# ---------------------------------------------------------------------------

ADMINISTRATIVE_KEYWORDS = ["ADMINISTRATIVO", "ADMINISTRAÇÃO", "ADM", "ADMINISTRACAO"]


@login_required
@permission_required("rhcontrol.view_careerplan", raise_exception=True)
def employee_career_plan_pdf(request, pk):
    employee = get_object_or_404(Employee, pk=pk)

    is_adm = False
    if employee.department:
        dept_name = employee.department.name.upper().strip()
        is_adm = any(keyword in dept_name for keyword in ADMINISTRATIVE_KEYWORDS)

    table_data = []

    history_records = EmployeeHistory.objects.filter(
        employee=employee, reason__in=["Admissão", "Promoção", "Mérito", "Dissídio"]
    ).order_by("date_changed")

    for h in history_records:
        base_salary = float(h.new_salary or h.old_salary or employee.current_salary or 0)
        row_job_title = h.new_job_title or h.old_job_title or employee.job_title.name
        insalubrity_str, total_str = _insalubrity_columns(base_salary, h.date_changed.year, is_adm)

        table_data.append({
            "year": h.date_changed.year,
            "date": h.date_changed,
            "salary": base_salary,
            "insalubrity": insalubrity_str,
            "total": total_str,
            "job_title": row_job_title,
            "is_future": False,
        })

    active_plans = (
        employee.career_plans.filter(
            status__in=["SCHEDULED", "AWAITING_CONFIRMATION", "CONFIRMED"]
        )
        .select_related("proposed_job")
        .order_by("promotion_date")
    )

    for plan in active_plans:
        base_salary = float(plan.proposed_salary or 0)
        insalubrity_str, total_str = _insalubrity_columns(base_salary, plan.promotion_date.year, is_adm)

        table_data.append({
            "year": plan.promotion_date.year,
            "date": plan.promotion_date,
            "salary": base_salary,
            "insalubrity": insalubrity_str,
            "total": total_str,
            "job_title": plan.proposed_job.name,
            "is_future": True,
        })

    return render_pdf(
        request,
        "dashboard/pages/career/pdf/career_plan_pdf.html",
        {
            "employee": employee,
            "table_data": table_data,
            "is_administrative": is_adm,
        },
        f"Plano_Carreira_{employee.name.replace(' ', '_')}.pdf",
    )
