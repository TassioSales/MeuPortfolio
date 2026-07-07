from fastapi import APIRouter, Query, HTTPException, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, asc
from typing import Optional, List
from loguru import logger

from models.database import get_db, Novela, Episodio, Comentario
from models.schemas import NovelaOut, NovelaListResponse, EpisodioOut, ComentarioOut
from models.auth import get_optional_user

router = APIRouter()


# ─── NOVELAS ─────────────────────────────────────────────────────────────────────

@router.get("/novelas", response_model=NovelaListResponse)
async def listar_novelas(
    pagina: int = Query(1, ge=1),
    por_pagina: int = Query(20, ge=1, le=100),
    genero: Optional[str] = None,
    idioma: Optional[str] = None,
    sort: str = Query("recente", pattern="^(recente|rating|trending|titulo)$"),
    db: Session = Depends(get_db),
):
    try:
        q = db.query(Novela)
        if genero:
            q = q.filter(Novela.genero.any(genero))
        if idioma:
            q = q.filter(Novela.idioma == idioma)

        sort_map = {
            "recente": desc(Novela.data_criacao),
            "rating": desc(Novela.rating_medio),
            "trending": desc(Novela.views),
            "titulo": asc(Novela.titulo),
        }
        q = q.order_by(sort_map.get(sort, desc(Novela.data_criacao)))

        total = q.count()
        novelas = q.offset((pagina - 1) * por_pagina).limit(por_pagina).all()

        items = [_novela_to_out(n, db) for n in novelas]
        return NovelaListResponse(
            items=items,
            total=total,
            pagina=pagina,
            por_pagina=por_pagina,
            total_paginas=max(1, -(-total // por_pagina)),
        )
    except Exception as e:
        logger.error(f"listar_novelas error: {e}")
        return NovelaListResponse(items=[], total=0, pagina=1, por_pagina=por_pagina, total_paginas=1)


@router.get("/novelas/{novela_id}", response_model=NovelaOut)
async def detalhe_novela(novela_id: str, db: Session = Depends(get_db)):
    try:
        import uuid as _uuid
        n = db.query(Novela).filter(Novela.id == _uuid.UUID(novela_id)).first()
        if not n:
            raise HTTPException(status_code=404, detail="Novela não encontrada")
        n.views = (n.views or 0) + 1
        db.commit()
        return _novela_to_out(n, db)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"detalhe_novela error: {e}")
        raise HTTPException(status_code=500, detail="Erro ao buscar novela")


@router.get("/novelas/{novela_id}/episodios", response_model=List[EpisodioOut])
async def episodios_da_novela(novela_id: str, db: Session = Depends(get_db)):
    try:
        import uuid as _uuid
        eps = (
            db.query(Episodio)
            .filter(Episodio.novela_id == _uuid.UUID(novela_id))
            .order_by(Episodio.numero)
            .all()
        )
        return [_episodio_to_out(e) for e in eps]
    except Exception as e:
        logger.error(f"episodios_da_novela error: {e}")
        return []


@router.get("/novelas/{novela_id}/comentarios", response_model=List[ComentarioOut])
async def comentarios_da_novela(
    novela_id: str,
    pagina: int = Query(1, ge=1),
    por_pagina: int = Query(20, ge=1, le=50),
    db: Session = Depends(get_db),
):
    try:
        import uuid as _uuid
        comentarios = (
            db.query(Comentario)
            .filter(
                Comentario.novela_id == _uuid.UUID(novela_id),
                Comentario.deletado_em.is_(None),
            )
            .order_by(desc(Comentario.criado_em))
            .offset((pagina - 1) * por_pagina)
            .limit(por_pagina)
            .all()
        )
        return [_comentario_to_out(c) for c in comentarios]
    except Exception as e:
        logger.error(f"comentarios_da_novela error: {e}")
        return []


# ─── STREAM ──────────────────────────────────────────────────────────────────────

@router.get("/stream/{episode_id}")
async def stream_episodio(
    episode_id: str,
    db: Session = Depends(get_db),
    current_user: Optional[dict] = Depends(get_optional_user),
):
    try:
        import uuid as _uuid
        ep = db.query(Episodio).filter(Episodio.id == _uuid.UUID(episode_id)).first()
        if not ep:
            raise HTTPException(status_code=404, detail="Episódio não encontrado")
        return {"video_url": ep.video_url, "titulo": ep.titulo}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"stream_episodio error: {e}")
        raise HTTPException(status_code=500, detail="Erro ao obter stream")


@router.get("/episodes/{episode_id}/subtitle")
async def get_subtitle(episode_id: str, db: Session = Depends(get_db)):
    try:
        import uuid as _uuid
        ep = db.query(Episodio).filter(Episodio.id == _uuid.UUID(episode_id)).first()
        if not ep or not ep.legendas_url:
            raise HTTPException(status_code=404, detail="Legenda não disponível")
        return {"legendas_url": ep.legendas_url}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail="Erro ao obter legenda")


# ─── BUSCA ───────────────────────────────────────────────────────────────────────

@router.get("/busca", response_model=NovelaListResponse)
async def busca_avancada(
    q: Optional[str] = None,
    genero: Optional[str] = None,
    idioma: Optional[str] = None,
    ano_min: Optional[int] = None,
    ano_max: Optional[int] = None,
    rating_min: Optional[float] = None,
    sort: str = Query("relevancia", pattern="^(relevancia|rating|recente|trending)$"),
    pagina: int = Query(1, ge=1),
    por_pagina: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    try:
        query = db.query(Novela)
        if q:
            query = query.filter(Novela.titulo.ilike(f"%{q}%"))
        if genero:
            query = query.filter(Novela.genero.any(genero))
        if idioma:
            query = query.filter(Novela.idioma == idioma)
        if ano_min:
            query = query.filter(Novela.ano >= ano_min)
        if ano_max:
            query = query.filter(Novela.ano <= ano_max)
        if rating_min:
            query = query.filter(Novela.rating_medio >= rating_min)

        sort_map = {
            "relevancia": desc(Novela.views),
            "rating": desc(Novela.rating_medio),
            "recente": desc(Novela.data_criacao),
            "trending": desc(Novela.views),
        }
        query = query.order_by(sort_map.get(sort, desc(Novela.views)))

        total = query.count()
        novelas = query.offset((pagina - 1) * por_pagina).limit(por_pagina).all()

        return NovelaListResponse(
            items=[_novela_to_out(n, db) for n in novelas],
            total=total,
            pagina=pagina,
            por_pagina=por_pagina,
            total_paginas=max(1, -(-total // por_pagina)),
        )
    except Exception as e:
        logger.error(f"busca_avancada error: {e}")
        return NovelaListResponse(items=[], total=0, pagina=1, por_pagina=por_pagina, total_paginas=1)


# ─── RECOMENDAÇÕES ───────────────────────────────────────────────────────────────

@router.get("/recomendacoes/trending", response_model=List[NovelaOut])
async def trending(limit: int = Query(20, ge=1, le=50), db: Session = Depends(get_db)):
    try:
        novelas = db.query(Novela).order_by(desc(Novela.views)).limit(limit).all()
        return [_novela_to_out(n, db) for n in novelas]
    except Exception as e:
        logger.error(f"trending error: {e}")
        return []


@router.get("/recomendacoes", response_model=List[NovelaOut])
async def recomendacoes(
    user_id: Optional[str] = None,
    limit: int = Query(20, ge=1, le=50),
    db: Session = Depends(get_db),
):
    try:
        novelas = db.query(Novela).order_by(desc(Novela.rating_medio)).limit(limit).all()
        return [_novela_to_out(n, db) for n in novelas]
    except Exception as e:
        logger.error(f"recomendacoes error: {e}")
        return []


@router.get("/generos")
async def listar_generos(db: Session = Depends(get_db)):
    try:
        rows = db.query(Novela.genero).all()
        generos = set()
        for (g,) in rows:
            if g:
                generos.update(g)
        return sorted(list(generos))
    except Exception:
        return ["Drama", "Romance", "Ação", "Comédia", "Suspense", "Ficção Científica"]


# ─── Helpers ─────────────────────────────────────────────────────────────────────

def _novela_to_out(n: Novela, db: Session) -> NovelaOut:
    from models.schemas import OrigemEnum as SchemaOrigemEnum
    total_ep = db.query(func.count(Episodio.id)).filter(Episodio.novela_id == n.id).scalar() or 0
    return NovelaOut(
        id=str(n.id),
        titulo=n.titulo,
        descricao=n.descricao,
        genero=n.genero or [],
        idioma=n.idioma or "pt",
        ano=n.ano,
        poster_url=n.poster_url,
        backdrop_url=n.backdrop_url,
        rating_medio=n.rating_medio or 0.0,
        total_votos=n.total_votos or 0,
        views=n.views or 0,
        origem=SchemaOrigemEnum(n.origem.value) if n.origem else SchemaOrigemEnum.agregada,
        data_criacao=n.data_criacao,
        total_episodios=total_ep,
    )


def _episodio_to_out(e: Episodio) -> EpisodioOut:
    return EpisodioOut(
        id=str(e.id),
        novela_id=str(e.novela_id),
        numero=e.numero,
        titulo=e.titulo,
        descricao=e.descricao,
        video_url=e.video_url,
        duracao_segundos=e.duracao_segundos or 0,
        legendas_url=e.legendas_url,
        thumbnail_url=e.thumbnail_url,
        data_lancamento=e.data_lancamento,
    )


def _comentario_to_out(c: Comentario) -> ComentarioOut:
    nome = c.usuario.nome if c.usuario else "Usuário"
    foto = c.usuario.foto_url if c.usuario else None
    return ComentarioOut(
        id=str(c.id),
        episode_id=str(c.episode_id),
        user_id=str(c.user_id),
        usuario_nome=nome,
        usuario_foto=foto,
        texto=c.texto,
        likes=c.likes or 0,
        criado_em=c.criado_em,
        atualizado_em=c.atualizado_em,
    )
