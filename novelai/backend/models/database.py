from sqlalchemy import (
    create_engine, Column, String, Integer, Float, DateTime, Text,
    ForeignKey, UniqueConstraint, CheckConstraint, Enum as SAEnum, Boolean
)
from sqlalchemy.dialects.postgresql import UUID, ARRAY, JSONB
from sqlalchemy.orm import declarative_base, relationship, sessionmaker, Session
from sqlalchemy.pool import NullPool
from datetime import datetime
from typing import Generator
import uuid
import enum

from config import settings

engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    echo=False,
)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
Base = declarative_base()


# ─── Enums ───────────────────────────────────────────────────────────────────────

class OrigemEnum(str, enum.Enum):
    agregada = "agregada"
    gerada_ia = "gerada_ia"

class FilaStatusEnum(str, enum.Enum):
    pendente = "pendente"
    processando = "processando"
    concluido = "concluido"
    publicado = "publicado"
    erro = "erro"

class UserRoleEnum(str, enum.Enum):
    usuario = "usuario"
    admin = "admin"


# ─── Models ──────────────────────────────────────────────────────────────────────

class Novela(Base):
    __tablename__ = "novelas"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    titulo = Column(String(255), nullable=False)
    descricao = Column(Text)
    genero = Column(ARRAY(String(50)), default=list)
    idioma = Column(String(10), default="pt")
    ano = Column(Integer)
    poster_url = Column(String)
    backdrop_url = Column(String)
    rating_medio = Column(Float, default=0.0)
    total_votos = Column(Integer, default=0)
    views = Column(Integer, default=0)
    origem = Column(SAEnum(OrigemEnum, name="origem_enum", create_type=False), default=OrigemEnum.agregada)
    fonte_original = Column(String)
    data_criacao = Column(DateTime, default=datetime.utcnow)
    atualizado_em = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    episodios = relationship("Episodio", back_populates="novela", cascade="all, delete-orphan")
    comentarios = relationship("Comentario", back_populates="novela", cascade="all, delete-orphan")
    ratings = relationship("Rating", back_populates="novela", cascade="all, delete-orphan")
    favoritos = relationship("Favorito", back_populates="novela", cascade="all, delete-orphan")


class Episodio(Base):
    __tablename__ = "episodios"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    novela_id = Column(UUID(as_uuid=True), ForeignKey("novelas.id", ondelete="CASCADE"), nullable=False)
    youtube_id = Column(String(50))
    numero = Column(Integer, nullable=False, default=1)
    titulo = Column(String(300), nullable=False)
    descricao = Column(Text)
    video_url = Column(String(1000), nullable=False)
    duracao_segundos = Column(Integer, default=0)
    legendas_url = Column(String(500))
    thumbnail_url = Column(String(500))
    data_lancamento = Column(DateTime, default=datetime.utcnow)
    criado_em = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("novela_id", "numero", name="uq_novela_episodio"),
    )

    novela = relationship("Novela", back_populates="episodios")
    historico = relationship("HistoricoReproducao", back_populates="episodio", cascade="all, delete-orphan")
    comentarios = relationship("Comentario", back_populates="episodio", cascade="all, delete-orphan")
    ratings = relationship("Rating", back_populates="episodio", cascade="all, delete-orphan")


class Usuario(Base):
    __tablename__ = "usuarios"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    nome = Column(String(150), nullable=False)
    foto_url = Column(String(500))
    role = Column(SAEnum(UserRoleEnum, name="user_role_enum", create_type=False), default=UserRoleEnum.usuario)
    idioma_preferido = Column(String(10), default="pt")
    qualidade_padrao = Column(String(10), default="720p")
    legendas_padrao = Column(String(10), default="off")
    criado_em = Column(DateTime, default=datetime.utcnow)
    atualizado_em = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    historico = relationship("HistoricoReproducao", back_populates="usuario", cascade="all, delete-orphan")
    favoritos = relationship("Favorito", back_populates="usuario", cascade="all, delete-orphan")
    comentarios = relationship("Comentario", back_populates="usuario", cascade="all, delete-orphan")
    ratings = relationship("Rating", back_populates="usuario", cascade="all, delete-orphan")


class HistoricoReproducao(Base):
    __tablename__ = "historico_reproducao"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("usuarios.id", ondelete="CASCADE"), nullable=False)
    episode_id = Column(UUID(as_uuid=True), ForeignKey("episodios.id", ondelete="CASCADE"), nullable=False)
    posicao_segundos = Column(Integer, default=0)
    percentual_completado = Column(Float, default=0.0)
    assistido_em = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("user_id", "episode_id", name="uq_user_episode"),
    )

    usuario = relationship("Usuario", back_populates="historico")
    episodio = relationship("Episodio", back_populates="historico")


class Favorito(Base):
    __tablename__ = "favoritos"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("usuarios.id", ondelete="CASCADE"), nullable=False)
    novela_id = Column(UUID(as_uuid=True), ForeignKey("novelas.id", ondelete="CASCADE"), nullable=False)
    criado_em = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("user_id", "novela_id", name="uq_user_novela_fav"),
    )

    usuario = relationship("Usuario", back_populates="favoritos")
    novela = relationship("Novela", back_populates="favoritos")


class Comentario(Base):
    __tablename__ = "comentarios"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    episode_id = Column(UUID(as_uuid=True), ForeignKey("episodios.id", ondelete="CASCADE"), nullable=False)
    novela_id = Column(UUID(as_uuid=True), ForeignKey("novelas.id", ondelete="CASCADE"), nullable=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("usuarios.id", ondelete="CASCADE"), nullable=False)
    texto = Column(Text, nullable=False)
    likes = Column(Integer, default=0)
    criado_em = Column(DateTime, default=datetime.utcnow)
    atualizado_em = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    deletado_em = Column(DateTime)

    episodio = relationship("Episodio", back_populates="comentarios")
    novela = relationship("Novela", back_populates="comentarios")
    usuario = relationship("Usuario", back_populates="comentarios")


class Rating(Base):
    __tablename__ = "ratings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    episode_id = Column(UUID(as_uuid=True), ForeignKey("episodios.id", ondelete="CASCADE"), nullable=False)
    novela_id = Column(UUID(as_uuid=True), ForeignKey("novelas.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("usuarios.id", ondelete="CASCADE"), nullable=False)
    estrelas = Column(Integer, nullable=False)
    criado_em = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("episode_id", "user_id", name="uq_episode_user_rating"),
        CheckConstraint("estrelas >= 1 AND estrelas <= 5", name="ck_estrelas"),
    )

    episodio = relationship("Episodio", back_populates="ratings")
    novela = relationship("Novela", back_populates="ratings")
    usuario = relationship("Usuario", back_populates="ratings")


class FilaGeracao(Base):
    __tablename__ = "fila_geracao"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    status = Column(SAEnum(FilaStatusEnum, name="fila_status_enum", create_type=False), default=FilaStatusEnum.pendente)
    tipo = Column(String(50), default="episodio")
    parametros = Column(JSONB, default=dict)
    video_url_resultado = Column(String(1000))
    erro_mensagem = Column(Text)
    criado_em = Column(DateTime, default=datetime.utcnow)
    iniciado_em = Column(DateTime)
    concluido_em = Column(DateTime)


# ─── Session dependency ───────────────────────────────────────────────────────────

def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_tables():
    from sqlalchemy import text
    with engine.begin() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS \"uuid-ossp\""))
        conn.execute(text("""
            DO $$ BEGIN
                CREATE TYPE origem_enum AS ENUM ('agregada', 'gerada_ia');
            EXCEPTION WHEN duplicate_object THEN NULL;
            END $$
        """))
        conn.execute(text("""
            DO $$ BEGIN
                CREATE TYPE user_role_enum AS ENUM ('usuario', 'admin');
            EXCEPTION WHEN duplicate_object THEN NULL;
            END $$
        """))
        conn.execute(text("""
            DO $$ BEGIN
                CREATE TYPE fila_status_enum AS ENUM ('pendente', 'processando', 'concluido', 'publicado', 'erro');
            EXCEPTION WHEN duplicate_object THEN NULL;
            END $$
        """))
    Base.metadata.create_all(bind=engine)
