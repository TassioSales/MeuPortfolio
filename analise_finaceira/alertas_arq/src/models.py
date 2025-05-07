import os
import sys
from pathlib import Path
from datetime import datetime
from .database import get_connection
import json

# Adiciona o diretório raiz ao path para importar o logger
root_dir = str(Path(__file__).parent.parent.parent)
if root_dir not in sys.path:
    sys.path.append(root_dir)

from logger import get_logger, log_function, RequestContext

# Configura o logger para este módulo
logger = get_logger("alertas.models")

class Alerta:
    """Classe que representa um alerta no sistema"""
    
    def __init__(self, **kwargs):
        self.id = kwargs.get('id')
        self.tipo = kwargs.get('tipo', '')
        self.descricao = kwargs.get('descricao', '')
        self.valor_referencia = kwargs.get('valor_referencia')
        self.categoria = kwargs.get('categoria')
        self.data_inicio = kwargs.get('data_inicio', '')
        self.data_fim = kwargs.get('data_fim')
        self.frequencia = kwargs.get('frequencia', 'unico')
        self.notificacao_sistema = kwargs.get('notificacao_sistema', True)
        self.notificacao_email = kwargs.get('notificacao_email', True)
        self.prioridade = kwargs.get('prioridade', 'media')
        self.ativo = kwargs.get('ativo', True)
        self.data_criacao = kwargs.get('data_criacao', datetime.now().isoformat())
        self.data_atualizacao = kwargs.get('data_atualizacao')
        self.usuario_id = kwargs.get('usuario_id')
    
    def to_dict(self):
        """Converte o objeto para dicionário"""
        return {
            'id': self.id,
            'tipo': self.tipo,
            'descricao': self.descricao,
            'valor_referencia': self.valor_referencia,
            'categoria': self.categoria,
            'data_inicio': self.data_inicio,
            'data_fim': self.data_fim,
            'frequencia': self.frequencia,
            'notificacao_sistema': bool(self.notificacao_sistema),
            'notificacao_email': bool(self.notificacao_email),
            'prioridade': self.prioridade,
            'ativo': bool(self.ativo),
            'data_criacao': self.data_criacao,
            'data_atualizacao': self.data_atualizacao,
            'usuario_id': self.usuario_id
        }
    
    @classmethod
    def from_dict(cls, data):
        """Cria uma instância de Alerta a partir de um dicionário"""
        return cls(**data)
    
    def save(self):
        """Salva o alerta no banco de dados"""
        conn = None
        try:
            conn = get_connection()
            cursor = conn.cursor()
            
            # Dados sensíveis que não devem ser logados
            log_data = self.to_dict()
            log_data['valor_referencia'] = '***' if log_data['valor_referencia'] else None
            
            if self.id is None:
                # Log antes da inserção
                logger.info(f"Iniciando inserção de novo alerta. Dados: {json.dumps(log_data, default=str)}")
                
                # Inserir novo alerta
                cursor.execute('''
                INSERT INTO alertas (
                    tipo, descricao, valor_referencia, categoria, data_inicio, data_fim,
                    frequencia, notificacao_sistema, notificacao_email, prioridade, ativo,
                    data_criacao, data_atualizacao, usuario_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    self.tipo, self.descricao, self.valor_referencia, self.categoria,
                    self.data_inicio, self.data_fim, self.frequencia, int(self.notificacao_sistema),
                    int(self.notificacao_email), self.prioridade, int(self.ativo),
                    self.data_criacao, datetime.now().isoformat(), self.usuario_id
                ))
                self.id = cursor.lastrowid
                
                logger.info(f"Alerta inserido com sucesso. ID: {self.id}")
                
            else:
                # Log antes da atualização
                logger.info(f"Iniciando atualização do alerta ID: {self.id}. Dados: {json.dumps(log_data, default=str)}")
                
                # Busca dados atuais para logar as alterações
                cursor.execute('SELECT * FROM alertas WHERE id = ?', (self.id,))
                old_data = dict(zip([desc[0] for desc in cursor.description], cursor.fetchone()))
                
                # Atualizar alerta existente
                cursor.execute('''
                UPDATE alertas SET
                    tipo = ?, descricao = ?, valor_referencia = ?, categoria = ?,
                    data_inicio = ?, data_fim = ?, frequencia = ?,
                    notificacao_sistema = ?, notificacao_email = ?, prioridade = ?,
                    ativo = ?, data_atualizacao = ?, usuario_id = ?
                WHERE id = ?
                ''', (
                    self.tipo, self.descricao, self.valor_referencia, self.categoria,
                    self.data_inicio, self.data_fim, self.frequencia, int(self.notificacao_sistema),
                    int(self.notificacao_email), self.prioridade, int(self.ativo),
                    datetime.now().isoformat(), self.usuario_id, self.id
                ))
                
                # Loga as alterações
                changes = {}
                for key, new_value in self.to_dict().items():
                    if key in old_data and old_data[key] != new_value:
                        changes[key] = {
                            'de': old_data[key],
                            'para': new_value
                        }
                
                if changes:
                    logger.info(f"Alterações no alerta ID {self.id}: {json.dumps(changes, default=str)}")
                else:
                    logger.info("Nenhuma alteração detectada no alerta")
            
            conn.commit()
            logger.info(f"Alerta ID {self.id} salvo com sucesso")
            return True
            
        except Exception as e:
            logger.error(f"Erro ao salvar alerta: {str(e)}", exc_info=True)
            if conn:
                conn.rollback()
            return False
        finally:
            if conn:
                conn.close()
    
    @classmethod
    def get_by_id(cls, alerta_id):
        """Busca um alerta pelo ID"""
        conn = None
        try:
            logger.debug(f"Buscando alerta por ID: {alerta_id}")
            conn = get_connection()
            cursor = conn.cursor()
            
            cursor.execute('SELECT * FROM alertas WHERE id = ?', (alerta_id,))
            alerta_data = cursor.fetchone()
            
            if not alerta_data:
                logger.warning(f"Alerta ID {alerta_id} não encontrado")
                return None
                
            # Converte a tupla para dicionário
            columns = [desc[0] for desc in cursor.description]
            alerta_dict = dict(zip(columns, alerta_data))
            
            logger.debug(f"Alerta ID {alerta_id} encontrado com sucesso")
            return cls.from_dict(alerta_dict)
            
        except Exception as e:
            logger.error(f"Erro ao buscar alerta ID {alerta_id}: {str(e)}", exc_info=True)
            return None
        finally:
            if conn:
                conn.close()
    
    @classmethod
    def get_all(cls, filtros=None):
        """Busca todos os alertas, com filtros opcionais"""
        conn = None
        try:
            logger.debug(f"Buscando alertas com filtros: {filtros}")
            conn = get_connection()
            cursor = conn.cursor()
            
            query = 'SELECT * FROM alertas'
            params = []
            
            # Adiciona filtros se fornecidos
            if filtros:
                conditions = []
                for key, value in filtros.items():
                    if value is not None:
                        conditions.append(f"{key} = ?")
                        params.append(value)
                
                if conditions:
                    query += ' WHERE ' + ' AND '.join(conditions)
            
            logger.debug(f"Executando query: {query} com parâmetros: {params}")
            cursor.execute(query, params)
            alertas = cursor.fetchall()
            
            # Converte as tuplas para dicionários e depois para objetos Alerta
            columns = [desc[0] for desc in cursor.description]
            resultado = [cls.from_dict(dict(zip(columns, alerta))) for alerta in alertas]
            
            logger.info(f"Encontrados {len(resultado)} alertas")
            return resultado
            
        except Exception as e:
            logger.error(f"Erro ao buscar alertas: {str(e)}", exc_info=True)
            return []
        finally:
            if conn:
                conn.close()
    
    def delete(self):
        """Remove o alerta do banco de dados"""
        if not self.id:
            logger.error("Tentativa de excluir alerta sem ID")
            return False
            
        conn = None
        try:
            logger.info(f"Iniciando exclusão do alerta ID: {self.id}")
            
            # Primeiro, registra os dados do alerta que será excluído para auditoria
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM alertas WHERE id = ?', (self.id,))
            alerta_data = cursor.fetchone()
            
            if not alerta_data:
                logger.warning(f"Alerta ID {self.id} não encontrado para exclusão")
                return False
                
            # Converte para dicionário para log
            columns = [desc[0] for desc in cursor.description]
            alerta_dict = dict(zip(columns, alerta_data))
            logger.info(f"Dados do alerta a ser excluído: {json.dumps(alerta_dict, default=str)}")
            
            # Exclui o alerta
            cursor.execute('DELETE FROM alertas WHERE id = ?', (self.id,))
            conn.commit()
            
            # Remove o ID para indicar que o objeto não está mais no banco
            deleted_id = self.id
            self.id = None
            
            logger.info(f"Alerta ID {deleted_id} excluído com sucesso")
            return True
            
        except Exception as e:
            logger.error(f"Erro ao excluir alerta ID {self.id}: {str(e)}", exc_info=True)
            if conn:
                conn.rollback()
            return False
        finally:
            if conn:
                conn.close()

class HistoricoAlerta:
    """Classe que representa o histórico de disparos de um alerta"""
    
    @classmethod
    def registrar_disparo(cls, alerta_id, mensagem, status='enviado'):
        """Registra um novo disparo de alerta no histórico"""
        conn = None
        try:
            logger.info(f"Registrando disparo para alerta ID {alerta_id}. Status: {status}")
            
            conn = get_connection()
            cursor = conn.cursor()
            
            data_disparo = datetime.now().isoformat()
            
            cursor.execute('''
            INSERT INTO alertas_historico 
            (alerta_id, data_disparo, mensagem, status)
            VALUES (?, ?, ?, ?)
            ''', (alerta_id, data_disparo, mensagem, status))
            
            historico_id = cursor.lastrowid
            conn.commit()
            
            logger.debug(f"Disparo registrado com sucesso. ID: {historico_id}")
            return True
            
        except Exception as e:
            logger.error(
                f"Erro ao registrar disparo para alerta ID {alerta_id}: {str(e)}",
                exc_info=True
            )
            if conn:
                conn.rollback()
            return False
        finally:
            if conn:
                conn.close()
    
    @classmethod
    def get_historico_por_alerta(cls, alerta_id, limit=10):
        """Busca o histórico de disparos de um alerta"""
        conn = None
        try:
            logger.debug(f"Buscando histórico para alerta ID: {alerta_id}. Limite: {limit}")
            
            conn = get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
            SELECT * FROM alertas_historico 
            WHERE alerta_id = ? 
            ORDER BY data_disparo DESC 
            LIMIT ?
            ''', (alerta_id, limit))
            
            historico = cursor.fetchall()
            
            # Converte as tuplas para dicionários
            if historico:
                columns = [desc[0] for desc in cursor.description]
                resultado = [dict(zip(columns, item)) for item in historico]
                logger.debug(f"Encontrados {len(resultado)} registros de histórico para o alerta ID {alerta_id}")
                return resultado
                
            logger.debug(f"Nenhum registro de histórico encontrado para o alerta ID {alerta_id}")
            return []
            
        except Exception as e:
            logger.error(
                f"Erro ao buscar histórico para alerta ID {alerta_id}: {str(e)}",
                exc_info=True
            )
            return []
        finally:
            if conn:
                conn.close()
