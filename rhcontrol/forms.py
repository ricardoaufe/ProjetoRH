from datetime import date, timezone
from decimal import Decimal
from django import forms 
from django.contrib.auth.models import Group, User
from rhcontrol.models import Dependent, Employee, JobTitle, NotificationRecipient, NotificationRule, Training, UserAlertPreference, Vacation, Department, CareerPlan, Occurrence

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

def validate_cpf(cpf):
    if not cpf: return True 

    clean_cpf = ''.join([c for c in cpf if c.isdigit()])

    if len(clean_cpf) != 11: return False

    if clean_cpf == clean_cpf[0] * 11: return False

    add = sum(int(clean_cpf[i]) * (10 - i) for i in range(9))
    rest = (add * 10) % 11
    if rest == 10: rest = 0
    if rest != int(clean_cpf[9]): return False

    add = sum(int(clean_cpf[i]) * (11 - i) for i in range(10))
    rest = (add * 10) % 11
    if rest == 10: rest = 0
    if rest != int(clean_cpf[10]): return False

    return True

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

    special_workday_other = forms.CharField(
        label='Qual Trabalho Especial?',
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Descreva o trabalho especial'})
    )

    completed_integration_trainings = forms.BooleanField(
        label="Concluiu os Treinamentos de Integração?",
        required=False,
        help_text="Se marcado, os treinamentos padrão serão automaticamente registrados no histórico deste funcionário."
    )

    
    class Meta:
        model = Employee
        fields = '__all__'
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control uppercase-input'}),
            'mother_name': forms.TextInput(attrs={'class': 'form-control uppercase-input'}),
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
            'cpf': forms.TextInput(attrs={'class': 'form-control cpf-input', 'placeholder': '000.000.000-00'}),
            'mobile_phone': forms.TextInput(attrs={'class': 'form-control phone-input', 'placeholder': '(00) 00000-0000'}),
            'emergency_phone': forms.TextInput(attrs={'class': 'form-control phone-input', 'placeholder': '(00) 00000-0000'}),
            'zip_code': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '00000-000'}),        
            }
        
    def clean_cpf(self):
        cpf = self.cleaned_data.get('cpf')
        if not validate_cpf(cpf):
            raise forms.ValidationError("CPF Inválido ou Inexistente.")
        return cpf
    
    def clean_birth_date(self):
        birth_date = self.cleaned_data.get('birth_date')
        
        if birth_date:
            today = date.today()
            age = today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))
            if age < 18:
                raise forms.ValidationError("O funcionário deve ter pelo menos 18 anos.")
            
            if age > 100:
                raise forms.ValidationError("Idade inválida. Verifique o ano de nascimento (Máx: 100 anos).")
        return birth_date
    
    
    def clean_name(self):
        name = self.cleaned_data.get('name')
        if name:
            return name.upper()
        return name

    def clean_mother_name(self):
        mother_name = self.cleaned_data.get('mother_name')
        if mother_name:
            return mother_name.upper()
        return mother_name
        
    def clean_current_salary(self):
        salary = self.cleaned_data.get('current_salary')
        if not salary: return None
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
        
    def clean(self):
        cleaned_data = super().clean()

        hire_date = cleaned_data.get('hire_date')
        termination_date = cleaned_data.get('termination_date')

        if hire_date and termination_date:
            if termination_date < hire_date:
                self.add_error(
                    'termination_date', 
                    'A data de demissão não pode ser anterior à data de admissão.'
                )

        special_workday = cleaned_data.get('special_workday')
        special_workday_other = cleaned_data.get('special_workday_other')

        if special_workday == 'Outro' and not special_workday_other:
            self.add_error('special_workday_other', 'Por favor, especifique qual é o trabalho especial.')
        
        if special_workday != 'Outro':
            cleaned_data['special_workday_other'] = ''

        return cleaned_data

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if self.instance and self.instance.pk:
            fez_integracao = self.instance.attended_trainings.filter(is_integration=True).exists()
            self.fields['completed_integration_trainings'].initial = fez_integracao

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
                
    def save(self, commit=True):
        employee = super().save(commit=False)

        old_save_m2m = self.save_m2m if hasattr(self, 'save_m2m') else lambda: None
        
        def custom_save_m2m():
            old_save_m2m()
            
            integration_trainings = Training.objects.filter(is_integration=True)
            
            if self.cleaned_data.get('completed_integration_trainings'):
                for training in integration_trainings:
                    training.scheduled_employees.add(employee)
                    training.attended_employees.add(employee)
            else:
                for training in integration_trainings:
                    training.scheduled_employees.remove(employee)
                    training.attended_employees.remove(employee)

        self.save_m2m = custom_save_m2m
        
        if commit:
            employee.save()
            self.save_m2m() 

        return employee

class DependentForm(forms.ModelForm):
    class Meta:
        model = Dependent
        fields = ['name', 'cpf', 'birth_date', 'relationship_type', 'has_disability']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control uppercase-input', 'placeholder': 'Nome Completo'}),
            'cpf': forms.TextInput(attrs={'class': 'form-control cpf-input cpf-input', 'placeholder': '000.000.000-00'}),
            'birth_date': forms.DateInput(format='%Y-%m-%d', attrs={'type': 'date', 'class': 'form-control'}),
            'relationship_type': forms.Select(attrs={'class': 'form-control form-select'}),
        }
    def clean_name(self):
        name = self.cleaned_data.get('name')
        if name:
            return name.upper()
        return name
    
    def clean_cpf(self):
        cpf = self.cleaned_data.get('cpf')
        if not validate_cpf(cpf):
            raise forms.ValidationError("CPF Inválido ou Inexistente.")
        return cpf

DependentFormSet = forms.inlineformset_factory(
    Employee,
    Dependent,
    form=DependentForm,
    extra=0,
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
            'start_date': forms.DateInput(format='%Y-%m-%d', attrs={'class': 'form-control', 'type': 'date'}),
            'end_date': forms.DateInput(format='%Y-%m-%d', attrs={'class': 'form-control', 'type': 'date'}),
            'training_total_hours': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Ex: 8'}),
            'is_fundamental': forms.CheckboxInput(attrs={'class': 'form-check-input', 'id': 'id_is_fundamental'}),
            'target_department': forms.Select(attrs={'class': 'form-control', 'id': 'id_target_department'}),
            'scheduled_employees': forms.SelectMultiple(attrs={'class': 'form-control', 'size': '10', 'id': 'id_scheduled_employees'}),
            'attended_employees': forms.SelectMultiple(attrs={'class': 'form-control', 'size': '10'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')

        if start_date and end_date and end_date < start_date:
            self.add_error('end_date', 'A data de término não pode ser anterior à data de início.')

        return cleaned_data

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            self.fields['attended_employees'].queryset = self.instance.scheduled_employees.all()
        else:
            self.fields['attended_employees'].queryset = Employee.objects.none()

class OccurrenceForm(forms.ModelForm):
    class Meta:
        model = Occurrence

        fields = ['title', 'description', 'occurrence_date', 'is_absence', 'end_date']
        
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Título da ocorrência',
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Descreva a ocorrência...',
            }),
            'occurrence_date': forms.DateInput(
                format='%Y-%m-%d',
                attrs={'class': 'form-control', 'type': 'date'},
            ),

            'end_date': forms.DateInput(
                format='%Y-%m-%d',
                attrs={'class': 'form-control', 'type': 'date'},
            ),

            'is_absence': forms.CheckboxInput(
                attrs={'class': 'form-check-input'}
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.instance.pk and not self.initial.get('occurrence_date'):
            from django.utils import timezone as django_tz
            self.initial['occurrence_date'] = django_tz.localdate()

    def clean_occurrence_date(self):
        from django.utils import timezone as django_tz
        date = self.cleaned_data.get('occurrence_date')
        if date and date > django_tz.localdate():
            raise forms.ValidationError("A data não pode ser no futuro.")
        return date

    def clean(self):
        cleaned_data = super().clean()
        
        is_absence = cleaned_data.get('is_absence')
        occurrence_date = cleaned_data.get('occurrence_date')
        end_date = cleaned_data.get('end_date')

        if not is_absence:
            cleaned_data['end_date'] = None

        else:
            if end_date and occurrence_date and end_date < occurrence_date:
                self.add_error('end_date', 'A data de fim não pode ser anterior à data de início.')

        return cleaned_data


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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk and self.instance.base_salary:
            self.initial['base_salary'] = f'{self.instance.base_salary:.2f}'.replace('.', ',')

    def clean_base_salary(self):
        salary = self.cleaned_data.get('base_salary')
        if not salary: 
            return None
        
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
    extra=0,          
    can_delete=True
)



class CareerPlanForm(forms.ModelForm):
    proposed_department = forms.ModelChoiceField(
        queryset=Department.objects.all(),
        label='Novo Setor',
        required=True
    )

    class Meta:
        model = CareerPlan
        fields = ['employee', 'proposed_department', 'proposed_job', 'proposed_salary', 'promotion_date']
        
        widgets = {
            'promotion_date': forms.DateInput(attrs={'type': 'date'}),
            'proposed_salary': forms.TextInput(attrs={'placeholder': '0,00', 'class': 'money-input'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        for field in self.fields.values():
            if 'class' in field.widget.attrs:
                field.widget.attrs['class'] += ' form-control'
            else:
                field.widget.attrs['class'] = 'form-control'
                
        if self.instance and self.instance.pk:
            self.fields['employee'].disabled = True

        self.fields['proposed_job'].queryset = JobTitle.objects.none()

        if 'proposed_department' in self.data:
            try:
                department_id = int(self.data.get('proposed_department'))
                self.fields['proposed_job'].queryset = JobTitle.objects.filter(
                    department_id=department_id
                ).order_by('name')
            except (ValueError, TypeError):
                pass 

        elif self.instance.pk and self.instance.proposed_job:
            self.fields['proposed_department'].initial = self.instance.proposed_job.department
            self.fields['proposed_job'].queryset = JobTitle.objects.filter(
                department=self.instance.proposed_job.department
            ).order_by('name')

class RoleGroupForm(forms.ModelForm):
    class Meta:
        model = Group
        fields = ['name']
        labels = {
            'name': 'Nome do Perfil de Acesso',
        }
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nome do Perfil de Acesso'}),
        }

    def save(self, commit=True):
        group = super().save(commit=False)
        if commit:
            group.save()
        
        return group
    

class SystemUserForm(forms.ModelForm):
    role = forms.ModelChoiceField(
        queryset=Group.objects.all(),
        label="Perfil de Acesso (Cargo)",
        empty_label="Selecione um perfil",
        widget=forms.Select(attrs={'class': 'form-control'})
    )

    password = forms.CharField(
        label="Senha Temporária",
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Digite uma senha inicial'})
    )

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'username']
        labels = {
            'first_name': 'Nome',
            'last_name': 'Sobrenome',
            'username': 'Nome de Usuário (Login)'
        }
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'username': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: joao.silva'}),
        }

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password'])
        user.is_superuser = False
        user.is_staff = False 
        
        if commit:
            user.save()
            role = self.cleaned_data['role']
            user.groups.set([role]) #
            
        return user

class SystemUserUpdateForm(forms.ModelForm):
    role = forms.ModelChoiceField(
        queryset=Group.objects.all(),
        label="Perfil de Acesso (Cargo)",
        empty_label="Selecione um perfil",
        widget=forms.Select(attrs={'class': 'form-control'})
    )

    receive_all_events = forms.BooleanField(
        label="Receber notificações de TODOS os eventos",
        required=False,
        widget=forms.CheckboxInput(attrs={'id': 'id_receive_all'})
    )

    alerts = forms.ModelMultipleChoiceField(
        queryset=NotificationRule.objects.filter(is_active=True),
        widget=forms.CheckboxSelectMultiple,
        label="Notificações Específicas",
        required=False 
    )

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'username']
        labels = {
            'first_name': 'Nome',
            'last_name': 'Sobrenome',
            'username': 'Nome de Usuário (Login)'
        }
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'username': forms.TextInput(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:

            grupo_atual = self.instance.groups.first()
            if grupo_atual:
                self.fields['role'].initial = grupo_atual

            email = self.instance.email
            if email:
                recipient = NotificationRecipient.objects.filter(email=email).first()
                if recipient:
                    self.fields['receive_all_events'].initial = recipient.receive_all_events
                    self.fields['alerts'].initial = recipient.subscribed_rules.all()

    def clean(self):
        cleaned_data = super().clean()
        email = cleaned_data.get('email')
        alerts = cleaned_data.get('alerts')
        receive_all = cleaned_data.get('receive_all_events')

        if (alerts or receive_all) and not email:
            self.add_error('email', 'Para ativar alertas, é obrigatório cadastrar um e-mail.')
            self.add_error('receive_all_events', 'Preencha o e-mail antes de ativar as notificações.')

        return cleaned_data

    def save(self, commit=True):

        old_email = None
        if self.instance.pk:
            old_email = User.objects.get(pk=self.instance.pk).email

        user = super().save(commit=False)
        if commit:
            user.save()

            role = self.cleaned_data.get('role')
            if role:
                user.groups.set([role])
            else:
                user.groups.clear()

            email = self.cleaned_data.get('email')
            receive_all = self.cleaned_data.get('receive_all_events', False)
            alerts = self.cleaned_data.get('alerts', [])

            if email:

                recipient = NotificationRecipient.objects.filter(email=old_email).first()
                if not recipient:
                    recipient = NotificationRecipient.objects.filter(email=email).first()

                if alerts or receive_all:
                    if not recipient:
                        recipient = NotificationRecipient(email=email)
                    
                    nome_completo = f"{user.first_name} {user.last_name}".strip()
                    recipient.name = nome_completo if nome_completo else user.username
                    recipient.email = email
                    recipient.receive_all_events = receive_all
                    recipient.is_active = True
                    recipient.save()

                    if receive_all:
                        recipient.subscribed_rules.clear() 
                        recipient.subscribed_rules.set(alerts)

                else:
                    if recipient:
                        recipient.receive_all_events = False
                        recipient.subscribed_rules.clear()
                        recipient.is_active = False 
                        recipient.save()

        return user