from django.db import models
from datetime import timedelta
import holidays 


class Vacation(models.Model):
    employee = models.ForeignKey('Employee', on_delete=models.CASCADE, related_name='vacations')
    start_date = models.DateField(verbose_name="Data de Início")
    end_date = models.DateField(blank=True, null=True, verbose_name="Data de Fim")
    return_date = models.DateField(blank=True, null=True, verbose_name="Data de Retorno")
    vacation_duration= models.IntegerField(help_text='Duração em dias', verbose_name="Duração")

    #Função para verificação de feriados/dias não úteis + cálculo de data de término
    def save(self, *args, **kwargs):
        if self.start_date and self.vacation_duration:

            self.end_date = self.start_date + timedelta(days=self.vacation_duration) # Calcula a data de término com base na duração
            next_day = self.end_date + timedelta(days=1) # A data retorno é o dia após o término das férias
            br_holidays = holidays.Brazil()

            while next_day.weekday() >= 5 or next_day in br_holidays: # Verifica se é sábado, domingo ou feriado
                next_day += timedelta(days=1)
            self.return_date = next_day

        super().save(*args, **kwargs)

    def __str__(self):
        return f'Férias do(a) {self.employee.name} até {self.start_date} para {self.end_date}'
    
class Training(models.Model):
    training_name = models.CharField(max_length=200, verbose_name="Nome do Treinamento")
    training_date = models.DateField(verbose_name="Data do Treinamento")
    training_provider = models.CharField(max_length=200, blank=True, null=True, verbose_name="Fornecedor do Treinamento")
    training_duration = models.IntegerField(help_text='Duração em horas', verbose_name="Duração (horas)")
    training_description = models.TextField(blank=True, null=True, verbose_name="Descrição do Treinamento")

    is_fundamental = models.BooleanField(default=False, verbose_name="É Treinamento Fundamental?")
    target_department = models.ForeignKey('Department', on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Setor Alvo (Se Fundamental)")
    
    scheduled_employees = models.ManyToManyField('Employee', related_name='scheduled_trainings', blank=True, verbose_name="Funcionários Previstos")
    attended_employees = models.ManyToManyField('Employee', related_name='attended_trainings', blank=True, verbose_name="Funcionários Que Compareceram")

    def __str__(self):
        return f'Treinamento: {self.training_name} para {self.employee.name} em {self.training_date}'

class Department(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.name

class JobTitle(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name='job_titles')
    base_salary= models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return self.name
    
class EmployeeHistory(models.Model):
    employee = models.ForeignKey('Employee' , on_delete=models.CASCADE, related_name='history')
    date_changed = models.DateField(auto_now_add=True, verbose_name="Data da Mudança")
    
    old_job_title = models.CharField(max_length=200, null=True, verbose_name="Cargo Anterior")
    new_job_title = models.CharField(max_length=200, null=True, verbose_name="Novo Cargo")
    
    old_salary = models.DecimalField(max_digits=10, decimal_places=2, null=True, verbose_name="Salário Anterior")
    new_salary = models.DecimalField(max_digits=10, decimal_places=2, null=True, verbose_name="Novo Salário")
    
    reason = models.CharField(max_length=200, blank=True, verbose_name="Motivo")

    def __str__(self):
        return f"Histórico de {self.employee.name} - {self.date_changed}"

class Employee(models.Model):
    name = models.CharField(max_length=100, verbose_name="Nome")
    cpf = models.CharField(max_length=14, unique=True, verbose_name="CPF")
    rg = models.CharField(max_length=20, blank=True, null=True, verbose_name="RG")
    rg_issue_date = models.DateField(blank=True, null=True, verbose_name="Data de Emissão do RG") 
    ctps_number = models.CharField(max_length=20, blank=True, null=True, verbose_name="Número da CTPS")
    ctps_series = models.CharField(max_length=10, blank=True, null=True, verbose_name="Série da CTPS")
    ctps_issue_date = models.DateField(blank=True, null=True, verbose_name="Data de Emissão da CTPS") 
    pis = models.CharField(max_length=20, blank=True, null=True, verbose_name="PIS")
    ethnicity = models.CharField(max_length=50, blank=True, null=True, verbose_name="Etnia")
    mother_name = models.CharField(max_length=100, blank=True, null=True, verbose_name="Nome da Mãe")
    birth_city = models.CharField(max_length=100, blank=True, null=True, verbose_name="Cidade de Nascimento") 
    state_birthplace_code = models.CharField(max_length=2, blank=True, null=True, verbose_name="UF de Nascimento")
    birth_date = models.DateField(verbose_name="Data de Nascimento") 

    SEX_CHOICES = [
        ('M', 'Masculino'),
        ('F', 'Feminino'),
        ('O', 'Outro'),
    ]
    gender = models.CharField(max_length=1, choices=SEX_CHOICES, blank=True, null=True, verbose_name="Gênero") 

    EDUCATION_CHOICES = [
        ('Analfabeto(a)', 'Analfabeto'),
        ('Fundamental Incompleto', 'Fundamental Incompleto'),
        ('Fundamental Completo', 'Fundamental Completo'),
        ('Médio Incompleto', 'Médio Incompleto'),
        ('Médio Completo', 'Médio Completo'),
        ('Superior Incompleto', 'Superior Incompleto'),
        ('Superior Completo', 'Superior Completo'),
        ('Pós-graduação', 'Pós-graduação'),
        ('Mestrado', 'Mestrado'),
        ('Doutorado', 'Doutorado'),
    ]
    education_level = models.CharField(max_length=22, choices=EDUCATION_CHOICES, blank=True, null=True, verbose_name="Nível de Escolaridade") 

    RETIREMENT_CHOICES = [
        ('I', 'Por Idade'),
        ('T', 'Por Tempo de Contribuição'),
        ('N', 'Não recebe'),
    ]
    retirement_status = models.CharField(max_length=1, choices=RETIREMENT_CHOICES, blank=True, null=True, verbose_name="Status de Aposentadoria")

    CIVIL_STATUS_CHOICES = [
        ('S', 'Solteiro(a)'),
        ('C', 'Casado(a)'),
        ('D', 'Divorciado(a)'),
        ('V', 'Viúvo(a)'),
        ('E', 'Separado(a)'),
        ('U', 'União Estável'),
    ]
    marital_status = models.CharField(max_length=1, choices= CIVIL_STATUS_CHOICES, blank=True, null=True, verbose_name="Estado Civil") 

    is_pcd = models.BooleanField(default=False, verbose_name="Pessoa com Deficiência (PCD)")    

    TIPO_DEFICIENCIA_CHOICES = [
        ('Física', 'Física'),
        ('Visual', 'Visual'),
        ('Auditiva', 'Auditiva'),
        ('Mental', 'Mental'),
        ('Intelectual', 'Intelectual'),
        ('Múltipla', 'Múltipla'),
    ]
    disability_type = models.CharField(max_length=50, choices=TIPO_DEFICIENCIA_CHOICES, blank=True, null=True, verbose_name="Tipo de Deficiência") 

    # DADOS DE CONTATO
    address = models.CharField(max_length=200, blank=True, null=True, verbose_name="Endereço") 
    address_num = models.CharField(max_length=10, blank=True, null=True, verbose_name="Número") 
    complement = models.CharField(max_length=50, blank=True, null=True, verbose_name="Complemento")
    neighborhood = models.CharField(max_length=100, blank=True, null=True, verbose_name="Bairro") 
    city = models.CharField(max_length=100, blank=True, null=True, verbose_name="Cidade")
    state_code = models.CharField(max_length=2, blank=True, null=True, verbose_name="UF")
    zip_code = models.CharField(max_length=9, blank=True, null=True, verbose_name="CEP") 
    emergency_phone = models.CharField(max_length=20, blank=True, null=True, verbose_name="Telefone de Emergência") 
    emergency_contact_name = models.CharField(max_length=100, blank=True, null=True, verbose_name="Nome do Contato de Emergência") 
    mobile_phone = models.CharField(max_length=20, blank=True, null=True, verbose_name="Celular") 
    email = models.EmailField(blank=True, null=True, verbose_name="E-mail")

    # DADOS BANCÁRIOS
    bank_name = models.CharField(max_length=100, blank=True, null=True, verbose_name="Banco") 
    account_num = models.CharField(max_length=50, blank=True, null=True, verbose_name="Número da Conta") 
    bank_agency_code = models.CharField(max_length=20, blank=True, null=True, verbose_name="Agência") 

    TIPO_CONTA_CHOICES = [
        ('Corrente', 'Corrente'),
        ('Poupança', 'Poupança'),
        ('Salário', 'Salário'),
        ('Conta Conjunta', 'Conta Conjunta'),
    ]
    account_type = models.CharField(max_length=25, choices=TIPO_CONTA_CHOICES, blank=True, null=True, verbose_name="Tipo de Conta") 

    # DADOS DO CONTRATO
    department = models.ForeignKey(Department, on_delete=models.PROTECT, verbose_name='Setor', related_name='funcionarios_setor') 
    job_title = models.ForeignKey(JobTitle, on_delete=models.PROTECT, verbose_name='Cargo', related_name='funcionarios_cargo') 
    current_salary = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True, verbose_name='Salário Atual') 
    hire_date = models.DateField(blank=True, null=True, verbose_name="Data de Admissão") 
    is_trial_contract = models.BooleanField(default=False, verbose_name="Contrato em Período de Experiência") 
    is_first_job = models.BooleanField(default=False, verbose_name="Primeiro Emprego") 
    is_intermittent_contract = models.BooleanField(default=False, verbose_name="Contrato Intermitente") 
    uses_transport_voucher = models.BooleanField(default=False, verbose_name="Usa Vale Transporte") 
    has_insalubrity_bonus = models.BooleanField(default=False, verbose_name="Recebe Adicional de Insalubridade") 
    has_danger_bonus = models.BooleanField(default=False, verbose_name="Recebe Adicional de Periculosidade") 
    admission_exam_date = models.DateField(blank=True, null=True, verbose_name="Data do Exame Admissional") 
    termination_date = models.DateField(blank=True, null=True, verbose_name="Data da Demissão") 
    termination_reason = models.CharField(max_length=200, blank=True, null=True, verbose_name="Motivo da Demissão")

    # DADOS DE ESTRANGEIROS
    is_foreign = models.BooleanField(default=False, verbose_name="É Estrangeiro") 
    arrival_date = models.DateField(blank=True, null=True, verbose_name="Data de Chegada") 
    naturalization_date = models.DateField(blank=True, null=True, verbose_name="Data de Naturalização") 
    married_to_brazilian = models.BooleanField(default=False, verbose_name="Casado com Brasileiro") 
    has_brazilian_children = models.BooleanField(default=False, verbose_name="Tem Filhos Brasileiros") 
    rne_number = models.CharField(max_length=50, blank=True, null=True, verbose_name="Número do RNE") 
    rne_issuing_authority = models.CharField(max_length=50, blank=True, null=True, verbose_name="Autoridade Emissora do RNE") 
    rne_issue_date = models.DateField(blank=True, null=True, verbose_name="Data de Emissão do RNE") 

    # DADOS DA CIPA
    is_cipa_member = models.BooleanField(default=False, verbose_name="Integrante da CIPA") 
    cipa_mandate_start_date = models.DateField(blank=True, null=True, verbose_name="Início do Mandato na CIPA") 
    cipa_mandate_end_date = models.DateField(blank=True, null=True, verbose_name="Fim do Mandato na CIPA") 
    cipa_role = models.CharField(max_length=100, blank=True, null=True, verbose_name="Função na CIPA") 

    def __str__(self):
        return self.name