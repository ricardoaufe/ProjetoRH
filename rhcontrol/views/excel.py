from io import BytesIO

from django.contrib.auth.decorators import login_required, permission_required
from django.http import HttpResponse
from django.utils.http import content_disposition_header
from openpyxl import Workbook
from openpyxl.styles import Font

from rhcontrol.filters import filter_employees
from rhcontrol.models import Employee

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
