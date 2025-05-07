import os
import sys
import unittest
import sqlite3
import pandas as pd
import matplotlib
from datetime import datetime, timedelta

matplotlib.use('Agg')  # Usar backend que não requer interface gráfica

# Adiciona o diretório pai ao path para importar o módulo
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.gerar_grafico_despesas import gerar_grafico_despesas_por_categoria, format_currency, conectar_banco
import matplotlib.pyplot as plt
import seaborn as sns

class TestGraficoDespesas(unittest.TestCase):
    def setUp(self):
        """Configuração inicial para os testes"""
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        self.img_dir = os.path.join(base_dir, 'dashboard_arq', 'static', 'img')
        os.makedirs(self.img_dir, exist_ok=True)
        self.db_path = os.path.join(base_dir, 'banco', 'financas.db')
        
    def test_geracao_grafico_com_dados_reais(self):
        """Testa a geração do gráfico com dados reais do banco de dados"""
        try:
            # Verificar se o banco de dados existe
            if not os.path.exists(self.db_path):
                self.skipTest("Banco de dados não encontrado.")
                return
                
            # Executar a função de geração do gráfico
            img_path = gerar_grafico_despesas_por_categoria(meses_atras=12)
            
            # Verificar se o arquivo foi criado
            self.assertIsNotNone(img_path, "O caminho da imagem não deve ser None")
            self.assertTrue(os.path.exists(img_path), f"O arquivo {img_path} não foi criado")
            self.assertGreater(os.path.getsize(img_path), 0, "O arquivo da imagem está vazio")
            
            # Verificar se o arquivo é uma imagem PNG válida
            with open(img_path, 'rb') as f:
                header = f.read(8)
                self.assertTrue(header.startswith(b'\x89PNG\r\n\x1a\n'), "O arquivo não é uma imagem PNG válida")
                
        except sqlite3.Error as e:
            self.fail(f"Erro ao acessar o banco de dados: {e}")
        except Exception as e:
            self.fail(f"Erro inesperado: {e}")
        finally:
            if 'conn' in locals():
                conn.close()
    
    def test_format_currency(self):
        """Testa a formatação de valores monetários"""
        self.assertEqual(format_currency(1000), "R$ 1.000,00")
        self.assertEqual(format_currency(1500.5), "R$ 1.500,50")
        self.assertEqual(format_currency(1234567.89), "R$ 1.234.567,89")

    def tearDown(self):
        """Limpar os arquivos gerados após os testes"""
        # Remover arquivos de imagem gerados durante os testes
        if os.path.exists(self.img_dir):
            for file in os.listdir(self.img_dir):
                if file.startswith(('grafico_despesas_', 'test_grafico_despesas')) and file.endswith('.png'):
                    try:
                        os.remove(os.path.join(self.img_dir, file))
                    except OSError:
                        pass

if __name__ == "__main__":
    unittest.main(verbosity=2)
