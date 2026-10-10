from datetime import timedelta

from django.db import models
from django.db.models import Q
from django.utils import timezone

from .organization import Department, JobTitle


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

    DISABILITY_TYPE_CHOICES = [
        ('Física', 'Física'),
        ('Visual', 'Visual'),
        ('Auditiva', 'Auditiva'),
        ('Mental', 'Mental'),
        ('Intelectual', 'Intelectual'),
        ('Múltipla', 'Múltipla'),
    ]
    disability_type = models.CharField(max_length=50, choices=DISABILITY_TYPE_CHOICES, blank=True, null=True, verbose_name="Tipo de Deficiência") 
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

    ACCOUNT_TYPE_CHOICES = [
        ('Corrente', 'Corrente'),
        ('Poupança', 'Poupança'),
        ('Salário', 'Salário'),
        ('Conta Conjunta', 'Conta Conjunta'),
    ]
    account_type = models.CharField(max_length=25, choices=ACCOUNT_TYPE_CHOICES, blank=True, null=True, verbose_name="Tipo de Conta") 

    # DADOS DO CONTRATO
    department = models.ForeignKey(Department, on_delete=models.PROTECT, verbose_name='Setor', related_name='funcionarios_setor') 
    job_title = models.ForeignKey(JobTitle, on_delete=models.PROTECT, verbose_name='Cargo', related_name='funcionarios_cargo') 
    current_salary = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True, verbose_name='Salário Atual') 
    hire_date = models.DateField(blank=True, null=True, verbose_name="Data de Admissão")
    contract_end_date = models.DateField(blank=True, null=True, verbose_name="Fim do Contrato (Prazo Determinado)") 
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

    def check_cipa_expiration(self):
        """
        Verifies if the total time (Mandate + 1 Year Stability) has expired.
        If it has expired, clears the fields to allow a new election.
        """
        if not self.is_cipa_member or not self.cipa_mandate_end_date:
            return

        today = timezone.localdate()
        stability_end_date = self.cipa_mandate_end_date + timedelta(days=365)
        
        if today > stability_end_date:
            self.is_cipa_member = False
            self.cipa_role = None
            self.cipa_mandate_start_date = None
            self.cipa_mandate_end_date = None
            self.save(update_fields=[
                'is_cipa_member', 'cipa_role',
                'cipa_mandate_start_date', 'cipa_mandate_end_date'
            ])

    @property
    def cipa_status(self):

        if not self.is_cipa_member or not self.cipa_mandate_end_date:
            return None
        
        today = timezone.localdate()
        
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
            street = f"{self.address}"
            if self.address_num:
                street += f", {self.address_num}"
            parts.append(street)
            
        if self.complement:
            parts.append(self.complement)
            
        if self.neighborhood:
            parts.append(self.neighborhood)
            
        city_state = ""
        if self.city:
            city_state += self.city
        if self.state_code:
            city_state += f"/{self.state_code}"
            
        if city_state:
            parts.append(city_state)
            
        if self.zip_code:
            parts.append(f"{self.zip_code}")

        return ", ".join(parts) + "." if parts else "Endereço não cadastrado."

    @property
    def company_tenure(self):
        if not self.hire_date:
            return "-"
        
        today = timezone.localdate()
        
        if self.hire_date > today:
            return "Não possui tempo de empresa ainda"
        
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
            result.append(f"{months} {'mês' if months == 1 else 'meses'}")
            
        return " e ".join(result) if result else "Menos de 1 mês"
    
    @staticmethod
    def active_leave_q(today):
        """Filtro de ocorrência que é um afastamento em andamento na data."""
        return Q(is_absence=True, occurrence_date__lte=today) & (
            Q(end_date__isnull=True) | Q(end_date__gte=today)
        )

    @property
    def is_on_leave(self):
        return self.occurrences.filter(self.active_leave_q(timezone.localdate())).exists()

    def __str__(self):
        return self.name