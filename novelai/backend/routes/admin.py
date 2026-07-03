from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from typing import List, Optional
from loguru import logger
from datetime import datetime
import uuid

from models.database import get_db, Novela, Episodio, Usuario, FilaGeracao, FilaStatusEnum, OrigemEnum
from models.schemas import GerarEpisodioRequest, GeracaoOut, AdminStatsOut, NovelaOut
from models.auth import get_current_admin
from routes.public import _novela_to_out

router = APIRouter()


@router.get("/stats", response_model=AdminStatsOut)
async def admin_stats(admin: dict = Depends(get_current_admin), db: Session = Depends(get_db)):
    try:
        total_novelas = db.query(func.count(Novela.id)).scalar() or 0
        total_episodios = db.query(func.count(Episodio.id)).scalar() or 0
        total_usuarios = db.query(func.count(Usuario.id)).scalar() or 0
        total_views = db.query(func.sum(Novela.views)).scalar() or 0
        geracoes_pendentes = db.query(func.count(FilaGeracao.id)).filter(FilaGeracao.status == FilaStatusEnum.pendente).scalar() or 0
        geracoes_concluidas = db.query(func.count(FilaGeracao.id)).filter(FilaGeracao.status == FilaStatusEnum.concluido).scalar() or 0

        return AdminStatsOut(
            total_novelas=total_novelas,
            total_episodios=total_episodios,
            total_usuarios=total_usuarios,
            total_views=int(total_views),
            geracoes_pendentes=geracoes_pendentes,
            geracoes_concluidas=geracoes_concluidas,
        )
    except Exception as e:
        logger.error(f"admin_stats error: {e}")
        raise HTTPException(status_code=500, detail="Erro ao buscar estatísticas")


@router.post("/generate/episodio", response_model=GeracaoOut, status_code=202)
async def gerar_episodio(
    body: GerarEpisodioRequest,
    background_tasks: BackgroundTasks,
    admin: dict = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    try:
        geracao = FilaGeracao(
            status=FilaStatusEnum.pendente,
            tipo="episodio",
            parametros=body.model_dump(),
        )
        db.add(geracao)
        db.commit()
        db.refresh(geracao)

        geracao_id = str(geracao.id)
        background_tasks.add_task(_processar_geracao, geracao_id, body.model_dump())

        return GeracaoOut(
            id=geracao_id,
            status="pendente",
            tipo="episodio",
            parametros=body.model_dump(),
            criado_em=geracao.criado_em,
        )
    except Exception as e:
        db.rollback()
        logger.error(f"gerar_episodio error: {e}")
        raise HTTPException(status_code=500, detail="Erro ao enfileirar geração")


@router.get("/queue", response_model=List[GeracaoOut])
async def get_queue(
    admin: dict = Depends(get_current_admin),
    db: Session = Depends(get_db),
    status: Optional[str] = None,
):
    try:
        q = db.query(FilaGeracao).order_by(desc(FilaGeracao.criado_em)).limit(50)
        if status:
            q = q.filter(FilaGeracao.status == status)
        rows = q.all()
        return [_geracao_to_out(r) for r in rows]
    except Exception as e:
        logger.error(f"get_queue error: {e}")
        return []


@router.post("/approve/{geracao_id}")
async def aprovar_video(
    geracao_id: str,
    admin: dict = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    geracao = db.query(FilaGeracao).filter(FilaGeracao.id == uuid.UUID(geracao_id)).first()
    if not geracao:
        raise HTTPException(status_code=404, detail="Geração não encontrada")
    if geracao.status != FilaStatusEnum.concluido:
        raise HTTPException(status_code=400, detail="Geração ainda não concluída")

    params = geracao.parametros or {}
    video_url = geracao.video_url_resultado

    novela_id_str = params.get("novela_id")
    if novela_id_str:
        novela = db.query(Novela).filter(Novela.id == uuid.UUID(novela_id_str)).first()
    else:
        novela = Novela(
            titulo=f"Novela: {params.get('tema', 'Sem título')}",
            descricao=f"Gerada com IA. Tema: {params.get('tema')}",
            genero=["Drama"],
            idioma="pt",
            origem=OrigemEnum.gerada_ia,
        )
        db.add(novela)
        db.flush()

    next_num = (db.query(func.max(Episodio.numero)).filter(Episodio.novela_id == novela.id).scalar() or 0) + 1
    ep = Episodio(
        novela_id=novela.id,
        numero=next_num,
        titulo=f"Episódio {next_num}",
        descricao="Gerado com IA",
        video_url=video_url or "",
    )
    db.add(ep)

    geracao.status = FilaStatusEnum.publicado
    db.commit()
    return {"detail": "Vídeo aprovado e publicado na biblioteca"}


@router.delete("/videos/{novela_id}")
async def remover_video(
    novela_id: str,
    admin: dict = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    novela = db.query(Novela).filter(Novela.id == uuid.UUID(novela_id)).first()
    if not novela:
        raise HTTPException(status_code=404)
    db.delete(novela)
    db.commit()
    return {"detail": "Novela e episódios removidos"}


@router.post("/scrape/manual")
async def scrape_manual(
    background_tasks: BackgroundTasks,
    admin: dict = Depends(get_current_admin),
    canal: Optional[str] = None,
):
    from services.scraper import scrape_canal
    background_tasks.add_task(scrape_canal, canal or "default")
    return {"detail": "Scraping iniciado em background"}


# ─── Helpers ─────────────────────────────────────────────────────────────────────

def _geracao_to_out(g: FilaGeracao) -> GeracaoOut:
    return GeracaoOut(
        id=str(g.id),
        status=g.status.value,
        tipo=g.tipo,
        parametros=g.parametros or {},
        video_url_resultado=g.video_url_resultado,
        erro_mensagem=g.erro_mensagem,
        criado_em=g.criado_em,
        iniciado_em=g.iniciado_em,
        concluido_em=g.concluido_em,
    )


async def _processar_geracao(geracao_id: str, params: dict):
    db = None
    try:
        from models.database import SessionLocal
        db = SessionLocal()
        geracao = db.query(FilaGeracao).filter(FilaGeracao.id == uuid.UUID(geracao_id)).first()
        if not geracao:
            return

        geracao.status = FilaStatusEnum.processando
        geracao.iniciado_em = datetime.utcnow()
        db.commit()

        from services.generator import gerar_conteudo
        video_url = await gerar_conteudo(params)

        geracao.status = FilaStatusEnum.concluido
        geracao.video_url_resultado = video_url
        geracao.concluido_em = datetime.utcnow()
        db.commit()
        logger.info(f"Geração {geracao_id} concluída: {video_url}")
    except Exception as e:
        logger.error(f"_processar_geracao {geracao_id} error: {e}")
        if db:
            geracao = db.query(FilaGeracao).filter(FilaGeracao.id == uuid.UUID(geracao_id)).first()
            if geracao:
                geracao.status = FilaStatusEnum.erro
                geracao.erro_mensagem = str(e)
                geracao.concluido_em = datetime.utcnow()
                db.commit()
    finally:
        if db:
            db.close()
