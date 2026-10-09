import hashlib

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth.models import User
from django.core.cache import cache
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

# Proteção contra força bruta: depois de LOGIN_MAX_ATTEMPTS falhas dentro de
# LOGIN_LOCKOUT_SECONDS, novas tentativas são recusadas sem nem checar a senha.
# Contamos por login digitado (protege uma conta) e por IP (protege contra
# alguém testando várias contas). O contador vive no cache do Django.
LOGIN_MAX_ATTEMPTS = getattr(settings, 'LOGIN_MAX_ATTEMPTS', 5)
LOGIN_MAX_ATTEMPTS_PER_IP = getattr(settings, 'LOGIN_MAX_ATTEMPTS_PER_IP', 20)
LOGIN_LOCKOUT_SECONDS = getattr(settings, 'LOGIN_LOCKOUT_SECONDS', 15 * 60)


def _login_attempt_keys(request, login_input):
    login_hash = hashlib.sha256(login_input.lower().encode()).hexdigest()
    ip = request.META.get('REMOTE_ADDR', '')
    return (
        (f'login-fail:user:{login_hash}', LOGIN_MAX_ATTEMPTS),
        (f'login-fail:ip:{ip}', LOGIN_MAX_ATTEMPTS_PER_IP),
    )


def _is_login_locked(keys):
    return any(cache.get(key, 0) >= limit for key, limit in keys)


def _register_login_failure(keys):
    for key, _ in keys:
        # add() só cria se não existir; o prazo conta a partir da 1ª falha.
        cache.add(key, 0, LOGIN_LOCKOUT_SECONDS)
        try:
            cache.incr(key)
        except ValueError:  # expirou entre o add() e o incr()
            cache.set(key, 1, LOGIN_LOCKOUT_SECONDS)


def login_create(request):
    if request.method != 'POST':
        raise Http404()

    form = LoginForm(request.POST)

    if form.is_valid():
        login_input = form.cleaned_data.get('email', '').strip()
        password = form.cleaned_data.get('password', '')
        attempt_keys = _login_attempt_keys(request, login_input)

        if _is_login_locked(attempt_keys):
            messages.error(request, 'Muitas tentativas de login. Aguarde alguns minutos e tente novamente.')
            return render(request, 'authors/pages/login.html', {
                'form': form,
                'form_action': reverse('rhcontrol:login_create')
            }, status=429)

        user = authenticate(request, username=login_input, password=password)

        if user is None:
            user_obj = User.objects.filter(email__iexact=login_input).first()
            if user_obj:
                user = authenticate(request, username=user_obj.username, password=password)

        if user is not None:
            cache.delete(attempt_keys[0][0])
            messages.success(request, 'Logado com sucesso!')
            login(request, user)
            return redirect('rhcontrol:dashboard')
        else:
            _register_login_failure(attempt_keys)
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