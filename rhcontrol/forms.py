from django import forms 
from django.contrib.auth.models import User

class LoginForm(forms.Form):
    email = forms.EmailField(label='Email', max_length=100, widget=forms.EmailInput(attrs={
        'class': 'form-control',
        'placeholder': 'Digite seu email',
    }))

    password = forms.CharField(label='Senha', max_length=100, widget=forms.PasswordInput(attrs={
        'class': 'form-control',
        'placeholder': 'Digite sua senha',
    }))

