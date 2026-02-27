import random
from django.core.management.base import BaseCommand
from rhcontrol.models import Employee, Department, JobTitle, Vacation

class Command(BaseCommand):
    help = 'Gera setores, cargos e funcionários fictícios e relacionados para testes.'

    def add_arguments(self, parser):
        parser.add_argument('quantidade', type=int, help='Número de funcionários a serem criados')

    def handle(self, *args, **options):
        from faker import Faker
        quantidade = options['quantidade']
        fake = Faker('pt_BR')
        
        self.stdout.write(self.style.NOTICE('=== INICIANDO GERAÇÃO DE DADOS ==='))
        self.stdout.write('Gerando Setores...')
        nomes_setores = [
            'Tecnologia da Informação', 'Recursos Humanos', 
            'Financeiro', 'Produção', 'Logística'
        ]
        setores_criados = []
        
        for nome in nomes_setores:
            setor, created = Department.objects.get_or_create(name=nome)
            setores_criados.append(setor)
            
        self.stdout.write(self.style.SUCCESS(f'{len(setores_criados)} Setores garantidos no banco.'))

        # ==========================================
        # 2. CRIAÇÃO DE CARGOS (JobTitles)
        # ==========================================
        self.stdout.write('Gerando Cargos amarrados aos Setores...')
        
        # Dicionário mapeando os Setores aos seus respectivos Cargos possíveis
        cargos_por_setor = {
            'Tecnologia da Informação': ['Desenvolvedor Júnior', 'Desenvolvedor Pleno', 'Desenvolvedor Sênior', 'Gerente de TI', 'Suporte Técnico'],
            'Recursos Humanos': ['Analista de RH', 'Assistente de Departamento Pessoal', 'Gerente de RH', 'Recrutador'],
            'Financeiro': ['Analista Financeiro', 'Assistente Administrativo', 'Diretor Financeiro', 'Contador'],
            'Produção': ['Operador de Máquinas', 'Supervisor de Produção', 'Auxiliar de Produção', 'Técnico de Manutenção'],
            'Logística': ['Estoquista', 'Analista de Logística', 'Motorista', 'Coordenador de Frota']
        }

        for setor in setores_criados:
            cargos_do_setor = cargos_por_setor.get(setor.name, ['Auxiliar Geral'])
            for nome_cargo in cargos_do_setor:
                salario_aleatorio = round(random.uniform(1500.0, 12000.0), 2)
                JobTitle.objects.get_or_create(
                    name=nome_cargo,
                    department=setor,
                    defaults={'base_salary': salario_aleatorio, 'description': f'Descrição padrão para {nome_cargo}'}
                )
                
        self.stdout.write(self.style.SUCCESS('Cargos criados e vinculados aos setores com sucesso.'))

        # ==========================================
        # 3. CRIAÇÃO DE FUNCIONÁRIOS
        # ==========================================
        self.stdout.write(f'Gerando {quantidade} Funcionários com dados obrigatórios...')
        funcionarios_criados = []
        cpfs_gerados = set() # Controle local para evitar repetição de CPF no sorteio do Faker

        for i in range(quantidade):
            # Garante que o Faker não gere um CPF repetido nesta mesma rodada
            cpf_valido = fake.cpf()
            while cpf_valido in cpfs_gerados:
                cpf_valido = fake.cpf()
            cpfs_gerados.add(cpf_valido)
            
            # Sorteia um setor
            setor_sorteado = random.choice(setores_criados)
            
            # Pega todos os cargos que pertencem ÚNICA E EXCLUSIVAMENTE ao setor sorteado
            # (Utiliza o related_name 'job_titles' definido no seu models.py)
            cargos_validos_do_setor = list(setor_sorteado.job_titles.all())
            cargo_sorteado = random.choice(cargos_validos_do_setor)
            
            try:
                emp = Employee.objects.create(
                    name=fake.name(),
                    cpf=cpf_valido,
                    birth_date=fake.date_of_birth(minimum_age=18, maximum_age=65),
                    current_salary=cargo_sorteado.base_salary,
                    department=setor_sorteado,
                    job_title=cargo_sorteado
                )
                funcionarios_criados.append(emp)
                
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'Erro ao criar funcionário: {e}'))

        self.stdout.write(self.style.SUCCESS(f'{len(funcionarios_criados)} Funcionários criados com sucesso!'))
        self.stdout.write(self.style.NOTICE('=== GERAÇÃO FINALIZADA ==='))

        self.stdout.write('Gerando histórico de Férias...')
        ferias_criadas = 0

        for emp in funcionarios_criados:

            if random.random() < 0.40:
                data_inicio = fake.date_between(start_date='-1y', end_date='+1y')
                duracao = random.choice([10, 15, 20, 30])
                
                try:
                    Vacation.objects.create(
                        employee=emp,
                        start_date=data_inicio,
                        vacation_duration=duracao
                    )
                    ferias_criadas += 1
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f'Erro ao criar férias para {emp.name}: {e}'))

        self.stdout.write(self.style.SUCCESS(f'{ferias_criadas} registros de Férias criados com sucesso!'))
        self.stdout.write(self.style.NOTICE('=== GERAÇÃO FINALIZADA ==='))