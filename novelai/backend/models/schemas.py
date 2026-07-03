from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum


class OrigemEnum(str, Enum):
    agregada = "agregada"
    gerada_ia = "gerada_ia"


class StatusGeracaoEnum(str, Enum):
    pendente = "pendente"
    processando = "processando"
    concluido = "concluido"
    publicado = "publicado"
    erro = "erro"


# ─── AUTH ────────────────────────────────────────────────────────────────────────

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    nome: str = Field(min_length=2, max_length=100)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str


# ─── USUÁRIO ─────────────────────────────────────────────────────────────────────

class UsuarioOut(BaseModel):
    id: str
    email: str
    nome: str
    foto_url: Optional[str] = None
    idioma_preferido: str = "pt"
    qualidade_padrao: str = "720p"
    legendas_padrao: str = "off"
    role: str = "usuario"
    criado_em: Optional[datetime] = None


class UsuarioPreferencias(BaseModel):
    idioma_preferido: Optional[str] = None
    qualidade_padrao: Optional[str] = None
    legendas_padrao: Optional[str] = None


# ─── NOVELA ──────────────────────────────────────────────────────────────────────

class NovelaOut(BaseModel):
    id: str
    titulo: str
    descricao: Optional[str] = None
    genero: List[str] = []
    idioma: str = "pt"
    ano: Optional[int] = None
    poster_url: Optional[str] = None
    backdrop_url: Optional[str] = None
    rating_medio: float = 0.0
    total_votos: int = 0
    views: int = 0
    origem: OrigemEnum = OrigemEnum.agregada
    data_criacao: Optional[datetime] = None
    total_episodios: Optional[int] = None


class NovelaListResponse(BaseModel):
    items: List[NovelaOut]
    total: int
    pagina: int
    por_pagina: int
    total_paginas: int


# ─── EPISÓDIO ────────────────────────────────────────────────────────────────────

class EpisodioOut(BaseModel):
    id: str
    novela_id: str
    numero: int
    titulo: str
    descricao: Optional[str] = None
    video_url: str
    duracao_segundos: int = 0
    legendas_url: Optional[str] = None
    thumbnail_url: Optional[str] = None
    data_lancamento: Optional[datetime] = None


# ─── HISTÓRICO ───────────────────────────────────────────────────────────────────

class HistoricoUpdate(BaseModel):
    posicao_segundos: int = Field(ge=0)


class HistoricoOut(BaseModel):
    episode_id: str
    episodio: EpisodioOut
    novela: NovelaOut
    posicao_segundos: int
    assistido_em: datetime


# ─── FAVORITOS ───────────────────────────────────────────────────────────────────

class FavoritoToggle(BaseModel):
    novela_id: str


class FavoritoOut(BaseModel):
    novela: NovelaOut
    criado_em: datetime


# ─── COMENTÁRIOS ─────────────────────────────────────────────────────────────────

class ComentarioCreate(BaseModel):
    texto: str = Field(min_length=1, max_length=2000)


class ComentarioUpdate(BaseModel):
    texto: str = Field(min_length=1, max_length=2000)


class ComentarioOut(BaseModel):
    id: str
    episode_id: str
    user_id: str
    usuario_nome: str
    usuario_foto: Optional[str] = None
    texto: str
    likes: int = 0
    criado_em: datetime
    atualizado_em: Optional[datetime] = None


# ─── RATING ──────────────────────────────────────────────────────────────────────

class RatingCreate(BaseModel):
    estrelas: int = Field(ge=1, le=5)


class RatingOut(BaseModel):
    episode_id: str
    user_id: str
    estrelas: int
    criado_em: datetime


# ─── BUSCA ───────────────────────────────────────────────────────────────────────

class BuscaFiltros(BaseModel):
    q: Optional[str] = None
    genero: Optional[str] = None
    idioma: Optional[str] = None
    ano_min: Optional[int] = None
    ano_max: Optional[int] = None
    rating_min: Optional[float] = None
    sort: str = "relevancia"
    pagina: int = Field(default=1, ge=1)
    por_pagina: int = Field(default=20, ge=1, le=100)


# ─── ADMIN ───────────────────────────────────────────────────────────────────────

class GerarEpisodioRequest(BaseModel):
    tema: str = Field(min_length=3, max_length=200)
    estilo: str = "Drama moderno"
    total_episodios: int = Field(default=1, ge=1, le=10)
    qualidade: str = "720p"
    novela_id: Optional[str] = None


class GeracaoOut(BaseModel):
    id: str
    status: StatusGeracaoEnum
    tipo: str
    parametros: dict
    video_url_resultado: Optional[str] = None
    erro_mensagem: Optional[str] = None
    criado_em: datetime
    iniciado_em: Optional[datetime] = None
    concluido_em: Optional[datetime] = None


class AdminStatsOut(BaseModel):
    total_novelas: int
    total_episodios: int
    total_usuarios: int
    total_views: int
    geracoes_pendentes: int
    geracoes_concluidas: int
