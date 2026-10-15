from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.shortcuts import get_object_or_404, redirect, render

from rhcontrol.filters import filter_vacations
from rhcontrol.forms import VacationForm
from rhcontrol.models import Vacation
from rhcontrol.pagination import paginate


def _warn_if_late(request, form):
    if form.is_late:
        deadline = form.period['deadline'].strftime('%d/%m/%Y')
        messages.warning(request, f'Férias após o prazo de {deadline}: devem ser pagas em dobro (CLT art. 137).')


@login_required
@permission_required('rhcontrol.view_vacation', raise_exception=True)
def vacation_view(request):
    vacation_list = Vacation.objects.select_related('employee').all()

    search_query = request.GET.get('search', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    
    status = request.GET.get('status', 'ativas')

    sort_by = request.GET.get('sort', 'employee__name') 

    valid_sort_fields = ['employee__name', 'start_date', 'end_date', 'return_date', 'vacation_duration']
    
    if sort_by in valid_sort_fields:
        vacation_list = vacation_list.order_by(sort_by)
    else:
        vacation_list = vacation_list.order_by('employee__name') 

    vacation_list = filter_vacations(vacation_list, request.GET)

    page_obj = paginate(request, vacation_list)

    context = {
        'object_list': page_obj,
        'page_obj': page_obj,
        'search_query': search_query,
        'date_from': date_from,
        'date_to': date_to,
        'current_sort': sort_by,
        'status': status,
    }
    return render(request, 'dashboard/pages/vacation/list.html', context)

@login_required
@permission_required('rhcontrol.add_vacation', raise_exception=True)
def vacation_create(request):
    if request.method == 'POST':
        form = VacationForm(request.POST)
        
        if form.is_valid():
            # Fim e retorno são calculados em Vacation.save(), que também
            # pula feriados nacionais (o cálculo que existia aqui não pulava
            # e era sobrescrito pelo model de qualquer forma).
            form.save()
            messages.success(request, 'Férias cadastradas com sucesso!')
            _warn_if_late(request, form)
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
@permission_required('rhcontrol.change_vacation', raise_exception=True)
def vacation_update(request, pk):
    vacation = get_object_or_404(Vacation, pk=pk)
    form = VacationForm(request.POST or None, instance=vacation)

    if form.is_valid():
        form.save()
        messages.success(request, 'Férias atualizadas com sucesso!')
        _warn_if_late(request, form)
        return redirect('rhcontrol:vacation_list')

    return render(request, 'dashboard/pages/vacation/form.html', {
        'form': form,
        'title': 'Editar Férias'
    })

@login_required
@permission_required('rhcontrol.delete_vacation', raise_exception=True)
def vacation_delete(request, pk):
    vacation = get_object_or_404(Vacation, pk=pk)

    if request.method == 'POST':
        vacation.delete()
        messages.success(request, 'Férias excluídas com sucesso!')
        return redirect('rhcontrol:vacation_list')

    return render(request, 'dashboard/pages/vacation/delete.html', {
        'vacation': vacation
    })