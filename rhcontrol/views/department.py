from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render

from rhcontrol.forms import DepartmentForm, JobTitleFormSet
from rhcontrol.models import Department, JobTitle


@login_required
@permission_required('rhcontrol.view_department', raise_exception=True)
def department_list(request):
    departments = Department.objects.all().order_by('name') 

    search_query = request.GET.get('search', '')
    
    if search_query:
        departments = departments.filter(
            Q(name__icontains=search_query) | 
            Q(description__icontains=search_query)
        )
    
    context = {
        'object_list': departments, 
        'title': 'Lista de Setores'
    }
    
    return render(request, 'dashboard/pages/departments/list.html', context)

@login_required
@permission_required('rhcontrol.add_department', raise_exception=True)
def department_create(request):
    if request.method == 'POST':
        form = DepartmentForm(request.POST)
        formset = JobTitleFormSet(request.POST)

        if form.is_valid() and formset.is_valid():
            department = form.save()
            formset.instance = department 
            formset.save()

            messages.success(request, 'Setor criado com sucesso!')
            return redirect('rhcontrol:department_list')
    else:
        form = DepartmentForm()
        formset = JobTitleFormSet()

    return render(request, 'dashboard/pages/departments/form.html', {
        'form': form,
        'formset': formset,
        'title': 'Cadastrar Setores'
    })

@login_required
@permission_required('rhcontrol.change_department', raise_exception=True)
def department_update(request, pk):
    department = get_object_or_404(Department, pk=pk)

    ordened_jobtitles = JobTitle.objects.order_by('base_salary')

    if request.method == 'POST':
        form = DepartmentForm(request.POST or None, instance=department)
        formset = JobTitleFormSet(request.POST or None, instance=department, queryset=ordened_jobtitles)

        if form.is_valid() and formset.is_valid():
            form.save()
            formset.save()
            messages.success(request, 'Setor atualizado com sucesso!')
            return redirect('rhcontrol:department_list')

    else:
        form = DepartmentForm(instance=department)
        formset = JobTitleFormSet(instance=department, queryset=ordened_jobtitles)

    return render(request, 'dashboard/pages/departments/form.html', {
        'form': form,
        'formset': formset,
        'title': 'Editar Setor'
    })    

@login_required
@permission_required('rhcontrol.delete_department', raise_exception=True)
def department_delete(request, pk):
    department = get_object_or_404(Department, pk=pk)

    if request.method == 'POST':
        department.delete()
        messages.success(request, 'Setor excluído com sucesso!')
        return redirect('rhcontrol:department_list')

    return render(request, 'dashboard/pages/departments/delete.html', {
        'department': department
    })

@login_required
@permission_required('rhcontrol.view_jobtitle', raise_exception=True)
def ajax_load_jobs_by_department(request):
    department_id = request.GET.get('department_id')
    jobs = []
    if department_id:
        jobs = [
            {'id': j.id, 'name': j.name, 'salary': str(j.base_salary or '0.00')}
            for j in JobTitle.objects.filter(department_id=department_id).order_by('name')
        ]
    return JsonResponse({'success': bool(department_id), 'jobs': jobs})
