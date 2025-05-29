"""
Módulo para gerenciar a criação e manipulação de alertas no banco de dados.
"""
import sqlite3
import json
from datetime import datetime
import os
import logging
from .config import CONFIG
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List, Tuple, Union
from logger import get_logger, LogLevel

# Configura o logger
logger = get_logger('alert_service')
logger.level(LogLevel.DEBUG)
logger.info("Nível de log configurado para DEBUG no alert_service")

class AlertService:
    """
    Classe responsável por gerenciar os alertas no banco de dados.
    """
    
    def __init__(self, db_path=None):
        """
        Inicializa o serviço de alertas.
        
        Args:
            db_path: Caminho para o arquivo do banco de dados SQLite
        """
        self.db_path = db_path or CONFIG['db_path']
        self._criar_tabela_alertas()
        self._verificar_e_migrar_esquema()
    
    def _get_connection(self):
        """Cria uma nova conexão com o banco de dados."""
        try:
            conn = sqlite3.connect(self.db_path)
            # Habilita o suporte a chaves estrangeiras
            conn.execute('PRAGMA foreign_keys = ON')
            return conn
        except sqlite3.Error as e:
            logger.error(f"Erro ao conectar ao banco de dados: {e}")
            raise
    
    def _criar_tabela_alertas(self):
        """
        Cria a tabela de alertas_automaticos se ela não existir.
        """
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS alertas_automaticos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            titulo VARCHAR(255) NOT NULL,
            descricao TEXT NOT NULL,
            tipo VARCHAR(50) NOT NULL,
            prioridade VARCHAR(20) NOT NULL,
            status VARCHAR(20) NOT NULL DEFAULT 'pendente',
            data_criacao DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            data_atualizacao DATETIME,
            data_ocorrencia DATETIME NOT NULL,
            categoria VARCHAR(100),
            valor DECIMAL(15,2),
            origem VARCHAR(100) NOT NULL,
            dados_adicionais TEXT,
            automatico BOOLEAN NOT NULL DEFAULT 1,
            transacao_id VARCHAR(100)
        )
        """
        
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(create_table_sql)
                conn.commit()
                logger.info("Tabela 'alertas_automaticos' verificada/criada com sucesso.")
        except Exception as e:
            logger.error(f"Erro ao criar tabela 'alertas_automaticos': {e}")
            raise
    
    def _verificar_e_migrar_esquema(self):
        """
        Verifica se o esquema da tabela alertas_automaticos está atualizado e aplica migrações necessárias.
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                # Obtém as colunas atuais da tabela
                cursor.execute("PRAGMA table_info(alertas_automaticos)")
                columns = [col[1] for col in cursor.fetchall()]
                
                # Verifica se transacao_id existe
                if 'transacao_id' not in columns:
                    logger.info("Coluna 'transacao_id' não encontrada. Aplicando migração.")
                    cursor.execute("ALTER TABLE alertas_automaticos ADD COLUMN transacao_id VARCHAR(100)")
                    conn.commit()
                    logger.info("Coluna 'transacao_id' adicionada com sucesso.")
                else:
                    logger.debug("Coluna 'transacao_id' já existe na tabela.")
        except sqlite3.Error as e:
            logger.error(f"Erro ao verificar/migrar esquema da tabela: {e}")
            raise
    
    def criar_alerta(self, alerta):
        """
        Cria um novo alerta no banco de dados.
        
        Args:
            alerta: Dicionário com os dados do alerta
            
        Returns:
            int: ID do alerta criado ou None em caso de erro
        """
        logger.info(f"Tentando salvar alerta: {alerta.get('titulo')}")
        logger.debug(f"Dados completos do alerta: {alerta}")
        
        try:
            # Garante que os campos obrigatórios existam
            campos_obrigatorios = ['titulo', 'data_ocorrencia', 'valor', 'categoria']
            for campo in campos_obrigatorios:
                if campo not in alerta:
                    logger.error(f"Campo obrigatório ausente: {campo}")
                    return None
            
            # Formata a data de ocorrência se for string
            if isinstance(alerta['data_ocorrencia'], str):
                try:
                    data_str = alerta['data_ocorrencia'].strip()
                    
                    # Se a data estiver no formato 'YYYY-MM-DD', adiciona o horário
                    if len(data_str) == 10 and data_str.count('-') == 2:
                        data_str += ' 00:00:00'
                    # Se a data estiver no formato com 'T' (ISO 8601)
                    elif 'T' in data_str:
                        # Formato: 2023-01-25T21:00:00-03:00
                        data_parts = data_str.split('T')
                        data_str = data_parts[0] + ' ' + data_parts[1].split('-')[0].split('+')[0]
                    
                    # Remove frações de segundo se existirem
                    if '.' in data_str:
                        data_str = data_str.split('.')[0]
                    
                    # Converte para datetime
                    alerta['data_ocorrencia'] = datetime.strptime(data_str, '%Y-%m-%d %H:%M:%S')
                    
                except Exception as e:
                    logger.error(f"Formato de data inválido: {alerta['data_ocorrencia']}. Erro: {e}")
                    return None
            
            # Converte o valor para float
            try:
                alerta['valor'] = float(alerta['valor'])
            except (ValueError, TypeError) as e:
                logger.error(f"Valor inválido: {alerta['valor']}. Erro: {e}")
                return None
            
            # Normaliza o título para incluir a data de ocorrência
            original_titulo = alerta['titulo']
            if 'Anomalia em Investimentos' in original_titulo:
                # Remove prefixos como "Alta" ou "Media" e normaliza o formato da data
                base_titulo = 'Anomalia em Investimentos'
                alerta['titulo'] = f"{base_titulo} - {alerta['data_ocorrencia'].strftime('%Y-%m-%d %H:%M:%S')}"
                logger.debug(f"Título normalizado de '{original_titulo}' para '{alerta['titulo']}'")
            
            # Verifica se o alerta já existe
            if self._alerta_ja_existe(alerta):
                logger.info(f"Alerta similar já existe: {alerta.get('titulo')} - Data: {alerta.get('data_ocorrencia')} - Valor: {alerta.get('valor')}")
                return None
                
            logger.info("Alerta não é uma duplicata, prosseguindo com o salvamento")
            
            # Garante que os campos opcionais tenham valores padrão
            alerta.setdefault('descricao', '')
            alerta.setdefault('tipo', 'anomalia')
            alerta.setdefault('prioridade', 'media')
            alerta.setdefault('status', 'pendente')
            alerta.setdefault('data_criacao', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
            alerta.setdefault('data_atualizacao', None)
            alerta.setdefault('origem', 'Sistema')
            alerta.setdefault('dados_adicionais', '{}')
            alerta.setdefault('automatico', 1)
            alerta.setdefault('transacao_id', None)
            
            logger.debug(f"Dados do alerta após aplicar valores padrão: {alerta}")
            
        except Exception as e:
            logger.error(f"Erro ao processar os dados do alerta: {e}", exc_info=True)
            return None
            
        # Verifica se a coluna transacao_id existe
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("PRAGMA table_info(alertas_automaticos)")
            columns = [col[1] for col in cursor.fetchall()]
            has_transacao_id = 'transacao_id' in columns
        
        insert_sql = """
        INSERT INTO alertas_automaticos (
            titulo, descricao, tipo, prioridade, status, data_criacao,
            data_atualizacao, data_ocorrencia, categoria, valor, origem,
            dados_adicionais, automatico{}
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?{})
        """.format(
            ", transacao_id" if has_transacao_id else "",
            ", ?" if has_transacao_id else ""
        )
        
        # Prepara os dados para inserção
        try:
            # Converte dados_adicionais para string JSON se for um dicionário
            dados_adicionais = alerta.get('dados_adicionais')
            if isinstance(dados_adicionais, dict):
                try:
                    import json
                    dados_adicionais = json.dumps(dados_adicionais, ensure_ascii=False)
                except Exception as e:
                    logger.error(f"Erro ao serializar dados_adicionais: {e}")
                    dados_adicionais = '{}'
            
            # Garante que o valor seja um float
            try:
                valor = float(alerta.get('valor', 0))
            except (TypeError, ValueError) as e:
                logger.error(f"Valor inválido: {alerta.get('valor')}. Usando 0.0 como valor padrão. Erro: {e}")
                valor = 0.0
            
            dados = (
                alerta.get('titulo', ''),
                alerta.get('descricao', ''),
                alerta.get('tipo', 'anomalia'),
                alerta.get('prioridade', 'media'),
                alerta.get('status', 'pendente'),
                alerta.get('data_criacao'),
                alerta.get('data_atualizacao'),
                alerta.get('data_ocorrencia'),
                alerta.get('categoria', 'Outros'),
                valor,
                alerta.get('origem', 'Sistema'),
                dados_adicionais,
                int(bool(alerta.get('automatico', 1)))
            )
            if has_transacao_id:
                dados += (alerta.get('transacao_id'),)
                
        except Exception as e:
            logger.error(f"Erro ao preparar dados do alerta: {e}", exc_info=True)
            return None
        
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                logger.debug(f"Executando query de inserção: {insert_sql}")
                logger.debug(f"Dados para inserção: {dados}")
                
                cursor.execute(insert_sql, dados)
                alerta_id = cursor.lastrowid
                conn.commit()
                
                logger.info(f"Alerta salvo com sucesso. ID: {alerta_id}")
                logger.debug(f"Detalhes do alerta salvo - ID: {alerta_id}, Título: {alerta.get('titulo')}, Data: {alerta.get('data_ocorrencia')}")
                
                return alerta_id
        except sqlite3.IntegrityError as e:
            logger.error(f"Erro de integridade ao salvar alerta: {e}", exc_info=True)
            logger.error(f"Detalhes do alerta que causou o erro: {alerta}")
            return None
        except Exception as e:
            logger.error(f"Erro inesperado ao salvar alerta: {e}", exc_info=True)
            logger.error(f"tipo do erro: {type(e).__name__}")
            logger.error(f"Detalhes do alerta que causou o erro: {alerta}")
            return None
    
    def _alerta_ja_existe(self, alerta):
        """
        Verifica se um alerta similar já existe no banco de dados.
        
        Um alerta é considerado similar se:
        - Tiver o mesmo transacao_id (se fornecido e a coluna existe)
        - OU mesma data de ocorrência, categoria e valor idêntico (com tolerância para arredondamento)
        
        Args:
            alerta: Dicionário com os dados do alerta
            
        Returns:
            bool: True se um alerta similar já existe, False caso contrário
        """
        logger.debug(f"Verificando se alerta já existe: {alerta.get('titulo')} - Data: {alerta.get('data_ocorrencia')} - Valor: {alerta.get('valor')} - Transacao ID: {alerta.get('transacao_id')}")
        
        # Verifica se o alerta tem os campos necessários
        required_fields = ['data_ocorrencia', 'valor', 'categoria']
        if not all(k in alerta for k in required_fields):
            logger.warning(f"Alerta não possui todos os campos necessários: {alerta}")
            return False
            
        # Prepara os parâmetros para a consulta
        try:
            # Converte a data de ocorrência para o formato correto
            data_ocorrencia = alerta['data_ocorrencia']
            if isinstance(data_ocorrencia, str):
                try:
                    data_str = data_ocorrencia
                    
                    # Se a data estiver no formato com 'T' (ISO 8601)
                    if 'T' in data_str:
                        # Formato: 2023-01-25T21:00:00-03:00
                        data_parts = data_str.split('T')
                        data_str = data_parts[0] + ' ' + data_parts[1].split('-')[0].split('+')[0]
                    
                    # Remove frações de segundo se existirem
                    if '.' in data_str:
                        data_str = data_str.split('.')[0]
                    
                    # Converte para datetime
                    data_ocorrencia = datetime.strptime(data_str, '%Y-%m-%d %H:%M:%S')
                    
                except Exception as e:
                    logger.error(f"Erro ao converter data_ocorrencia: {data_ocorrencia}. Erro: {e}")
                    return False
            
            data_formatada = data_ocorrencia.strftime('%Y-%m-%d %H:%M:%S')
            
            # Converte o valor para float para garantir comparação numérica
            try:
                valor = float(alerta['valor'])
            except (ValueError, TypeError) as e:
                logger.error(f"Valor inválido no alerta: {alerta['valor']}. Erro: {e}")
                return False
            
            # Obtém a origem e transacao_id ou usa valores padrão
            origem = alerta.get('origem', 'Sistema')
            transacao_id = alerta.get('transacao_id')
            
            logger.debug(f"Verificando alerta duplicado: categoria: {alerta['categoria']} | Data: {data_formatada} | Valor: {valor} | Transacao ID: {transacao_id}")
            
            # Verifica se a coluna transacao_id existe
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("PRAGMA table_info(alertas_automaticos)")
                columns = [col[1] for col in cursor.fetchall()]
                has_transacao_id = 'transacao_id' in columns
                
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                # Primeiro, verifica por transacao_id (se fornecido e a coluna existe)
                if transacao_id and has_transacao_id:
                    query = """
                    SELECT id, titulo, categoria, data_ocorrencia, valor, origem, automatico, transacao_id 
                    FROM alertas_automaticos 
                    WHERE transacao_id = ? 
                      AND automatico = 1
                    """
                    cursor.execute(query, (transacao_id,))
                    alertas_similares = cursor.fetchall()
                    
                    if alertas_similares:
                        logger.info(f"Alerta duplicado encontrado por transacao_id: {transacao_id}")
                        logger.debug(f"Alertas similares encontrados: {[dict(row) for row in alertas_similares]}")
                        return True
                
                # Se não houver transacao_id ou não encontrar duplicatas, verifica por categoria, data e valor
                query = """
                SELECT id, titulo, categoria, data_ocorrencia, valor, origem, automatico{} 
                FROM alertas_automaticos 
                WHERE categoria = ?
                  AND data_ocorrencia = ?
                  AND automatico = 1
                """.format(", transacao_id" if has_transacao_id else "")
                
                params = (
                    alerta['categoria'],
                    data_formatada
                )
                
                cursor.execute(query, params)
                alertas_similares = cursor.fetchall()
                
                if not alertas_similares:
                    logger.debug(f"Nenhum alerta similar encontrado para {alerta['categoria']} em {data_formatada}")
                    return False
                
                logger.debug(f"Encontrados {len(alertas_similares)} alertas similares: {[dict(row) for row in alertas_similares]}")
                
                # Verifica cada alerta similar encontrado
                for alerta_similar in alertas_similares:
                    try:
                        valor_similar = float(alerta_similar['valor'])
                        
                        logger.debug(f"Comparando com alerta existente: ID={alerta_similar['id']}, Valor={valor_similar}")
                        
                        # Se os valores forem idênticos (com pequena tolerância para arredondamento)
                        if abs(valor_similar - valor) < 0.01:
                            logger.info(f"Alerta duplicado exato encontrado: {alerta_similar['titulo']} - Valor: {valor_similar} - Data: {alerta_similar['data_ocorrencia']}")
                            return True
                        
                    except Exception as e_inner:
                        logger.error(f"Erro ao comparar alertas: {e_inner}", exc_info=True)
                        continue
                
                # Se chegou até aqui, não encontrou alertas suficientemente similares
                logger.debug(f"Nenhum alerta similar o suficiente encontrado para {alerta['categoria']} em {data_formatada}")
                return False
                
        except Exception as e:
            logger.error(f"Erro ao verificar alerta duplicado: {e}", exc_info=True)
            logger.error(f"tipo do erro: {type(e).__name__}")
            logger.error(f"Alerta que causou o erro: {alerta}")
            # Em caso de erro, assumimos que o alerta não existe para evitar perda de dados
            return False
    
    def obter_alertas(
        self, 
        pagina=1, 
        itens_por_pagina=20, 
        tipo=None, 
        prioridade=None, 
        status=None,
        categoria=None
    ):
        """
        Obtém uma lista paginada de alertas com filtros opcionais.
        
        Args:
            pagina: Número da página (começando em 1)
            itens_por_pagina: Número de itens por página
            tipo: Filtro por tipo
            prioridade: Filtro por prioridade
            status: Filtro por status
            categoria: Filtro por categoria
            
        Returns:
            dict: Dicionário com os alertas e informações de paginação
        """
        offset = (pagina - 1) * itens_por_pagina
        
        # Verifica se a coluna transacao_id existe
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("PRAGMA table_info(alertas_automaticos)")
            columns = [col[1] for col in cursor.fetchall()]
            has_transacao_id = 'transacao_id' in columns
        
        # Constrói a consulta base
        query = """
        SELECT 
            id, titulo, descricao, tipo, prioridade, status,
            strftime('%Y-%m-%d %H:%M:%S', data_criacao) as data_criacao,
            strftime('%Y-%m-%d %H:%M:%S', data_atualizacao) as data_atualizacao,
            strftime('%Y-%m-%d %H:%M:%S', data_ocorrencia) as data_ocorrencia,
            categoria, valor, origem, dados_adicionais, automatico{}
        FROM alertas_automaticos
        WHERE 1=1
        """.format(", transacao_id" if has_transacao_id else "")
        
        # Parâmetros para a consulta
        params = []
        
        # Adiciona filtros
        if tipo:
            query += " AND tipo = ?"
            params.append(tipo)
            
        if prioridade:
            query += " AND prioridade = ?"
            params.append(prioridade)
            
        if status:
            query += " AND status = ?"
            params.append(status)
            
        if categoria:
            query += " AND categoria = ?"
            params.append(categoria)
        
        # Ordenação
        query += " ORDER BY data_ocorrencia DESC, data_criacao DESC"
        
        # Adiciona paginação
        query += " LIMIT ? OFFSET ?"
        params.extend([itens_por_pagina, offset])
        
        # Consulta para contar o total de itens
        count_query = "SELECT COUNT(*) FROM alertas_automaticos WHERE 1=1"
        if tipo:
            count_query += " AND tipo = ?"
        if prioridade:
            count_query += " AND prioridade = ?"
        if status:
            count_query += " AND status = ?"
        if categoria:
            count_query += " AND categoria = ?"
        
        try:
            with self._get_connection() as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                # Executa a contagem total
                cursor.execute(count_query, params[:-2] if len(params) > 2 else [])
                total_itens = cursor.fetchone()[0]
                
                # Executa a consulta principal
                cursor.execute(query, params)
                
                # Converte os resultados para dicionários
                alertas = []
                for row in cursor.fetchall():
                    alerta = dict(row)
                    # Converte dados_adicionais de JSON para dicionário
                    if alerta.get('dados_adicionais'):
                        try:
                            alerta['dados_adicionais'] = json.loads(alerta['dados_adicionais'])
                        except (json.JSONDecodeError, TypeError):
                            alerta['dados_adicionais'] = {}
                    alertas.append(alerta)
                
                # Calcula o total de páginas
                total_paginas = (total_itens + itens_por_pagina - 1) // itens_por_pagina if itens_por_pagina > 0 else 1
                
                return {
                    'alertas': alertas,
                    'pagina_atual': pagina,
                    'itens_por_pagina': itens_por_pagina,
                    'total_itens': total_itens,
                    'total_paginas': total_paginas if total_paginas > 0 else 1
                }
                
        except Exception as e:
            logger.error(f"Erro ao obter alertas: {e}")
            return {
                'alertas': [],
                'pagina_atual': pagina,
                'itens_por_pagina': itens_por_pagina,
                'total_itens': 0,
                'total_paginas': 1
            }
    
    def atualizar_status(self, alerta_id, status, comentario=None):
        """
        Atualiza o status de um alerta.
        
        Args:
            alerta_id: ID do alerta
            status: Novo status
            comentario: Comentário opcional
            
        Returns:
            bool: True se a atualização foi bem-sucedida, False caso contrário
        """
        update_sql = """
        UPDATE alertas_automaticos
        SET status = ?,
            data_atualizacao = ?
        WHERE id = ?
        """
        
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    update_sql, 
                    (status, datetime.now().strftime('%Y-%m-%d %H:%M:%S'), alerta_id)
                )
                conn.commit()
                
                if cursor.rowcount > 0:
                    logger.info(f"Status do alerta {alerta_id} atualizado para '{status}'")
                    return True
                else:
                    logger.warning(f"Alerta não encontrado: ID {alerta_id}")
                    return False
        except Exception as e:
            logger.error(f"Erro ao atualizar status do alerta {alerta_id}: {e}")
            return False

# Instância global do serviço de alertas
alert_service = AlertService()