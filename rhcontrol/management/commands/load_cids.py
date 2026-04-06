import csv
import urllib.request
from django.core.management.base import BaseCommand
from rhcontrol.models import CID

class Command(BaseCommand):
    help = 'Carrega a lista completa de CIDs-10 de forma resiliente.'

    def handle(self, *args, **kwargs):
        # 4 espelhos acadêmicos e projetos de dados públicos (um deles sempre estará online)
        urls = [
            "https://raw.githubusercontent.com/cartaproale/PySUS/main/tabelas/cid10.csv",
            "https://raw.githubusercontent.com/cartaproale/PySUS/master/tabelas/cid10.csv",
            "https://raw.githubusercontent.com/labulatif/public/main/cid10.csv",
            "https://raw.githubusercontent.com/labulatif/public/master/cid10.csv"
        ]
        
        data_lines = None
        
        self.stdout.write("Buscando a base do CID-10 nos espelhos públicos...")
        
        for url in urls:
            try:
                req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
                with urllib.request.urlopen(req) as response:
                    raw_bytes = response.read()
                    # Tenta ler no padrão da web, se falhar, lê no padrão Windows/Brasil
                    try:
                        text = raw_bytes.decode('utf-8')
                    except UnicodeDecodeError:
                        text = raw_bytes.decode('latin-1')
                    
                    data_lines = text.splitlines()
                
                self.stdout.write(self.style.SUCCESS("Conexão estabelecida e arquivo baixado com sucesso!"))
                break # Se deu certo, para de tentar os outros links
            except Exception:
                continue # Se deu erro (404, etc), tenta o próximo silenciosamente
                
        if not data_lines:
            self.stdout.write(self.style.ERROR("Falha crítica: Todos os espelhos estão indisponíveis no momento."))
            return
            
        try:
            # Descobre se o arquivo usa vírgula ou ponto-e-vírgula
            primeira_linha = data_lines[0]
            delimiter = ';' if ';' in primeira_linha else ','
            
            reader = csv.reader(data_lines, delimiter=delimiter)
            header = next(reader)
            
            # Mapeamento inteligente de colunas
            col_code, col_desc = 0, 1
            for i, col in enumerate(header):
                col_lower = col.lower()
                if col_lower in ['codigo', 'cod', 'cid', 'subcat', 'cd_categoria']:
                    col_code = i
                elif col_lower in ['nome', 'descricao', 'desc', 'doenca', 'ds_categoria']:
                    col_desc = i

            cids_to_create = []
            for row in reader:
                if len(row) > max(col_code, col_desc):
                    codigo = row[col_code].strip()
                    descricao = row[col_desc].strip()
                    
                    if codigo and descricao:
                        cids_to_create.append(CID(code=codigo, description=descricao))
            
            # Limpa e popula o banco
            CID.objects.all().delete()
            CID.objects.bulk_create(cids_to_create, batch_size=1000)
            
            self.stdout.write(self.style.SUCCESS(f'Missão Cumprida! {len(cids_to_create)} doenças foram catalogadas no banco.'))
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Erro ao processar a leitura do arquivo: {str(e)}'))