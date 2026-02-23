import time
import sys
import logging
from django.core.management.base import BaseCommand

from rhcontrol.services import process_notifications

logger = logging.getLogger(__name__)

# ==========================================
# REGISTRY DE AUTOMAÇÕES
# Para adicionar novas rotinas no futuro, 
# basta importar a função e mapeá-la aqui.
# ==========================================
AUTOMATIONS_REGISTRY = {
    'notifications': process_notifications,
 
}

class Command(BaseCommand):
    help = 'Hub central para execução de automações agendadas do sistema.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--only',
            type=str,
            help='Executa apenas a automação especificada (ex: --only notifications)',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Executa em modo de simulação (não grava no banco nem envia e-mails)',
        )

    def handle(self, *args, **options):
        only = options.get('only')
        dry_run = options.get('dry_run')

        routines_to_run = {}
        if only:
            if only not in AUTOMATIONS_REGISTRY:
                self.stderr.write(self.style.ERROR(f"ERRO: Rotina '{only}' não encontrada no registry."))
                sys.exit(1)
            routines_to_run = {only: AUTOMATIONS_REGISTRY[only]}
        else:
            routines_to_run = AUTOMATIONS_REGISTRY

        start_time = time.time()
        dry_run_tag = "[DRY-RUN ATIVO] " if dry_run else ""
        self.stdout.write(self.style.NOTICE(f"=== INICIANDO HUB DE AUTOMAÇÕES {dry_run_tag}==="))

        has_failures = False
        results = {}

        for name, func in routines_to_run.items():
            self.stdout.write(f"-> Iniciando rotina: {name}...")
            routine_start = time.time()
            
            try:

                func(dry_run=dry_run)
                
                duration = time.time() - routine_start
                results[name] = {'status': 'SUCCESS', 'duration': duration}
                self.stdout.write(self.style.SUCCESS(f"   [SUCCESS] {name} concluída em {duration:.2f}s"))
                
            except Exception as e:
                duration = time.time() - routine_start
                has_failures = True
                results[name] = {'status': 'FAILED', 'duration': duration, 'error': str(e)}
                
                self.stderr.write(self.style.ERROR(f"   [FAILED] {name} falhou em {duration:.2f}s: {str(e)}"))
                logger.exception(f"Erro fatal na automação '{name}'")

        total_duration = time.time() - start_time

        self.stdout.write("\n=== RESUMO DA EXECUÇÃO ===")
        for name, data in results.items():
            status_color = self.style.SUCCESS if data['status'] == 'SUCCESS' else self.style.ERROR
            self.stdout.write(status_color(f" - {name}: {data['status']} ({data['duration']:.2f}s)"))
        
        self.stdout.write(f"Tempo total de processamento: {total_duration:.2f}s")
        self.stdout.write("==========================\n")

        if has_failures:
            self.stderr.write(self.style.ERROR("Processamento finalizado com falhas em uma ou mais rotinas."))
            sys.exit(1)  
        else:
            self.stdout.write(self.style.SUCCESS("Processamento finalizado com sucesso total."))