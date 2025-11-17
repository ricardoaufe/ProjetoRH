from django.db import models

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

class Employee(models.Model):
    name = models.CharField(max_length=100)
    cpf = models.CharField(max_length=14, unique=True)
    rg = models.CharField(max_length=20, blank=True, null=True)
    rg_issue_date = models.DateField(blank=True, null=True) 
    ctps_number = models.CharField(max_length=20, blank=True, null=True)
    ctps_series = models.CharField(max_length=10, blank=True, null=True)
    ctps_issue_date = models.DateField(blank=True, null=True) 
    pis = models.CharField(max_length=20, blank=True, null=True)
    ethnicity = models.CharField(max_length=50, blank=True, null=True)
    mother_name = models.CharField(max_length=100, blank=True, null=True)
    birth_city = models.CharField(max_length=100, blank=True, null=True) 
    state_birthplace_code = models.CharField(max_length=2, blank=True, null=True)
    birth_date = models.DateField() 

    SEX_CHOICES = [
        ('M', 'Masculino'),
        ('F', 'Feminino'),
        ('O', 'Outro'),
    ]
    gender = models.CharField(max_length=1, choices=SEX_CHOICES, blank=True, null=True) 

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
    education_level = models.CharField(max_length=22, choices=EDUCATION_CHOICES, blank=True, null=True) 

    RETIREMENT_CHOICES = [
        ('I', 'Por Idade'),
        ('T', 'Por Tempo de Contribuição'),
        ('N', 'Não recebe'),
    ]
    retirement_status = models.CharField(max_length=1, choices=RETIREMENT_CHOICES, blank=True, null=True)

    CIVIL_STATUS_CHOICES = [
        ('S', 'Solteiro(a)'),
        ('C', 'Casado(a)'),
        ('D', 'Divorciado(a)'),
        ('V', 'Viúvo(a)'),
        ('E', 'Separado(a)'),
        ('U', 'União Estável'),
    ]
    marital_status = models.CharField(max_length=1, choices= CIVIL_STATUS_CHOICES, blank=True, null=True) 

    PCD_CHOICES = [
        ('S', 'Sim'),
        ('N', 'Não'),
    ]
    is_pcd = models.CharField(max_length=1, choices=PCD_CHOICES, blank=True, null=True) 

    TIPO_DEFICIENCIA_CHOICES = [
        ('Física', 'Física'),
        ('Visual', 'Visual'),
        ('Auditiva', 'Auditiva'),
        ('Mental', 'Mental'),
        ('Intelectual', 'Intelectual'),
        ('Múltipla', 'Múltipla'),
    ]
    disability_type = models.CharField(max_length=50, choices=TIPO_DEFICIENCIA_CHOICES, blank=True, null=True) 

    # DADOS DE CONTATO
    address = models.CharField(max_length=200, blank=True, null=True) 
    address_num = models.CharField(max_length=10, blank=True, null=True) 
    complement = models.CharField(max_length=50, blank=True, null=True)
    neighborhood = models.CharField(max_length=100, blank=True, null=True) 
    city = models.CharField(max_length=100, blank=True, null=True)
    state_code = models.CharField(max_length=2, blank=True, null=True)
    zip_code = models.CharField(max_length=9, blank=True, null=True) 
    emergency_phone = models.CharField(max_length=20, blank=True, null=True) 
    emergency_contact_name = models.CharField(max_length=100, blank=True, null=True) 
    mobile_phone = models.CharField(max_length=20, blank=True, null=True) 
    email = models.EmailField(blank=True, null=True)

    # DADOS BANCÁRIOS
    bank_name = models.CharField(max_length=100, blank=True, null=True) 
    account_num = models.CharField(max_length=50, blank=True, null=True) 
    bank_agency_code = models.CharField(max_length=20, blank=True, null=True) 

    TIPO_CONTA_CHOICES = [
        ('Corrente', 'Corrente'),
        ('Poupança', 'Poupança'),
        ('Salário', 'Salário'),
        ('Conta Conjunta', 'Conta Conjunta'),
    ]
    account_type = models.CharField(max_length=25,choices=TIPO_CONTA_CHOICES, blank=True, null=True) 

    # DADOS DO CONTRATO
    department = models.ForeignKey(Department, on_delete=models.PROTECT, verbose_name='Setor', related_name='funcionarios_setor') 
    job_title = models.ForeignKey(JobTitle, on_delete=models.PROTECT, verbose_name='Cargo', related_name='funcionarios_cargo') 
    current_salary = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True, verbose_name='Salário Atual') 
    hire_date = models.DateField(blank=True, null=True) 
    is_trial_contract = models.BooleanField(default=False) 
    is_first_job = models.BooleanField(default=False) 
    is_intermittent_contract = models.BooleanField(default=False) 
    uses_transport_voucher = models.BooleanField(default=False) 
    has_insalubrity_bonus = models.BooleanField(default=False) 
    has_danger_bonus = models.BooleanField(default=False) 
    admission_exam_date = models.DateField(blank=True, null=True) 
    termination_date = models.DateField(blank=True, null=True, verbose_name="Data da Demissão") 
    termination_reason = models.CharField(max_length=200, blank=True, null=True, verbose_name="Motivo da Demissão")

    # DADOS DE ESTRANGEIROS
    is_foreign = models.BooleanField(default=False) 
    arrival_date = models.DateField(blank=True, null=True) 
    naturalization_date = models.DateField(blank=True, null=True) 
    married_to_brazilian = models.BooleanField(default=False) 
    has_brazilian_children = models.BooleanField(default=False) 
    rne_number = models.CharField(max_length=50, blank=True, null=True) 
    rne_issuing_authority = models.CharField(max_length=50, blank=True, null=True) 
    rne_issue_date = models.DateField(blank=True, null=True) 

    # DADOS DA CIPA
    is_cipa_member = models.BooleanField(default=False, verbose_name="Integrante da CIPA") 
    cipa_mandate_start_date = models.DateField(blank=True, null=True, verbose_name="Início do Mandato na CIPA") 
    cipa_mandate_end_date = models.DateField(blank=True, null=True, verbose_name="Fim do Mandato na CIPA") 
    cipa_role = models.CharField(max_length=100, blank=True, null=True, verbose_name="Título na CIPA") 

    def __str__(self):
        return self.name