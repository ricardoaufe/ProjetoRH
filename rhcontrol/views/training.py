from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from rhcontrol.forms import TrainingForm
from rhcontrol.models import Employee, Training


@login_required
@permission_required('rhcontrol.view_training', raise_exception=True)
def training_view(request):
    training_list = Training.objects.annotate(
        num_attended=Count('attended_employees')
    ).order_by('-start_date')
    
    search_query = request.GET.get('search', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    status = request.GET.get('status', '')

    if search_query:
        training_list = training_list.filter(
            Q(training_name__icontains=search_query) |
            Q(training_provider__icontains=search_query)
        )

    if date_from:
        training_list = training_list.filter(start_date__gte=date_from)
    
    if date_to:
        training_list = training_list.filter(start_date__lte=date_to)

    today = timezone.now().date()

    

    if status == 'proximos':
        training_list = training_list.filter(start_date__gte=today)
    elif status == 'pendentes':
        training_list = training_list.filter(start_date__lt=today, num_attended=0)
    elif status == 'realizados':
        training_list = training_list.filter(start_date__lt=today, num_attended__gt=0)
    elif status == 'integracao':
        training_list = training_list.filter(is_integration=True)



    paginator = Paginator(training_list, 15)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'object_list': page_obj,
        'search_query': search_query,
        'date_from': date_from,
        'date_to': date_to,
        'status': status,
    }
    return render(request, 'dashboard/pages/training/list.html', context)

@login_required
@permission_required('rhcontrol.add_training', raise_exception=True)
def training_create(request):
    if request.method == 'POST':
        form = TrainingForm(request.POST)
        if form.is_valid():
            training = form.save(commit=False)
            training.save() 
            
            is_fundamental = form.cleaned_data.get('is_fundamental')
            all_depts = form.cleaned_data.get('all_departments')
            target_dept = form.cleaned_data.get('target_department')

            if is_fundamental:
                if all_depts:
                    employees_to_add = Employee.objects.filter(termination_date__isnull=True)
                elif target_dept:
                    employees_to_add = Employee.objects.filter(department=target_dept, termination_date__isnull=True)
                else:
                    employees_to_add = Employee.objects.filter(department=target_dept, termination_date__isnull=True)

                training.scheduled_employees.set(employees_to_add)
                training.attended_employees.set(employees_to_add)
            
            else:
                form.save_m2m() 

            messages.success(request, 'Treinamento criado com sucesso!')
            return redirect('rhcontrol:training_list')
    else:
        form = TrainingForm()
    
    return render(request, 'dashboard/pages/training/form.html', {'form': form})

@login_required
@permission_required('rhcontrol.change_training', raise_exception=True)
def training_update(request, pk):
    training = get_object_or_404(Training, pk=pk)
    form = TrainingForm(request.POST or None, instance=training)

    if form.is_valid():
        form.save()
        messages.success(request, 'Treinamento atualizado com sucesso!')
        return redirect('rhcontrol:training_list')

    return render(request, 'dashboard/pages/training/form.html', {
        'form': form,
        'title': 'Editar Treinamento'
    })    

@login_required
@permission_required('rhcontrol.delete_training', raise_exception=True)
def training_delete(request, pk):
    training = get_object_or_404(Training, pk=pk)

    if request.method == 'POST':
        training.delete()
        messages.success(request, 'Treinamento excluído com sucesso!')
        return redirect('rhcontrol:training_list')

    return render(request, 'dashboard/pages/training/delete.html', {
        'training': training
    })