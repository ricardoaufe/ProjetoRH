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
        widgets = {
            'birth_date': forms.DateInput(attrs={'type': 'date',}),
            'hire_date': forms.DateInput(attrs={'type': 'date',}),
            'rg_issue_date': forms.DateInput(attrs={'type': 'date',}),
            'ctps_issue_date': forms.DateInput(attrs={'type': 'date',}),
            'admission_exam_date': forms.DateInput(attrs={'type': 'date',}),
            'termination_date': forms.DateInput(attrs={'type': 'date',}),
            'arrival_date': forms.DateInput(attrs={'type': 'date',}),
            'naturalization_date': forms.DateInput(attrs={'type': 'date',}),
            'rne_issue_date': forms.DateInput(attrs={'type': 'date',}),
            'cipa_mandate_start_date': forms.DateInput(attrs={'type': 'date',}),
            'cipa_mandate_end_date': forms.DateInput(attrs={'type': 'date',}),

            'department': forms.Select(attrs={'class': 'form-control'}),
            'job_title': forms.Select(attrs={'class': 'form-control'}),                      
            }

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

class VacationForm(forms.Form):
    employee = forms.ModelChoiceField(
        queryset=Employee.objects.all(), 
        label="Funcionário",
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    start_date = forms.DateField(
        label="Data de Início",
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date',
        })
    )
    
    vacation_duration = forms.IntegerField(
        label="Duração (em dias)",
        min_value=1,
        max_value=30,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ex: 30'
        })
    )
        