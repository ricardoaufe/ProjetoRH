from django import forms 
from django.contrib.auth.models import User
from rhcontrol.models import Employee, JobTitle

class LoginForm(forms.Form):
    email = forms.CharField(label='Usuário ou Email', max_length=100, widget=forms.TextInput(attrs={
        'class': 'form-control',
        'placeholder': 'Digite seu usuário ou email',
    }))

    password = forms.CharField(label='Senha', max_length=100, widget=forms.PasswordInput(attrs={
        'class': 'form-control',
        'placeholder': 'Digite sua senha',
    }))

class EmployeeForm(forms.ModelForm):
    class Meta:
        model = Employee
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        if 'department' in self.data:
            try:
                department_id = int(self.data.get('department'))
                self.fields['job_title'].queryset = JobTitle.objects.filter(department_id=department_id).order_by('name')
            except (ValueError, TypeError):
                pass 
        elif self.instance.pk and self.instance.department:

            self.fields['job_title'].queryset = self.instance.department.job_titles.order_by('name')
        else:
            self.fields['job_title'].queryset = JobTitle.objects.none()

        