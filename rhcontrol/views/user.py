# user.py
from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.auth.models import User
from django.db.models import Count
from django.shortcuts import get_object_or_404, redirect, render

from rhcontrol.forms import SystemUserForm, SystemUserUpdateForm


@login_required
@permission_required('auth.add_user', raise_exception=True)
def user_create_view(request):
    if request.method == 'POST':
        form = SystemUserForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('rhcontrol:user_list')
    else:
        form = SystemUserForm()

    context = {
        'form': form
    }
    return render(request, 'dashboard/pages/user/form.html', context)

@login_required
@permission_required('auth.view_user', raise_exception=True)
def user_list_view(request):
    users = User.objects.annotate(num_groups=Count('groups')).order_by('username')
    
    context = {
        'users': users
    }
    return render(request, 'dashboard/pages/user/list.html', context)

@login_required
@permission_required('auth.change_user', raise_exception=True)
def user_update_view(request, pk):
    """ View para editar um Usuário existente """
    user = get_object_or_404(User, pk=pk)

    if user.is_superuser:
        messages.warning(request, "Acesso negado: Você não pode editar um superusuário.")
        return redirect('rhcontrol:user_list')

    if request.method == 'POST':
        form = SystemUserUpdateForm(request.POST, instance=user)
        if form.is_valid():
            form.save()
            messages.success(request, f"Usuário '{user.username}' atualizado com sucesso.")
            return redirect('rhcontrol:user_list')
        else:
            messages.error(request, "Erro ao atualizar. Verifique os campos.")
    else:
        form = SystemUserUpdateForm(instance=user)

    context = {
        'form': form,
        'system_user': user,
        'is_update': True
    }
    return render(request, 'dashboard/pages/user/form.html', context)


@login_required
@permission_required('auth.delete_user', raise_exception=True)
def user_delete_view(request, pk):
    user = get_object_or_404(User, pk=pk)

    if user == request.user or user.is_superuser:
        messages.warning(request, "Acesso negado: Você não pode excluir a si mesmo ou um administrador.")
        return redirect('rhcontrol:user_list')

    if request.method == 'POST':
        user.delete()
        messages.success(request, 'Usuário excluído com sucesso!')
        return redirect('rhcontrol:user_list')

    return render(request, 'dashboard/pages/user/delete.html', {'system_user': user})