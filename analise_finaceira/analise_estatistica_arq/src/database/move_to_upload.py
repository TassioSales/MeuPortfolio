import shutil
import os

def move_to_upload():
    # Caminho do arquivo gerado
    source_path = r'D:\Github\MeuPortfolio\analise_finaceira\analise_estatistica_arq\src\database\transacoes_teste.csv'
    
    # Caminho do diretório de upload
    upload_dir = r'D:\Github\MeuPortfolio\analise_finaceira\Uploads'
    
    # Criar o diretório de upload se não existir
    os.makedirs(upload_dir, exist_ok=True)
    
    # Mover o arquivo para o diretório de upload
    try:
        shutil.copy2(source_path, upload_dir)
        print(f"Arquivo movido com sucesso para {upload_dir}")
    except Exception as e:
        print(f"Erro ao mover arquivo: {str(e)}")

if __name__ == '__main__':
    move_to_upload()
