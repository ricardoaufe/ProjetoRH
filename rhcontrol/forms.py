from django import forms 
from django.contrib.auth.models import User

class LoginForm(forms.Form):
    email = forms.CharField(label='Usuário ou Email', max_length=100, widget=forms.TextInput(attrs={
        'class': 'form-control',
        'placeholder': 'Digite seu usuário ou email',
    }))

    password = forms.CharField(label='Senha', max_length=100, widget=forms.PasswordInput(attrs={
        'class': 'form-control',
        'placeholder': 'Digite sua senha',
    }))

