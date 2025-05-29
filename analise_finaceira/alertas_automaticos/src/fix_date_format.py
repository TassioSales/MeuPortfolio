import re
import fileinput
import sys

def fix_date_format(file_path):
    # Padrão para encontrar linhas com data no formato 'YYYY-MM-01'
    pattern = r"('data_ocorrencia': pd\.Timestamp\(\w+\.start_time\)\.strftime\(')%Y-%m-01('\),)"
    
    # Novo formato com hora
    replacement = r"\g<1>%Y-%m-01 00:00:00\g<2>"
    
    # Contador de substituições
    count = 0
    
    try:
        # Lê o arquivo e faz as substituições
        with fileinput.FileInput(file_path, inplace=True, backup='.bak') as file:
            for line in file:
                # Verifica se a linha contém o padrão
                if "'data_ocorrencia':" in line and "strftime('%Y-%m-01')" in line:
                    # Faz a substituição
                    new_line = line.replace("strftime('%Y-%m-01')", "strftime('%Y-%m-01 00:00:00')")
                    print(new_line, end='')
                    count += 1
                else:
                    print(line, end='')
        
        print(f"Foram feitas {count} correções no arquivo {file_path}")
        return True
    except Exception as e:
        print(f"Erro ao processar o arquivo: {e}")
        return False

if __name__ == "__main__":
    if len(sys.argv) > 1:
        file_path = sys.argv[1]
        fix_date_format(file_path)
    else:
        print("Por favor, informe o caminho do arquivo como argumento.")
