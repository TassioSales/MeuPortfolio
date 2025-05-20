from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.ext.declarative import declarative_base

# Configurar o banco de dados
engine = create_engine('sqlite:///transacoes.db')
Session = scoped_session(sessionmaker(bind=engine))

db_session = Session()

# Criar base para models
Base = declarative_base()
