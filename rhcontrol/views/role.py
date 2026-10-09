from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.auth.models import Group
from django.db.models import Count
from django.shortcuts import get_object_or_404, redirect, render

from rhcontrol.forms import RoleGroupForm
from rhcontrol.utils import RH_PERMISSION_MATRIX, get_matrix_permissions


@login_required
@permission_required('auth.add_group', raise_exception=True)
def role_create_view(request):
    if request.method == 'POST':
        form = RoleGroupForm(request.POST)
        if form.is_valid():
            new_group = form.save()
            new_group.permissions.set(get_matrix_permissions(request.POST.getlist('permissions')))

            return redirect('rhcontrol:role_list')
        
    else:
            form = RoleGroupForm()
        

    context = {
        'form': form,
        'permission_matrix': RH_PERMISSION_MATRIX
    }
    return render(request, 'dashboard/pages/roles/form.html', context)

@login_required
@permission_required('auth.view_group', raise_exception=True)
def role_list_view(request):

    roles = Group.objects.annotate(num_users=Count('user')).order_by('name')
    
    context = {
        'roles': roles
    }
    return render(request, 'dashboard/pages/roles/list.html', context)

@login_required
@permission_required('auth.change_group', raise_exception=True)
def role_update_view(request, pk):
    """ View para editar um Perfil existente """
    group = get_object_or_404(Group, pk=pk)

    if request.method == 'POST':
        form = RoleGroupForm(request.POST, instance=group)
        if form.is_valid():
            saved_group = form.save()
            # set() com lista vazia remove tudo se desmarcar tudo
            saved_group.permissions.set(get_matrix_permissions(request.POST.getlist('permissions')))
                
            messages.success(request, f"Perfil '{saved_group.name}' atualizado com sucesso!")
            return redirect('rhcontrol:role_list')
        else:
            messages.error(request, "Erro ao atualizar. Verifique os campos.")
    else:
        form = RoleGroupForm(instance=group)

    current_perms = list(group.permissions.values_list('codename', flat=True))

    context = {
        'form': form,
        'permission_matrix': RH_PERMISSION_MATRIX,
        'current_perms': current_perms,
        'is_update': True,
        'role': group
    }

    return render(request, 'dashboard/pages/roles/form.html', context) 


@login_required
@permission_required('auth.delete_group', raise_exception=True)
def role_delete_view(request, pk):
    group = get_object_or_404(Group, pk=pk)

    if request.method == 'POST':
        group.delete()
        messages.success(request, 'Perfil excluído com sucesso!')
        return redirect('rhcontrol:role_list')

    return render(request, 'dashboard/pages/roles/delete.html', {'role': group})
