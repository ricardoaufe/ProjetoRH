"""
Lista de presença (Form40B Rev.18) preenchida a partir do modelo em Excel.

O arquivo é montado editando o XML de dentro do .xlsx (um .zip): o openpyxl,
ao salvar, apagaria o logo (WMF) do modelo real da empresa. Tudo o que não é
preenchido aqui é copiado byte a byte do modelo.

O sistema preenche só o que já sabe (tema, objetivo, datas, local,
integração, On The Job e os participantes previstos); o resto o RH completa
no Excel.
"""
import math
import re
import zipfile
from io import BytesIO
from posixpath import dirname, join, normpath
from xml.sax.saxutils import escape

from django.conf import settings

# --- Mapa de células do Form40B Rev.18 -------------------------------------
FRONT_SHEET = "FRENTE"
BACK_SHEET = "VERSO"  # fica só no On The Job, em branco

CELL_THEME = "B5"            # "Tema/ Treinamento: "
CELL_GOAL = "B15"            # "Objetivo do Treinamento: "
CELL_LOCATION = "B17"        # "☐ Interno ... ☐ Externo"
CELL_ON_THE_JOB = "B25"      # "☐ Sim        ☐ Não"
CELL_DATE = "B37"            # " Data Realização: "
CELL_INTEGRATION = "J12"     # "(   )Integração"

LIST_FIRST_ROW = 41          # a linha 40 é o cabeçalho da lista
LIST_PAGE_ROWS = 51          # linhas por página (41 a 91 no modelo)
COLUMN_NUMBER, COLUMN_NAME, COLUMN_DEPARTMENT, COLUMN_GDL = "A", "B", "F", "H"
GDL_EMPTY, GDL_MARKED = "     |", "     |  X"
LIST_MERGES = (("B", "E"), ("F", "G"), ("I", "M"))

UNCHECKED, CHECKED = "☐", "☒"  # ☐ e ☒
INTEGRATION_EMPTY, INTEGRATION_MARKED = "(   )Integração", "( X )Integração"

# Valor preenchido pelo sistema: azul e em negrito, para destacar do modelo.
VALUE_RUN = (
    '<r><rPr><b/><sz val="11"/><color rgb="FF0000FF"/><rFont val="Calibri"/>'
    '<family val="2"/><scheme val="minor"/></rPr>'
    '<t xml:space="preserve">{}</t></r>'
)

WORKBOOK = "xl/workbook.xml"
WORKBOOK_RELS = "xl/_rels/workbook.xml.rels"
CONTENT_TYPES = "[Content_Types].xml"
APP_PROPS = "docProps/app.xml"
CALC_CHAIN = "xl/calcChain.xml"
STYLES = "xl/styles.xml"


class AttendanceTemplateError(Exception):
    """O modelo não existe ou não tem a estrutura esperada do Form40B."""


# --- Células -----------------------------------------------------------------

def _cell_pattern(ref):
    # Célula vazia é auto-fechada (<c r="B41" s="3"/>): o (?:/>|...) evita que
    # o .*? engula a célula seguinte.
    return re.compile(r'<c r="%s"(?:\s[^>/]*)?(?:/>|>.*?</c>)' % ref, re.S)


def _get_cell(xml, ref):
    match = _cell_pattern(ref).search(xml)
    if not match:
        raise AttendanceTemplateError(f"Célula {ref} não encontrada no modelo.")
    return match


def _replace_cell(xml, ref, new_cell):
    match = _get_cell(xml, ref)
    return xml[:match.start()] + new_cell + xml[match.end():]


def _style_attr(cell):
    style = re.search(r'\ss="(\d+)"', cell)
    return f' s="{style.group(1)}"' if style else ""


def _text(value):
    return escape(str(value).replace("\r", ""))


def _inline_cell(ref, cell, text):
    """Troca o conteúdo da célula por um texto, mantendo o estilo dela."""
    return (
        f'<c r="{ref}"{_style_attr(cell)} t="inlineStr"><is>'
        f'<t xml:space="preserve">{_text(text)}</t></is></c>'
    )


def _set_text(xml, ref, text):
    cell = _get_cell(xml, ref).group(0)
    return _replace_cell(xml, ref, _inline_cell(ref, cell, text))


def _set_number(xml, ref, number):
    cell = _get_cell(xml, ref).group(0)
    return _replace_cell(xml, ref, f'<c r="{ref}"{_style_attr(cell)}><v>{number}</v></c>')


def _append_value(xml, ref, value):
    """Acrescenta o valor (azul, negrito) depois do rótulo que já está na célula."""
    if not value:
        return xml
    cell = _get_cell(xml, ref).group(0)
    if "<is>" not in cell:
        raise AttendanceTemplateError(f"Célula {ref} deveria ter texto no modelo.")
    if "<r>" not in cell:
        # Texto simples (<is><t>...</t></is>) vira um trecho, para somar o valor.
        cell = re.sub(
            r"<is>\s*<t(?:\s[^>]*)?>(.*?)</t>\s*</is>",
            r'<is><r><t xml:space="preserve">\1</t></r></is>',
            cell, flags=re.S,
        )
    cell = cell.replace("</is>", VALUE_RUN.format(_text(value)) + "</is>")
    return _replace_cell(xml, ref, cell)


def _tick(xml, ref, label):
    """Marca a caixinha (☐ -> ☒) que vem antes do texto `label`."""
    cell = _get_cell(xml, ref).group(0)
    box = f"{UNCHECKED} {label}"
    if box not in cell:
        raise AttendanceTemplateError(f'"{box}" não encontrado na célula {ref}.')
    return _replace_cell(xml, ref, cell.replace(box, f"{CHECKED} {label}", 1))


# --- Cabeçalho (frente) --------------------------------------------------------

def _date_text(training):
    if not training.start_date:
        return ""
    text = training.start_date.strftime("%d/%m/%Y")
    if training.end_date and training.end_date != training.start_date:
        text += " a " + training.end_date.strftime("%d/%m/%Y")
    return text


def _fill_header(xml, training):
    xml = _append_value(xml, CELL_THEME, training.training_name)
    xml = _append_value(xml, CELL_GOAL, training.training_description)
    xml = _append_value(xml, CELL_DATE, _date_text(training))
    xml = _tick(xml, CELL_LOCATION, "Externo" if training.training_location_type == "Externo" else "Interno")
    xml = _tick(xml, CELL_ON_THE_JOB, "Sim" if training.is_on_the_job else "Não")
    if training.is_integration:
        xml = _set_text(xml, CELL_INTEGRATION, INTEGRATION_MARKED)
    return xml


# --- Lista de participantes (verso da frente) ------------------------------------

def _row_pattern(number):
    return re.compile(r'<row r="%d"[^>]*>.*?</row>' % number, re.S)


def _renumber_row(row_xml, old, new):
    row_xml = re.sub(r'(<row r=")%d"' % old, r'\g<1>%d"' % new, row_xml)
    return re.sub(r'(<c r="[A-Z]+)%d"' % old, r'\g<1>%d"' % new, row_xml)


def _add_list_rows(xml, total_rows):
    """Cria as páginas extras da lista (51 linhas cada), copiando o modelo."""
    template_last = LIST_FIRST_ROW + LIST_PAGE_ROWS - 1
    new_last = LIST_FIRST_ROW + total_rows - 1
    if new_last == template_last:
        return xml

    if re.search(r'<row r="(\d+)"', xml[_row_pattern(template_last).search(xml).end():]):
        raise AttendanceTemplateError("O modelo tem linhas depois da lista.")
    body = _row_pattern(template_last - 1).search(xml).group(0)
    last = _row_pattern(template_last).search(xml)

    rows = []
    for number in range(template_last + 1, new_last + 1):
        pattern, old = (last.group(0), template_last) if number == new_last else (body, template_last - 1)
        row = _renumber_row(pattern, old, number)
        row = _set_number(row, f"{COLUMN_NUMBER}{number}", number - LIST_FIRST_ROW + 1)
        rows.append(row)
    xml = xml[:last.end()] + "".join(rows) + xml[last.end():]

    merges = "".join(
        f'<mergeCell ref="{first}{n}:{end}{n}"/>'
        for n in range(template_last + 1, new_last + 1) for first, end in LIST_MERGES
    )
    xml = xml.replace("</mergeCells>", merges + "</mergeCells>")
    xml = re.sub(
        r'<mergeCells count="\d+"',
        lambda _: '<mergeCells count="%d"' % xml.count("<mergeCell "),
        xml,
    )

    breaks = "".join(
        f'<brk id="{row}" max="16383" man="1"/>'
        for row in range(template_last, new_last, LIST_PAGE_ROWS)
    )
    xml = xml.replace("</rowBreaks>", breaks + "</rowBreaks>")
    count = xml.count("<brk ")
    xml = re.sub(
        r'<rowBreaks count="\d+" manualBreakCount="\d+"',
        f'<rowBreaks count="{count}" manualBreakCount="{count}"', xml,
    )
    return re.sub(r'(<dimension ref="A1:[A-Z]+)\d+"', r'\g<1>%d"' % new_last, xml)


def _fill_participants(xml, employees):
    total_rows = max(1, math.ceil(len(employees) / LIST_PAGE_ROWS)) * LIST_PAGE_ROWS
    xml = _add_list_rows(xml, total_rows)
    for index, employee in enumerate(employees):
        row = LIST_FIRST_ROW + index
        department = employee.department.name if employee.department_id else ""
        xml = _set_text(xml, f"{COLUMN_NAME}{row}", employee.name)
        xml = _set_text(xml, f"{COLUMN_DEPARTMENT}{row}", department)
        xml = _set_text(xml, f"{COLUMN_GDL}{row}", GDL_MARKED)
    return xml, LIST_FIRST_ROW + total_rows - 1


def _shrink_wide_numbers(sheet, styles, last_row):
    """
    A coluna Nº do modelo só cabe dois dígitos: do 100 em diante o Excel
    mostraria "##". Essas células ganham uma cópia do estilo com "reduzir
    para caber" (shrinkToFit).
    """
    first = LIST_FIRST_ROW + 99
    if last_row < first:
        return sheet, styles
    cell = _get_cell(sheet, f"{COLUMN_NUMBER}{first}").group(0)
    index = int(re.search(r'\ss="(\d+)"', cell).group(1)) if ' s="' in cell else 0

    block = re.search(r"(<cellXfs count=\")(\d+)(\">)(.*?)(</cellXfs>)", styles, re.S)
    xfs = re.findall(r"<xf [^>]*/>|<xf [^>]*>.*?</xf>", block.group(4), re.S)
    xf = xfs[index]
    if "<alignment" in xf:
        xf = re.sub(r"<alignment", '<alignment shrinkToFit="1"', xf, count=1)
    else:
        xf = xf.replace("/>", '><alignment shrinkToFit="1"/></xf>', 1) if xf.endswith("/>") \
            else xf.replace("</xf>", '<alignment shrinkToFit="1"/></xf>')
    if "applyAlignment" not in xf:
        xf = xf.replace("<xf ", '<xf applyAlignment="1" ', 1)
    new_index = len(xfs)
    styles = (
        styles[:block.start()] + block.group(1) + str(new_index + 1) + block.group(3)
        + block.group(4) + xf + block.group(5) + styles[block.end():]
    )

    for row in range(first, last_row + 1):
        ref = f"{COLUMN_NUMBER}{row}"
        number = re.search(r"<v>(\d+)</v>", _get_cell(sheet, ref).group(0)).group(1)
        sheet = _replace_cell(sheet, ref, f'<c r="{ref}" s="{new_index}"><v>{number}</v></c>')
    return sheet, styles


# --- Pasta de trabalho: abas, área de impressão, propriedades --------------------

def _sheet_targets(parts):
    """[(nome, r:id, caminho da parte)] na ordem das abas."""
    rels = {}
    for tag in re.findall(r"<Relationship [^>]*/>", parts[WORKBOOK_RELS]):
        rels[re.search(r'\sId="([^"]+)"', tag).group(1)] = re.search(r'\sTarget="([^"]+)"', tag).group(1)
    sheets = []
    for tag in re.findall(r"<sheet [^>]*/>", parts[WORKBOOK]):
        name = re.search(r'name="([^"]+)"', tag).group(1)
        rid = re.search(r'r:id="([^"]+)"', tag).group(1)
        target = rels[rid].lstrip("/")
        sheets.append((name, rid, target if target.startswith("xl/") else normpath(join("xl", target))))
    return sheets


def _rels_name(part):
    return join(dirname(part), "_rels", part.rsplit("/", 1)[-1] + ".rels")


def _related_parts(parts, part):
    rels = parts.get(_rels_name(part))
    if not rels:
        return []
    found = []
    for tag in re.findall(r"<Relationship [^>]*/>", rels):
        if 'TargetMode="External"' in tag:
            continue
        target = re.search(r'Target="([^"]+)"', tag).group(1)
        path = target.lstrip("/") if target.startswith("/") else normpath(join(dirname(part), target))
        found.append(path)
    return found


def _reachable(parts, roots):
    seen, stack = set(), list(roots)
    while stack:
        part = stack.pop()
        if part in seen:
            continue
        seen.add(part)
        stack.extend(_related_parts(parts, part))
    return seen


def _drop_sheets(parts, keep):
    sheets = _sheet_targets(parts)
    dropped = [(i, name, rid, path) for i, (name, rid, path) in enumerate(sheets) if name not in keep]
    if not dropped:
        return parts
    kept_paths = [path for name, _, path in sheets if name in keep]

    workbook = parts[WORKBOOK]
    rels = parts[WORKBOOK_RELS]
    for index, name, rid, _ in dropped:
        workbook = re.sub(r'<sheet [^>]*r:id="%s"[^>]*/>' % re.escape(rid), "", workbook)
        rels = re.sub(r'<Relationship [^>]*Id="%s"[^>]*/>' % re.escape(rid), "", rels)
        workbook = re.sub(r'<definedName [^>]*localSheetId="%d"[^>]*>.*?</definedName>' % index, "", workbook, flags=re.S)
        workbook = re.sub(
            r"<definedName [^>]*>[^<]*'?%s'?![^<]*</definedName>" % re.escape(name), "", workbook
        )
    workbook = re.sub(r'\s(activeTab|firstSheet)="\d+"', "", workbook)
    workbook = re.sub(r"<definedNames>\s*</definedNames>", "", workbook)

    # calcChain cita células das abas removidas; o Excel o recria sozinho.
    if CALC_CHAIN in parts:
        rels = re.sub(r'<Relationship [^>]*Target="[^"]*calcChain\.xml"[^>]*/>', "", rels)
    parts[WORKBOOK], parts[WORKBOOK_RELS] = workbook, rels

    still_used = _reachable(parts, kept_paths + [WORKBOOK])
    to_remove = _reachable(parts, [path for *_, path in dropped]) - still_used
    if CALC_CHAIN in parts:
        to_remove.add(CALC_CHAIN)
    for part in to_remove:
        parts.pop(part, None)
        parts.pop(_rels_name(part), None)
        parts[CONTENT_TYPES] = re.sub(
            r'<Override [^>]*PartName="/%s"[^>]*/>' % re.escape(part), "", parts[CONTENT_TYPES]
        )
    return parts


def _update_app_props(parts):
    """Lista de abas e intervalos nomeados em docProps/app.xml (Propriedades do arquivo)."""
    app = parts.get(APP_PROPS)
    if app is None:
        return parts
    sheets = [name for name, *_ in _sheet_targets(parts)]
    print_areas = [
        f"{sheets[int(i)]}!Print_Area"
        for i in re.findall(r'<definedName name="_xlnm.Print_Area" localSheetId="(\d+)"', parts[WORKBOOK])
    ]
    titles = sheets + print_areas
    counts = iter([len(sheets), len(print_areas)])
    app = re.sub(r"(<vt:i4>)\d+(</vt:i4>)", lambda m: f"{m.group(1)}{next(counts, 0)}{m.group(2)}", app)
    entries = "".join(f"<vt:lpstr>{escape(t)}</vt:lpstr>" for t in titles)
    app = re.sub(
        r"<TitlesOfParts>.*?</TitlesOfParts>",
        f'<TitlesOfParts><vt:vector size="{len(titles)}" baseType="lpstr">{entries}</vt:vector></TitlesOfParts>',
        app, flags=re.S,
    )
    parts[APP_PROPS] = app
    return parts


def _extend_print_area(workbook, last_row):
    return re.sub(
        r'(<definedName name="_xlnm.Print_Area" localSheetId="0">[^<]*\$)(\d+)(</definedName>)',
        lambda m: f"{m.group(1)}{max(int(m.group(2)), last_row)}{m.group(3)}",
        workbook,
    )


# --- Entrada -----------------------------------------------------------------

def build_attendance_sheet(training, template_path=None):
    """Devolve os bytes do .xlsx da lista de presença deste treinamento."""
    path = template_path or settings.ATTENDANCE_TEMPLATE_PATH
    try:
        with zipfile.ZipFile(path) as source:
            infos = source.infolist()
            original = {info.filename: source.read(info.filename) for info in infos}
    except (OSError, zipfile.BadZipFile) as error:
        raise AttendanceTemplateError(f"Modelo da lista de presença indisponível: {path}") from error

    # XML vira texto para editar; imagens e outros binários ficam como estão.
    parts = {
        name: data.decode("utf-8") if name.endswith((".xml", ".rels")) else data
        for name, data in original.items()
    }
    front = next((p for name, _, p in _sheet_targets(parts) if name == FRONT_SHEET), None)
    if front is None:
        raise AttendanceTemplateError(f'Aba "{FRONT_SHEET}" não encontrada no modelo.')

    employees = list(
        training.scheduled_employees.select_related("department").order_by("name")
    )
    sheet = _fill_header(parts[front], training)
    sheet, last_row = _fill_participants(sheet, employees)
    parts[front], parts[STYLES] = _shrink_wide_numbers(sheet, parts[STYLES], last_row)
    parts[WORKBOOK] = _extend_print_area(parts[WORKBOOK], last_row)

    keep = {FRONT_SHEET, BACK_SHEET} if training.is_on_the_job else {FRONT_SHEET}
    parts = _update_app_props(_drop_sheets(parts, keep))

    output = BytesIO()
    with zipfile.ZipFile(output, "w") as target:
        for info in infos:
            if info.filename not in parts:
                continue
            data = parts[info.filename]
            if isinstance(data, str):
                data = data.encode("utf-8")
            target.writestr(info, data, compress_type=info.compress_type)
    return output.getvalue()
