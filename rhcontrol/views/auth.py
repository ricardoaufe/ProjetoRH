from django.contrib import messages
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth.models import User
from django.core.exceptions import PermissionDenied
from django.http import Http404
from django.shortcuts import redirect, render
from django.urls import reverse

from rhcontrol.forms import LoginForm, UserUpdateForm


def login_view(request):
    
    if request.user.is_authenticated:
        return redirect('rhcontrol:dashboard') 

    form = LoginForm()
    
    return render(request, 'authors/pages/login.html', {
        'form': form,
        'form_action': reverse('rhcontrol:login_create'),
    })

def login_create(request):
    if request.method != 'POST':
        raise Http404()

    form = LoginForm(request.POST)

    if form.is_valid():
        login_input = form.cleaned_data.get('email', '').strip()
        password = form.cleaned_data.get('password', '')

        user = authenticate(request, username=login_input, password=password)

        if user is None:
            user_obj = User.objects.filter(email__iexact=login_input).first()
            if user_obj:
                user = authenticate(request, username=user_obj.username, password=password)

        if user is not None:
            messages.success(request, 'Logado com sucesso!')
            login(request, user)
            return redirect('rhcontrol:dashboard')
        else:
            messages.error(request, 'Usuário ou senha incorretos.')
    else:
        messages.error(request, 'Erro de validação.')

    return render(request, 'authors/pages/login.html', {
        'form': form,
        'form_action': reverse('rhcontrol:login_create')
    })

@login_required
def logout_view(request):
    if request.method != 'POST':
        return redirect('rhcontrol:login')

    logout(request)
    return redirect('rhcontrol:login')

@login_required
def profile_view(request):
    if request.method == 'POST':
        form = UserUpdateForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Perfil atualizado com sucesso!')
            return redirect('rhcontrol:profile')
        else:
            messages.error(request, 'Erro ao atualizar perfil.')

    form = UserUpdateForm(instance=request.user)

    return render(request, 'authors/pages/profile.html', {
        'form': form,
        'title': 'Meu Perfil'
    })

@login_required
def change_password(request):
    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user) 
            messages.success(request, 'Sua senha foi alterada com sucesso!')
            return redirect('rhcontrol:profile')
        else:
            messages.error(request, 'Erro ao alterar a senha. Verifique os campos.')
    else:
        form = PasswordChangeForm(request.user)
        
    return render(request, 'authors/pages/password_change.html', {
        'form': form,
        'title': 'Alterar Senha'
    })

def is_rh_admin(user):
    if user.groups.filter(name='RhAdmin').exists() or user.is_superuser:
        return True
    raise PermissionDenied