from sqlalchemy import create_engine, MetaData, Table
from sqlalchemy.orm import sessionmaker
from sqlalchemy import Column, Integer, Float, String, DateTime
from sqlalchemy.ext.declarative import declarative_base
import sqlite3

def update_database():
    # Conectar ao banco de dados
    engine = create_engine('sqlite:///transacoes.db')
    conn = sqlite3.connect('transacoes.db')
    cursor = conn.cursor()
    
    # Verificar se a tabela já existe
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='transacoes'")
    table_exists = cursor.fetchone()
    
    if table_exists:
        # Adicionar novas colunas se não existirem
        cursor.execute("PRAGMA table_info(transacoes)")
        columns = cursor.fetchall()
        column_names = [col[1] for col in columns]
        
        # Adicionar colunas faltantes
        if 'quantidade' not in column_names:
            cursor.execute("ALTER TABLE transacoes ADD COLUMN quantidade FLOAT")
        if 'tipo_operacao' not in column_names:
            cursor.execute("ALTER TABLE transacoes ADD COLUMN tipo_operacao TEXT")
        if 'taxa' not in column_names:
            cursor.execute("ALTER TABLE transacoes ADD COLUMN taxa FLOAT")
        if 'volume' not in column_names:
            cursor.execute("ALTER TABLE transacoes ADD COLUMN volume FLOAT")
        if 'indicador1' not in column_names:
            cursor.execute("ALTER TABLE transacoes ADD COLUMN indicador1 FLOAT")
        if 'indicador2' not in column_names:
            cursor.execute("ALTER TABLE transacoes ADD COLUMN indicador2 FLOAT")
        
        conn.commit()
    else:
        # Criar a tabela do zero se não existir
        Base = declarative_base()
        
        class Transacao(Base):
            __tablename__ = 'transacoes'
            
            id = Column(Integer, primary_key=True)
            data = Column(DateTime)
            valor = Column(Float)
            quantidade = Column(Float)
            tipo_operacao = Column(String)
            taxa = Column(Float)
            ativo = Column(String)
            tipo = Column(String)
            categoria = Column(String)
            descricao = Column(String)
            volume = Column(Float)
            indicador1 = Column(Float)
            indicador2 = Column(Float)
            
        Base.metadata.create_all(engine)
    
    conn.close()

if __name__ == '__main__':
    update_database()
