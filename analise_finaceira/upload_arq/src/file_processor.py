import pandas as pd
import logging
from datetime import datetime

# Configuração de logging
logger = logging.getLogger(__name__)

def normalize_column_name(column):
    """Normaliza o nome da coluna para minúsculas e sem acentos"""
    import unicodedata
    if not isinstance(column, str):
        column = str(column)
    # Remove acentos
    column = ''.join(c for c in unicodedata.normalize('NFD', column) 
                   if unicodedata.category(c) != 'Mn')
    # Converte para minúsculas e remove espaços extras
    return column.strip().lower()

class FileProcessor:
    """Classe para processar diferentes tipos de arquivos"""
    
    def __init__(self):
        self.supported_formats = ['csv', 'pdf']
    
    def process_csv(self, file_path):
        """Processa um arquivo CSV e retorna uma mensagem de sucesso ou erro"""
        try:
            # Lê o arquivo CSV
            df = pd.read_csv(file_path, encoding='utf-8')
            
            if df.empty:
                return False, "O arquivo CSV está vazio"
            
            # Normaliza os nomes das colunas
            df.columns = [normalize_column_name(col) for col in df.columns]
            
            # Verifica colunas obrigatórias
            required_columns = ['data', 'descricao', 'valor', 'tipo']
            missing_columns = [col for col in required_columns if col not in df.columns]
            
            if missing_columns:
                return False, f"Colunas obrigatórias faltando: {', '.join(missing_columns)}"
            
            # Converte a coluna de data para datetime
            try:
                df['data'] = pd.to_datetime(df['data'], dayfirst=True, errors='coerce')
                if df['data'].isna().any():
                    return False, "Formato de data inválido. Use DD/MM/AAAA"
            except Exception as e:
                return False, f"Erro ao converter datas: {str(e)}"
            
            # Valida os tipos
            valid_types = ['receita', 'despesa']
            df['tipo'] = df['tipo'].str.lower()
            invalid_types = df[~df['tipo'].isin(valid_types)]
            
            if not invalid_types.empty:
                return False, f"Tipos inválidos encontrados. Use 'receita' ou 'despesa'"
            
            # Converte valores para numérico
            try:
                df['valor'] = pd.to_numeric(df['valor'], errors='coerce')
                if df['valor'].isna().any():
                    return False, "Valores inválidos encontrados na coluna 'valor'"
            except Exception as e:
                return False, f"Erro ao converter valores: {str(e)}"
            
            # Aqui você pode adicionar mais validações e processamentos
            
            return True, f"Arquivo processado com sucesso! {len(df)} registros validados."
            
        except Exception as e:
            logger.error(f"Erro ao processar CSV: {str(e)}")
            return False, f"Erro ao processar o arquivo CSV: {str(e)}"
    
    def process_pdf(self, file_path):
        """Processa um arquivo PDF e retorna uma mensagem de sucesso ou erro"""
        try:
            # Importa aqui para não ser uma dependência obrigatória
            import PyPDF2
            
            with open(file_path, 'rb') as file:
                reader = PyPDF2.PdfReader(file)
                num_pages = len(reader.pages)
                
                # Extrai o texto de todas as páginas
                text = ""
                for page in reader.pages:
                    text += page.extract_text() + "\n"
                
                # Aqui você pode adicionar o processamento específico do PDF
                # Por enquanto, apenas retorna o número de páginas
                return True, f"PDF processado com sucesso! {num_pages} páginas lidas."
                
        except ImportError:
            return False, "A biblioteca PyPDF2 não está instalada. Instale com: pip install PyPDF2"
        except Exception as e:
            logger.error(f"Erro ao processar PDF: {str(e)}")
            return False, f"Erro ao processar o arquivo PDF: {str(e)}"
    
    def process_file(self, file_path):
        """Processa um arquivo com base em sua extensão"""
        if not file_path:
            return False, "Caminho do arquivo não fornecido"
            
        file_ext = file_path.split('.')[-1].lower()
        
        if file_ext == 'csv':
            return self.process_csv(file_path)
        elif file_ext == 'pdf':
            return self.process_pdf(file_path)
        else:
            return False, f"Formato de arquivo não suportado. Formatos suportados: {', '.join(self.supported_formats)}"
