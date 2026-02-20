from django.db import models
from datetime import timedelta
from django.utils import timezone
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
    description = models.TextField(verbose_name="Descrição", default="")
    department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name='job_titles')
    base_salary= models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return self.name
    
class EmployeeHistory(models.Model):
    employee = models.ForeignKey('Employee' , on_delete=models.CASCADE, related_name='history')
    date_changed = models.DateField(default=timezone.now, verbose_name="Data da Mudança")
    
    old_job_title = models.CharField(max_length=200, null=True, verbose_name="Cargo Anterior")
    new_job_title = models.CharField(max_length=200, null=True, verbose_name="Novo Cargo")
    
    old_salary = models.DecimalField(max_digits=10, decimal_places=2, null=True, verbose_name="Salário Anterior")
    new_salary = models.DecimalField(max_digits=10, decimal_places=2, null=True, verbose_name="Novo Salário")

    old_cipa_role = models.CharField(max_length=50, null=True, blank=True, verbose_name="CIPA Anterior")
    new_cipa_role = models.CharField(max_length=50, null=True, blank=True, verbose_name="CIPA Nova")
    
    reason = models.CharField(max_length=200, blank=True, verbose_name="Motivo")

    def __str__(self):
        return f"Histórico de {self.employee.name} - {self.date_changed}"
    
class Dependent(models.Model):
    employee = models.ForeignKey('Employee', on_delete=models.CASCADE, related_name='dependents')
    name = models.CharField(max_length=100, verbose_name="Nome Completo")
    cpf = models.CharField(max_length=14, unique=True, verbose_name="CPF")
    birth_date = models.DateField(verbose_name="Data de Nascimento")

    TYPE_CHOICES = [
        ('Filho(a)', 'Filho(a)'),
        ('Cônjuge', 'Cônjuge'),
        ('Pai/Mãe', 'Pai/Mãe'),
        ('Irmão(ã)', 'Irmão(ã)'),
        ('Outro', 'Outro'),
    ]
    relationship_type = models.CharField(max_length=10, choices=TYPE_CHOICES, verbose_name="Parentesco")
    has_disability = models.BooleanField(default=False, verbose_name="Possui Deficiência")

    def __str__(self):
        return self.name
    
class Employee(models.Model):
    name = models.CharField(max_length=100, verbose_name="Nome")
    cpf = models.CharField(max_length=14, unique=True, verbose_name="CPF")
    rg = models.CharField(max_length=20, blank=True, null=True, verbose_name="RG")
    rg_issue_date = models.DateField(blank=True, null=True, verbose_name="Emissão do RG") 
    ctps_number = models.CharField(max_length=20, blank=True, null=True, verbose_name="Número da CTPS")
    ctps_series = models.CharField(max_length=10, blank=True, null=True, verbose_name="Série")
    ctps_issue_date = models.DateField(blank=True, null=True, verbose_name="Emissão da CTPS") 
    pis = models.CharField(max_length=20, blank=True, null=True, verbose_name="PIS")
    registration_number = models.CharField(max_length=5, blank=True, null=True, verbose_name="Matrícula")

    ETHINICITY_CHOICES = [
        ('Branca', 'Branca'),
        ('Preta', 'Preta'),
        ('Parda', 'Parda'),
        ('Amarela', 'Amarela'),
        ('Indígena', 'Indígena'),
    ]
    ethnicity = models.CharField(max_length=10, choices=ETHINICITY_CHOICES, blank=True, null=True, verbose_name="Etnia")

    mother_name = models.CharField(max_length=100, blank=True, null=True, verbose_name="Nome da Mãe")
    birth_city = models.CharField(max_length=100, blank=True, null=True, verbose_name="Cidade de Nascimento") 
    birth_date = models.DateField(verbose_name="Data Nasc.") 

    UF_CHOICES = [
        ('AC', 'AC'),('AL', 'AL'),('AP', 'AP'),('AM', 'AM'),('BA', 'BA'),('CE', 'CE'),('DF', 'DF'),('ES', 'ES'),('GO', 'GO'),
        ('MA', 'MA'),('MT', 'MT'),('MS', 'MS'),('MG', 'MG'),('PA', 'PA'),('PB', 'PB'),('PR', 'PR'),('PE', 'PE'),('PI', 'PI'),
        ('RJ', 'RJ'),('RN', 'RN'),('RS', 'RS'),('RO', 'RO'),('RR', 'RR'),('SC', 'SC'),('SP', 'SP'),('SE', 'SE'),('TO', 'TO'),
    ]
    state_birthplace_code = models.CharField(max_length=2, choices=UF_CHOICES, blank=True, null=True, verbose_name="UF")
    

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
    education_level = models.CharField(max_length=22, choices=EDUCATION_CHOICES, blank=True, null=True, verbose_name="Escolaridade") 

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
    has_dependents = models.BooleanField(default=False, verbose_name="Possui Dependentes")

    # DADOS DE CONTATO
    address = models.CharField(max_length=200, blank=True, null=True, verbose_name="Endereço") 
    address_num = models.CharField(max_length=10, blank=True, null=True, verbose_name="Número") 
    complement = models.CharField(max_length=50, blank=True, null=True, verbose_name="Complemento")
    neighborhood = models.CharField(max_length=100, blank=True, null=True, verbose_name="Bairro") 
    city = models.CharField(max_length=100, blank=True, null=True, verbose_name="Cidade")
    state_code = models.CharField(max_length=2, blank=True, null=True, verbose_name="UF")
    zip_code = models.CharField(max_length=9, blank=True, null=True, verbose_name="CEP") 
    emergency_phone = models.CharField(max_length=20, blank=True, null=True, verbose_name="Telefone") 
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

    WORKDAY_TYPE_CHOICES = [
        ('F - Jornada de semana fixa', 'Fixa'),
        ('V - Jornada de semana variável', 'Variável'),
    ]
    workday_type = models.CharField(max_length=50, choices=WORKDAY_TYPE_CHOICES, blank=True, null=True, verbose_name="Tipo de Jornada")
    working_info = models.CharField(max_length=200, blank=True, null=True, verbose_name="Informações sobre a Jornada de Trabalho (Dias, Horários e Intervalos)")
    SPECIAL_WORKDAY_CHOICES = [
        ('12 X 36', '12 X 36'),
        ('24 X 72', '24 X 72'),
        ('Outro', 'Outro'),
    ]
    special_workday = models.CharField(max_length=20, choices=SPECIAL_WORKDAY_CHOICES, blank=True, null=True, verbose_name="Trabalho Especial")
    special_workday_other = models.CharField(max_length=100, blank=True, null=True, verbose_name="Especificação do Trabalho Especial")

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

    ROLE_CHOICES = [
        ('Titular', 'Titular'),
        ('Suplente', 'Suplente'),
    ] 
    cipa_role = models.CharField(max_length=20, choices=ROLE_CHOICES, blank=True, null=True, verbose_name="Função na CIPA") 

    @property
    def cipa_status(self):

        if not self.is_cipa_member or not self.cipa_mandate_end_date:
            return None
        
        today = timezone.now().date()
        
        start_date = self.cipa_mandate_start_date or self.cipa_mandate_end_date - timedelta(days=365)
        
        if start_date <= today <= self.cipa_mandate_end_date:
            return 'active'
        
        stability_end_date = self.cipa_mandate_end_date + timedelta(days=365)
        
        if self.cipa_mandate_end_date < today <= stability_end_date:
            return 'stability'
            
        return None
    
    @property
    def full_address(self):
        parts = []
        if self.address:
            endereco = f"{self.address}"
            if self.address_num:
                endereco += f", {self.address_num}"
            parts.append(endereco)
            
        if self.complement:
            parts.append(self.complement)
            
        if self.neighborhood:
            parts.append(self.neighborhood)
            
        cidade_estado = ""
        if self.city:
            cidade_estado += self.city
        if self.state_code:
            cidade_estado += f"/{self.state_code}"
            
        if cidade_estado:
            parts.append(cidade_estado)
            
        if self.zip_code:
            parts.append(f"{self.zip_code}")

        return ", ".join(parts) + "." if parts else "Endereço não cadastrado."

    @property
    def company_tenure(self):
        if not self.hire_date:
            return "-"
        
        today = timezone.now().date()
        
        years = today.year - self.hire_date.year
        months = today.month - self.hire_date.month

        if today.day < self.hire_date.day:
            months -= 1

        if months < 0:
            years -= 1
            months += 12
            
        result = []
        if years > 0:
            result.append(f"{years} ano{'s' if years > 1 else ''}")
        if months > 0:
            result.append(f"{months} mês{'es' if months > 1 else ''}")
            

        return " e ".join(result) if result else "Menos de 1 mês"
    
    def check_cipa_expiration(self):
        """
        Verifies if the total time (Mandate + 1 Year Stability) has expired.
        If it has expired, clears the fields to allow a new election.
        """
        if not self.is_cipa_member or not self.cipa_mandate_end_date:
            return

        today = timezone.now().date()
        stability_end_date = self.cipa_mandate_end_date + timedelta(days=365)
        
        if today > stability_end_date:
            self.is_cipa_member = False
            self.cipa_role = None
            self.cipa_mandate_start_date = None
            self.cipa_mandate_end_date = None
            self.save()

    def __str__(self):
        return self.name
