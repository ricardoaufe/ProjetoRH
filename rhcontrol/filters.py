"""
Filtros de listagem compartilhados entre as telas e os PDFs.

Cada lista (funcionários, férias, treinamentos, ocorrências) tem um botão
"Gerar PDF" que repassa os mesmos parâmetros da URL. Antes, a lógica de
busca/filtro/ordenação era copiada nas duas views e as cópias divergiam
(ex.: o filtro "Demitidos" funcionava no PDF e não na tela). Centralizar
aqui garante que o PDF mostre exatamente o que a tela mostra.
"""
from django.db.models import Q
from django.utils import timezone

EMPLOYEE_SORT_FIELDS = ['name', 'cpf', 'department__name', 'mobile_phone']
TRAINING_SORT_FIELDS = ['training_name', 'start_date', 'end_date', 'training_provider', 'training_total_hours']


def filter_employees(queryset, params):
    """Busca, status ('active'/'terminated') e ordenação da lista de funcionários."""
    query = params.get('search', '')
    if query:
        queryset = queryset.filter(
            Q(name__icontains=query) |
            Q(cpf__icontains=query) |
            Q(email__icontains=query) |
            Q(department__name__icontains=query) |
            Q(mobile_phone__icontains=query)
        )

    status = params.get('status')
    if status == 'active':
        queryset = queryset.filter(termination_date__isnull=True)
    elif status == 'terminated':
        queryset = queryset.filter(termination_date__isnull=False)

    sort_by = params.get('sort', 'name')
    return queryset.order_by(sort_by if sort_by in EMPLOYEE_SORT_FIELDS else 'name')


def filter_vacations(queryset, params, default_status='ativas'):
    """Busca por nome, período de início e status ('ativas'/'historico')."""
    search_query = params.get('search', '')
    if search_query:
        queryset = queryset.filter(employee__name__icontains=search_query)

    date_from = params.get('date_from', '')
    if date_from:
        queryset = queryset.filter(start_date__gte=date_from)

    date_to = params.get('date_to', '')
    if date_to:
        queryset = queryset.filter(start_date__lte=date_to)

    today = timezone.localdate()
    status = params.get('status', default_status)
    if status == 'historico':
        queryset = queryset.filter(end_date__lt=today)
    else:
        queryset = queryset.filter(end_date__gte=today)

    return queryset


def filter_trainings(queryset, params):
    """
    Busca, período, status e ordenação de treinamentos.
    O queryset precisa vir anotado com num_attended (usado pelos status).
    """
    search_query = params.get('search', '')
    if search_query:
        queryset = queryset.filter(
            Q(training_name__icontains=search_query) |
            Q(training_provider__icontains=search_query)
        )

    date_from = params.get('date_from', '')
    if date_from:
        queryset = queryset.filter(start_date__gte=date_from)

    date_to = params.get('date_to', '')
    if date_to:
        queryset = queryset.filter(start_date__lte=date_to)

    today = timezone.localdate()
    status = params.get('status', '')
    if status == 'proximos':
        queryset = queryset.filter(start_date__gte=today)
    elif status == 'pendentes':
        queryset = queryset.filter(start_date__lt=today, num_attended=0)
    elif status == 'realizados':
        queryset = queryset.filter(start_date__lt=today, num_attended__gt=0)
    elif status == 'integracao':
        queryset = queryset.filter(is_integration=True)

    sort_by = params.get('sort', '-start_date')
    if sort_by.lstrip('-') not in TRAINING_SORT_FIELDS:
        sort_by = '-start_date'
    return queryset.order_by(sort_by)


def filter_occurrences(queryset, params):
    """Busca por título, período e ordenação (mais recentes primeiro por padrão)."""
    search_query = params.get('search', '').strip()
    if search_query:
        queryset = queryset.filter(title__icontains=search_query)

    date_from = params.get('date_from')
    if date_from:
        queryset = queryset.filter(occurrence_date__gte=date_from)

    date_to = params.get('date_to')
    if date_to:
        queryset = queryset.filter(occurrence_date__lte=date_to)

    if params.get('sort') == 'occurrence_date':
        return queryset.order_by('occurrence_date', 'created_at')
    return queryset.order_by('-occurrence_date', '-created_at')
