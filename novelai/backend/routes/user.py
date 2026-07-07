from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc, func
from typing import List
from loguru import logger
from datetime import datetime
import uuid

from models.database import get_db, Usuario, Episodio, Novela, HistoricoReproducao, Favorito, Comentario, Rating
from models.schemas import (
    UsuarioOut, UsuarioPreferencias,
    HistoricoUpdate, HistoricoOut,
    FavoritoOut, FavoritoToggle,
    ComentarioCreate, ComentarioUpdate, ComentarioOut,
    RatingCreate, RatingOut,
    EpisodioOut, NovelaOut,
)
from models.auth import get_current_user
from routes.public import _novela_to_out, _episodio_to_out

router = APIRouter()


# ─── PERFIL ──────────────────────────────────────────────────────────────────────

@router.get("/me", response_model=UsuarioOut)
async def get_me(current_user: dict = Depends(get_current_user)):
    return UsuarioOut(**{k: v for k, v in current_user.items() if k != "password_hash"})


@router.put("/preferencias")
async def salvar_preferencias(
    body: UsuarioPreferencias,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    updates = body.model_dump(exclude_none=True)
    if not updates:
        return {"detail": "Nenhuma alteração"}
    u = db.query(Usuario).filter(Usuario.id == uuid.UUID(current_user["id"])).first()
    if not u:
        raise HTTPException(status_code=404)
    for k, v in updates.items():
        setattr(u, k, v)
    u.atualizado_em = datetime.utcnow()
    db.commit()
    return {"detail": "Preferências atualizadas"}


# ─── HISTÓRICO ───────────────────────────────────────────────────────────────────

@router.get("/historico", response_model=List[HistoricoOut])
async def get_historico(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
    limit: int = Query(20, ge=1, le=100),
):
    try:
        rows = (
            db.query(HistoricoReproducao)
            .filter(HistoricoReproducao.user_id == uuid.UUID(current_user["id"]))
            .order_by(desc(HistoricoReproducao.assistido_em))
            .limit(limit)
            .all()
        )
        result = []
        for h in rows:
            if not h.episodio:
                continue
            result.append(HistoricoOut(
                episode_id=str(h.episode_id),
                episodio=_episodio_to_out(h.episodio),
                novela=_novela_to_out(h.episodio.novela, db),
                posicao_segundos=h.posicao_segundos or 0,
                assistido_em=h.assistido_em,
            ))
        return result
    except Exception as e:
        logger.error(f"get_historico error: {e}")
        return []


@router.post("/historico")
async def atualizar_historico(
    body: HistoricoUpdate,
    episode_id: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        uid = uuid.UUID(current_user["id"])
        eid = uuid.UUID(episode_id)
        existing = db.query(HistoricoReproducao).filter(
            HistoricoReproducao.user_id == uid,
            HistoricoReproducao.episode_id == eid,
        ).first()

        ep = db.query(Episodio).filter(Episodio.id == eid).first()
        pct = 0.0
        if ep and ep.duracao_segundos:
            pct = round(body.posicao_segundos / ep.duracao_segundos * 100, 1)

        if existing:
            existing.posicao_segundos = body.posicao_segundos
            existing.percentual_completado = pct
            existing.assistido_em = datetime.utcnow()
        else:
            db.add(HistoricoReproducao(
                user_id=uid,
                episode_id=eid,
                posicao_segundos=body.posicao_segundos,
                percentual_completado=pct,
            ))
        db.commit()
        return {"detail": "Progresso salvo"}
    except Exception as e:
        db.rollback()
        logger.error(f"atualizar_historico error: {e}")
        raise HTTPException(status_code=500, detail="Erro ao salvar progresso")


# ─── FAVORITOS ───────────────────────────────────────────────────────────────────

@router.get("/favoritos", response_model=List[NovelaOut])
async def get_favoritos(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
    pagina: int = Query(1, ge=1),
    por_pagina: int = Query(20, ge=1, le=100),
):
    try:
        rows = (
            db.query(Favorito)
            .filter(Favorito.user_id == uuid.UUID(current_user["id"]))
            .order_by(desc(Favorito.criado_em))
            .offset((pagina - 1) * por_pagina)
            .limit(por_pagina)
            .all()
        )
        return [_novela_to_out(f.novela, db) for f in rows if f.novela]
    except Exception as e:
        logger.error(f"get_favoritos error: {e}")
        return []


@router.post("/favoritos/toggle")
async def toggle_favorito(
    body: FavoritoToggle,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        uid = uuid.UUID(current_user["id"])
        nid = uuid.UUID(body.novela_id)
        existing = db.query(Favorito).filter(
            Favorito.user_id == uid,
            Favorito.novela_id == nid,
        ).first()

        if existing:
            db.delete(existing)
            db.commit()
            return {"favorito": False, "detail": "Removido dos favoritos"}
        else:
            db.add(Favorito(user_id=uid, novela_id=nid))
            db.commit()
            return {"favorito": True, "detail": "Adicionado aos favoritos"}
    except Exception as e:
        db.rollback()
        logger.error(f"toggle_favorito error: {e}")
        raise HTTPException(status_code=500, detail="Erro ao atualizar favoritos")


# ─── COMENTÁRIOS ─────────────────────────────────────────────────────────────────

@router.post("/episodios/{episode_id}/comentarios", response_model=ComentarioOut, status_code=201)
async def criar_comentario(
    episode_id: str,
    body: ComentarioCreate,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        eid = uuid.UUID(episode_id)
        ep = db.query(Episodio).filter(Episodio.id == eid).first()
        if not ep:
            raise HTTPException(status_code=404, detail="Episódio não encontrado")

        c = Comentario(
            episode_id=eid,
            novela_id=ep.novela_id,
            user_id=uuid.UUID(current_user["id"]),
            texto=body.texto,
        )
        db.add(c)
        db.commit()
        db.refresh(c)

        return ComentarioOut(
            id=str(c.id),
            episode_id=str(c.episode_id),
            user_id=str(c.user_id),
            usuario_nome=current_user.get("nome", "Usuário"),
            usuario_foto=current_user.get("foto_url"),
            texto=c.texto,
            likes=0,
            criado_em=c.criado_em,
        )
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"criar_comentario error: {e}")
        raise HTTPException(status_code=500, detail="Erro ao criar comentário")


@router.put("/comentarios/{comment_id}", response_model=ComentarioOut)
async def editar_comentario(
    comment_id: str,
    body: ComentarioUpdate,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    c = db.query(Comentario).filter(Comentario.id == uuid.UUID(comment_id)).first()
    if not c:
        raise HTTPException(status_code=404, detail="Comentário não encontrado")
    if str(c.user_id) != current_user["id"]:
        raise HTTPException(status_code=403, detail="Sem permissão")

    c.texto = body.texto
    c.atualizado_em = datetime.utcnow()
    db.commit()

    return ComentarioOut(
        id=str(c.id),
        episode_id=str(c.episode_id),
        user_id=str(c.user_id),
        usuario_nome=current_user.get("nome", "Usuário"),
        usuario_foto=current_user.get("foto_url"),
        texto=c.texto,
        likes=c.likes or 0,
        criado_em=c.criado_em,
        atualizado_em=c.atualizado_em,
    )


@router.delete("/comentarios/{comment_id}")
async def deletar_comentario(
    comment_id: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    c = db.query(Comentario).filter(Comentario.id == uuid.UUID(comment_id)).first()
    if not c:
        raise HTTPException(status_code=404, detail="Comentário não encontrado")
    if str(c.user_id) != current_user["id"] and current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Sem permissão")
    c.deletado_em = datetime.utcnow()
    db.commit()
    return {"detail": "Comentário removido"}


# ─── RATINGS ─────────────────────────────────────────────────────────────────────

@router.post("/episodios/{episode_id}/rating", response_model=RatingOut)
async def dar_rating(
    episode_id: str,
    body: RatingCreate,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        eid = uuid.UUID(episode_id)
        uid = uuid.UUID(current_user["id"])

        ep = db.query(Episodio).filter(Episodio.id == eid).first()
        if not ep:
            raise HTTPException(status_code=404, detail="Episódio não encontrado")

        existing = db.query(Rating).filter(Rating.episode_id == eid, Rating.user_id == uid).first()
        if existing:
            existing.estrelas = body.estrelas
        else:
            db.add(Rating(episode_id=eid, novela_id=ep.novela_id, user_id=uid, estrelas=body.estrelas))
        db.commit()

        # Atualiza rating médio da novela
        avg = db.query(func.avg(Rating.estrelas)).filter(Rating.novela_id == ep.novela_id).scalar() or 0
        count = db.query(func.count(Rating.id)).filter(Rating.novela_id == ep.novela_id).scalar() or 0
        novela = db.query(Novela).filter(Novela.id == ep.novela_id).first()
        if novela:
            novela.rating_medio = round(float(avg), 2)
            novela.total_votos = count
            db.commit()

        return RatingOut(
            episode_id=episode_id,
            user_id=current_user["id"],
            estrelas=body.estrelas,
            criado_em=existing.criado_em if existing else datetime.utcnow(),
        )
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"dar_rating error: {e}")
        raise HTTPException(status_code=500, detail="Erro ao salvar rating")
