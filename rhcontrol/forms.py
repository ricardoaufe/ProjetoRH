from decimal import Decimal
from django import forms 
from django.contrib.auth.models import User
from rhcontrol.models import Dependent, Employee, JobTitle, Training, Vacation, Department

class LoginForm(forms.Form):
    email = forms.CharField(label='Usuário ou Email', max_length=100, widget=forms.TextInput(attrs={
        'class': 'form-control',
        'placeholder': 'Digite seu usuário ou email',
    }))

    password = forms.CharField(label='Senha', max_length=100, widget=forms.PasswordInput(attrs={
        'class': 'form-control',
        'placeholder': 'Digite sua senha',
    }))

class UserUpdateForm(forms.ModelForm):
    email = forms.EmailField(label="E-mail", required=True, widget=forms.EmailInput(attrs={'class': 'form-control'}))
    first_name = forms.CharField(label="Nome", required=True, widget=forms.TextInput(attrs={'class': 'form-control'}))
    last_name = forms.CharField(label="Sobrenome", required=True, widget=forms.TextInput(attrs={'class': 'form-control'}))

    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control', 'readonly': 'readonly'}), 
        }

class EmployeeForm(forms.ModelForm):
    current_salary = forms.CharField(
        label='Salário Atual',  
        required=False, 
        widget=forms.TextInput(attrs={'class': 'form-control money-input', 'placeholder': '0,00'})
    )
    
    change_date = forms.DateField(
        label="Data da Alteração (Histórico)", 
        required=False, 
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
        help_text="Se houver mudança de cargo/salário, qual a data de vigência?"
    )
    
    change_reason = forms.ChoiceField(
        label="Motivo da Alteração",
        required=False,
        choices=[
            ('', '--- Selecione o Motivo ---'),
            ('Promoção', 'Promoção'),
            ('Mérito', 'Mérito'),
            ('Dissídio', 'Dissídio'),
            ('Erro de Cadastro', 'Correção de Erro'),
        ],
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    class Meta:
        model = Employee
        fields = '__all__'
        widgets = {
            'birth_date': forms.DateInput(format='%Y-%m-%d', attrs={'type': 'date', 'class': 'form-control'}),
            'hire_date': forms.DateInput(format='%Y-%m-%d', attrs={'type': 'date', 'class': 'form-control'}),
            'rg_issue_date': forms.DateInput(format='%Y-%m-%d', attrs={'type': 'date', 'class': 'form-control'}),
            'ctps_issue_date': forms.DateInput(format='%Y-%m-%d', attrs={'type': 'date', 'class': 'form-control'}),
            'admission_exam_date': forms.DateInput(format='%Y-%m-%d', attrs={'type': 'date', 'class': 'form-control'}),
            'termination_date': forms.DateInput(format='%Y-%m-%d', attrs={'type': 'date', 'class': 'form-control'}),
            'arrival_date': forms.DateInput(format='%Y-%m-%d', attrs={'type': 'date', 'class': 'form-control'}),
            'naturalization_date': forms.DateInput(format='%Y-%m-%d', attrs={'type': 'date', 'class': 'form-control'}),
            'rne_issue_date': forms.DateInput(format='%Y-%m-%d', attrs={'type': 'date', 'class': 'form-control'}),
            'cipa_mandate_start_date': forms.DateInput(format='%Y-%m-%d', attrs={'type': 'date', 'class': 'form-control'}),
            'cipa_mandate_end_date': forms.DateInput(format='%Y-%m-%d', attrs={'type': 'date', 'class': 'form-control'}),
            'department': forms.Select(attrs={'class': 'form-control'}),
            'job_title': forms.Select(attrs={'class': 'form-control'}),   
            'cpf': forms.TextInput(attrs={'placeholder': '000.000.000-00'}),
            'mobile_phone': forms.TextInput(attrs={'placeholder': '(00) 00000-0000'}),
            'emergency_phone': forms.TextInput(attrs={'placeholder': '(00) 00000-0000'}),
            'zip_code': forms.TextInput(attrs={'placeholder': '00000-000'}),        
            }
        
    def clean_current_salary(self):
        salary = self.cleaned_data.get('current_salary')
        if not salary: return None
        # Se vier texto (1.500,00), limpamos. Se vier número, passamos direto.
        salary_str = str(salary).replace('.', '').replace(',', '.')
        try:
            return Decimal(salary_str)
        except:
            raise forms.ValidationError("Valor inválido")

    def clean_old_salary(self):
        salary = self.cleaned_data.get('old_salary')
        if not salary: return None
        salary_str = str(salary).replace('.', '').replace(',', '.')
        try:
            return Decimal(salary_str)
        except:
            raise forms.ValidationError("Valor inválido")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if self.instance and self.instance.pk:
            if self.instance.current_salary:
                self.initial['current_salary'] = f'{self.instance.current_salary:.2f}'.replace('.', ',')
        
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

        for field_name, field in self.fields.items():
            if isinstance(field.widget, forms.DateInput):
                field.widget.attrs.update({
                    'class': 'form-control',
                    'type': 'date'
                })

class DependentForm(forms.ModelForm):
    class Meta:
        model = Dependent
        fields = ['name', 'cpf', 'birth_date', 'relationship_type', 'has_disability']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nome Completo'}),
            'cpf': forms.TextInput(attrs={'class': 'form-control cpf-input', 'placeholder': '000.000.000-00'}),
            'birth_date': forms.DateInput(format='%Y-%m-%d', attrs={'type': 'date', 'class': 'form-control'}),
            'relationship_type': forms.Select(attrs={'class': 'form-control form-select'}),
        }

DependentFormSet = forms.inlineformset_factory(
    Employee,
    Dependent,
    form=DependentForm,
    extra=1,
    can_delete=True
)
        


class VacationForm(forms.ModelForm):
    class Meta:
        model = Vacation
        fields = ['employee', 'start_date', 'vacation_duration']
        
        widgets = {
            'employee': forms.Select(attrs={'class': 'form-control'}),
            'start_date': forms.DateInput(format='%Y-%m-%d', attrs={'class': 'form-control', 'type': 'date'}),
            'vacation_duration': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Ex: 30'}),
        }

class TrainingForm(forms.ModelForm):
    all_departments = forms.BooleanField(
        required=False, 
        label="Todos os Setores", 
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    
    class Meta:
        model = Training
        fields = '__all__'
        
        widgets = {
            'training_date': forms.DateInput(format='%Y-%m-%d', attrs={'class': 'form-control', 'type': 'date'}),
            'is_fundamental': forms.CheckboxInput(attrs={'class': 'form-check-input', 'id': 'id_is_fundamental'}),
            'target_department': forms.Select(attrs={'class': 'form-control', 'id': 'id_target_department'}),
            
            'scheduled_employees': forms.SelectMultiple(attrs={'class': 'form-control', 'size': '10', 'id': 'id_scheduled_employees'}),
            'attended_employees': forms.SelectMultiple(attrs={'class': 'form-control', 'size': '10'}),
        }

    
    
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            self.fields['attended_employees'].queryset = self.instance.scheduled_employees.all()
        else:
            self.fields['attended_employees'].queryset = Employee.objects.none()
        
class DepartmentForm(forms.ModelForm):
    class Meta:
        model = Department
        fields = ['name', 'description']
        labels = {
            'name': 'Nome do Setor',
            'description': 'Descrição do Setor',
        }
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nome do Setor'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'placeholder': 'Descrição do Setor', 'rows': 3}),
        }
    
class JobTitleForm(forms.ModelForm):
    base_salary = forms.CharField(
        label='Salário Base',
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control money-input', 'placeholder': '0,00'})
    )
    class Meta:
        model = JobTitle
        fields = ['name', 'base_salary', 'description']
        labels = {
            'name': 'Nome do Cargo',
            'base_salary': 'Salário Base',
            'description': 'Descrição',
        }
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nome do Cargo'}),
            'base_salary': forms.TextInput(attrs={'class': 'form-control money-input', 'placeholder': '0,00'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'placeholder': 'Descrição (Opcional)', 'rows': 1}),
        }

    # --- NOVO: Formata o valor inicial com vírgula ao carregar a página ---
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk and self.instance.base_salary:
            self.initial['base_salary'] = f'{self.instance.base_salary:.2f}'.replace('.', ',')

    def clean_base_salary(self):
        salary = self.cleaned_data.get('base_salary')
        if not salary: return None
        if isinstance(salary, (float, int, Decimal)): return salary
        
        salary_str = str(salary).replace('.', '').replace(',', '.')
        try:
            return Decimal(salary_str)
        except Exception:
            raise forms.ValidationError("Valor inválido")
        
JobTitleFormSet = forms.inlineformset_factory(
    Department,
    JobTitle,
    form=JobTitleForm,
    extra=1,          
    can_delete=True
)