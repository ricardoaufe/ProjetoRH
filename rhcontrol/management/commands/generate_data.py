import random

from django.core.management.base import BaseCommand

from rhcontrol.models import Department, Employee, JobTitle, Vacation


class Command(BaseCommand):
    help = 'Gera setores, cargos e funcionários fictícios e relacionados para testes.'

    def add_arguments(self, parser):
        parser.add_argument('count', type=int, help='Número de funcionários a serem criados')

    def handle(self, *args, **options):
        from faker import Faker
        count = options['count']
        fake = Faker('pt_BR')
        
        self.stdout.write(self.style.NOTICE('=== INICIANDO GERAÇÃO DE DADOS ==='))
        self.stdout.write('Gerando Setores...')
        department_names = [
            'Tecnologia da Informação', 'Recursos Humanos', 
            'Financeiro', 'Produção', 'Logística'
        ]
        created_departments = []
        
        for name in department_names:
            department, created = Department.objects.get_or_create(name=name)
            created_departments.append(department)
            
        self.stdout.write(self.style.SUCCESS(f'{len(created_departments)} Setores garantidos no banco.'))

        # ==========================================
        # 2. CRIAÇÃO DE CARGOS (JobTitles)
        # ==========================================
        self.stdout.write('Gerando Cargos amarrados aos Setores...')
        
        # Dicionário mapeando os Setores aos seus respectivos Cargos possíveis
        jobs_by_department = {
            'Tecnologia da Informação': ['Desenvolvedor Júnior', 'Desenvolvedor Pleno', 'Desenvolvedor Sênior', 'Gerente de TI', 'Suporte Técnico'],
            'Recursos Humanos': ['Analista de RH', 'Assistente de Departamento Pessoal', 'Gerente de RH', 'Recrutador'],
            'Financeiro': ['Analista Financeiro', 'Assistente Administrativo', 'Diretor Financeiro', 'Contador'],
            'Produção': ['Operador de Máquinas', 'Supervisor de Produção', 'Auxiliar de Produção', 'Técnico de Manutenção'],
            'Logística': ['Estoquista', 'Analista de Logística', 'Motorista', 'Coordenador de Frota']
        }

        for department in created_departments:
            department_jobs = jobs_by_department.get(department.name, ['Auxiliar Geral'])
            for job_name in department_jobs:
                random_salary = round(random.uniform(1500.0, 12000.0), 2)
                JobTitle.objects.get_or_create(
                    name=job_name,
                    department=department,
                    defaults={'base_salary': random_salary, 'description': f'Descrição padrão para {job_name}'}
                )
                
        self.stdout.write(self.style.SUCCESS('Cargos criados e vinculados aos setores com sucesso.'))

        # ==========================================
        # 3. CRIAÇÃO DE FUNCIONÁRIOS
        # ==========================================
        self.stdout.write(f'Gerando {count} Funcionários com dados obrigatórios...')
        created_employees = []
        used_cpfs = set() # Controle local para evitar repetição de CPF no sorteio do Faker

        for _ in range(count):
            # Garante que o Faker não gere um CPF repetido nesta mesma rodada
            cpf = fake.cpf()
            while cpf in used_cpfs:
                cpf = fake.cpf()
            used_cpfs.add(cpf)
            
            # Sorteia um setor
            random_department = random.choice(created_departments)
            
            # Pega todos os cargos que pertencem ÚNICA E EXCLUSIVAMENTE ao setor sorteado
            # (Utiliza o related_name 'job_titles' definido no seu models.py)
            valid_jobs = list(random_department.job_titles.all())
            random_job = random.choice(valid_jobs)
            
            try:
                emp = Employee.objects.create(
                    name=fake.name(),
                    cpf=cpf,
                    birth_date=fake.date_of_birth(minimum_age=18, maximum_age=65),
                    current_salary=random_job.base_salary,
                    department=random_department,
                    job_title=random_job
                )
                created_employees.append(emp)
                
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'Erro ao criar funcionário: {e}'))

        self.stdout.write(self.style.SUCCESS(f'{len(created_employees)} Funcionários criados com sucesso!'))
        self.stdout.write(self.style.NOTICE('=== GERAÇÃO FINALIZADA ==='))

        self.stdout.write('Gerando histórico de Férias...')
        created_vacations = 0

        for emp in created_employees:

            if random.random() < 0.40:
                start_date = fake.date_between(start_date='-1y', end_date='+1y')
                duration = random.choice([10, 15, 20, 30])
                
                try:
                    Vacation.objects.create(
                        employee=emp,
                        start_date=start_date,
                        vacation_duration=duration
                    )
                    created_vacations += 1
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f'Erro ao criar férias para {emp.name}: {e}'))

        self.stdout.write(self.style.SUCCESS(f'{created_vacations} registros de Férias criados com sucesso!'))
        self.stdout.write(self.style.NOTICE('=== GERAÇÃO FINALIZADA ==='))