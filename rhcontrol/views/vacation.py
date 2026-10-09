from datetime import timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from rhcontrol.forms import VacationForm
from rhcontrol.models import Vacation


@login_required
@permission_required('rhcontrol.view_vacation', raise_exception=True)
def vacation_view(request):
    from django.utils import timezone
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

    hoje = timezone.localdate()
    if status == 'historico':
        vacation_list = vacation_list.filter(end_date__lt=hoje)
    else:
        vacation_list = vacation_list.filter(end_date__gte=hoje)

    if search_query:
        vacation_list = vacation_list.filter(employee__name__icontains=search_query)

    if date_from:
        vacation_list = vacation_list.filter(start_date__gte=date_from)

    if date_to:
        vacation_list = vacation_list.filter(start_date__lte=date_to)

    paginator = Paginator(vacation_list, 30)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'object_list': page_obj,
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
            employee = form.cleaned_data['employee']
            start_date = form.cleaned_data['start_date']
            duration = form.cleaned_data['vacation_duration']

            if duration is None or duration <= 0:
                form.add_error('vacation_duration', 'A duração deve ser maior que zero.')
            else:
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
@permission_required('rhcontrol.change_vacation', raise_exception=True)
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