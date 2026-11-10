import logging
from io import BytesIO

from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.utils.http import content_disposition_header
from django.utils.text import slugify
from openpyxl import Workbook
from openpyxl.styles import Font

from rhcontrol.attendance_sheet import (
    AttendanceTemplateError,
    build_attendance_sheet,
    build_on_the_job_sheet,
)
from rhcontrol.filters import filter_employees
from rhcontrol.models import Employee, Training

logger = logging.getLogger(__name__)

XLSX_CONTENT_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def render_xlsx(workbook, filename):
    """Salva a planilha em memória e devolve como download (.xlsx)."""
    buffer = BytesIO()
    workbook.save(buffer)

    response = HttpResponse(buffer.getvalue(), content_type=XLSX_CONTENT_TYPE)
    response["Content-Disposition"] = content_disposition_header(
        as_attachment=True, filename=filename
    )
    return response


@login_required
@permission_required("rhcontrol.view_employee", raise_exception=True)
def create_employee_list_xlsx(request):
    """
    Mesma lista (colunas e filtros) do PDF de funcionários, em Excel.
    A data de admissão vai como data de verdade, para o Excel ordenar e filtrar.
    """
    employees = filter_employees(
        Employee.objects.select_related("department", "job_title"), request.GET
    )

    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Funcionários"

    headers = ["Colaborador", "Data de Admissão", "Setor", "Cargo", "Status"]
    sheet.append(headers)
    for cell in sheet[1]:
        cell.font = Font(bold=True)

    for employee in employees:
        name = employee.name
        if employee.is_cipa_member:
            name += " (CIPA)"
        sheet.append([
            name,
            employee.hire_date,
            employee.department.name if employee.department else "-",
            employee.job_title.name if employee.job_title else "-",
            "INATIVO" if employee.termination_date else "ATIVO",
        ])

    for row in sheet.iter_rows(min_row=2, min_col=2, max_col=2):
        row[0].number_format = "DD/MM/YYYY"

    for column, width in zip("ABCDE", [40, 18, 25, 30, 12], strict=True):
        sheet.column_dimensions[column].width = width
    sheet.freeze_panes = "A2"
    sheet.auto_filter.ref = sheet.dimensions

    return render_xlsx(workbook, "lista_de_funcionarios.xlsx")


@login_required
@permission_required("rhcontrol.view_training", raise_exception=True)
def training_attendance_sheet(request, pk):
    """
    Lista de presença (Form40B) do treinamento, já com tema, objetivo, datas,
    local e os participantes previstos. O resto o RH completa no Excel.
    """
    training = get_object_or_404(Training, pk=pk)
    return _form40b_download(request, training, "Lista_presenca", lambda: build_attendance_sheet(training))


@login_required
@permission_required("rhcontrol.view_training", raise_exception=True)
def training_on_the_job_sheet(request, pk):
    """Ficha do On The Job (verso do Form40B), só para treinamentos On The Job."""
    training = get_object_or_404(Training, pk=pk)
    if not training.is_on_the_job:
        messages.error(request, "Este treinamento não está marcado como On The Job.")
        return redirect("rhcontrol:training_update", pk=pk)
    return _form40b_download(request, training, "On_the_job", build_on_the_job_sheet)


def _form40b_download(request, training, prefix, build):
    """Gera um arquivo do Form40B e devolve como download (ou avisa se o modelo falhar)."""
    try:
        content = build()
    except AttendanceTemplateError:
        logger.exception("Falha ao gerar o Form40B (%s) do treinamento %s", prefix, training.pk)
        messages.error(
            request,
            "Não foi possível gerar o arquivo: o modelo em Excel não foi encontrado "
            "ou está diferente do Form40B. Avise o responsável pelo sistema.",
        )
        return redirect("rhcontrol:training_update", pk=training.pk)

    day = training.start_date.strftime("%d-%m-%Y") if training.start_date else "sem-data"
    filename = f"{prefix}_{slugify(training.training_name) or 'treinamento'}_{day}.xlsx"
    response = HttpResponse(content, content_type=XLSX_CONTENT_TYPE)
    response["Content-Disposition"] = content_disposition_header(
        as_attachment=True, filename=filename
    )
    return response
