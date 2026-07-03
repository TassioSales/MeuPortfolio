"""
Scraper de conteúdo agregado.
Usa yt-dlp para baixar metadados de canais/playlists do YouTube.
Os vídeos não são baixados — apenas URLs públicas são armazenadas para streaming.
"""
import uuid
from datetime import datetime
from typing import List, Dict
from loguru import logger

try:
    import yt_dlp
    YT_DLP_AVAILABLE = True
except ImportError:
    YT_DLP_AVAILABLE = False
    logger.warning("yt-dlp not installed — scraping disabled")


CANAIS_DEFAULT = [
    "https://www.youtube.com/@TeledramaturgiaOficial",
    "https://www.youtube.com/@NovelasClassicas",
]

YDL_OPTS = {
    "quiet": True,
    "extract_flat": True,
    "skip_download": True,
    "playlistend": 20,
}


async def scrape_canal(canal_url: str = "default"):
    from models.database import SessionLocal, Episodio, Novela, OrigemEnum

    urls = CANAIS_DEFAULT if canal_url == "default" else [canal_url]

    for url in urls:
        db = SessionLocal()
        try:
            videos = _fetch_playlist_info(url)
            salvos = 0
            for video in videos:
                if _salvar_video(db, video):
                    salvos += 1
            db.commit()
            logger.info(f"Scraping {url}: {salvos} novos vídeos salvos")
        except Exception as e:
            db.rollback()
            logger.error(f"scrape_canal {url} error: {e}")
        finally:
            db.close()


def _fetch_playlist_info(url: str) -> List[Dict]:
    if not YT_DLP_AVAILABLE:
        return []

    try:
        with yt_dlp.YoutubeDL(YDL_OPTS) as ydl:
            info = ydl.extract_info(url, download=False)
            entries = info.get("entries") or []
            return [
                {
                    "youtube_id": e.get("id"),
                    "titulo": e.get("title", "Sem título"),
                    "descricao": e.get("description", ""),
                    "duracao": e.get("duration", 0),
                    "thumbnail": e.get("thumbnail"),
                    "url": f"https://www.youtube.com/watch?v={e.get('id')}",
                    "upload_date": e.get("upload_date"),
                    "view_count": e.get("view_count", 0),
                    "canal": info.get("uploader", ""),
                }
                for e in entries
                if e.get("id")
            ]
    except Exception as e:
        logger.error(f"_fetch_playlist_info error: {e}")
        return []


def _salvar_video(db, video: Dict) -> bool:
    from models.database import Episodio, Novela, OrigemEnum
    from sqlalchemy import func

    try:
        youtube_id = video.get("youtube_id")
        if not youtube_id:
            return False

        existing = db.query(Episodio).filter(Episodio.youtube_id == youtube_id).first()
        if existing:
            return False

        canal = video.get("canal", "Canal Desconhecido")
        novela = db.query(Novela).filter(Novela.titulo == canal).first()
        if not novela:
            novela = Novela(
                titulo=canal,
                descricao=f"Conteúdo agregado do canal: {canal}",
                genero=["Drama"],
                idioma="pt",
                origem=OrigemEnum.agregada,
            )
            db.add(novela)
            db.flush()

        next_num = (db.query(func.max(Episodio.numero)).filter(Episodio.novela_id == novela.id).scalar() or 0) + 1

        ep = Episodio(
            novela_id=novela.id,
            youtube_id=youtube_id,
            numero=next_num,
            titulo=video["titulo"],
            descricao=video.get("descricao", ""),
            video_url=video["url"],
            duracao_segundos=int(video.get("duracao") or 0),
            thumbnail_url=video.get("thumbnail"),
            data_lancamento=_parse_date(video.get("upload_date")),
        )
        db.add(ep)
        return True
    except Exception as e:
        logger.error(f"_salvar_video error: {e}")
        return False


def _parse_date(date_str) -> datetime:
    if not date_str:
        return datetime.utcnow()
    try:
        return datetime.strptime(str(date_str), "%Y%m%d")
    except Exception:
        return datetime.utcnow()
