"""
Paginação padrão das listas do sistema.

Toda lista usa o mesmo tamanho de página e o mesmo rodapé
(templates/partials/pagination.html), que mantém busca, filtros e
ordenação ao trocar de página.
"""
from django.core.paginator import Paginator

LIST_PAGE_SIZE = 20


def paginate(request, queryset, per_page=None):
    """
    Devolve a página pedida em ?page=. Número inválido ou fora do
    intervalo cai na primeira ou na última página, sem erro 404.
    """
    paginator = Paginator(queryset, per_page or LIST_PAGE_SIZE)
    return paginator.get_page(request.GET.get('page'))
