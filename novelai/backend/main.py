from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from loguru import logger
import uvicorn
import os

from config import settings
from routes import public as public_routes
from routes import auth as auth_routes
from routes import user as user_routes
from routes import admin as admin_routes


limiter = Limiter(key_func=get_remote_address)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("NovelAI API starting up...")
    try:
        from models.database import create_tables
        create_tables()
        logger.info("Tabelas criadas/verificadas com sucesso")
        _seed_if_empty()
    except Exception as e:
        logger.warning(f"DB setup error: {e}")
    yield
    logger.info("NovelAI API shutting down...")


def _seed_if_empty():
    from models.database import SessionLocal, Novela, Usuario, OrigemEnum
    from models.auth import hash_password
    from models.database import UserRoleEnum
    import uuid

    db = SessionLocal()
    try:
        if db.query(Novela).count() == 0:
            novelas = [
                Novela(titulo="Coração Partido", descricao="Uma história de amor e rivalidade em São Paulo",
                       genero=["Drama", "Romance"], idioma="pt", ano=2024,
                       poster_url="https://picsum.photos/seed/novela1/400/600",
                       backdrop_url="https://picsum.photos/seed/novela1/1280/720",
                       rating_medio=4.2, total_votos=120, views=15420, origem=OrigemEnum.agregada),
                Novela(titulo="Destino Duplo", descricao="Gêmeas separadas ao nascer se reencontram décadas depois",
                       genero=["Drama", "Suspense"], idioma="pt", ano=2024,
                       poster_url="https://picsum.photos/seed/novela2/400/600",
                       backdrop_url="https://picsum.photos/seed/novela2/1280/720",
                       rating_medio=3.8, total_votos=85, views=8930, origem=OrigemEnum.agregada),
                Novela(titulo="Amor de Verão", descricao="Romance proibido em uma cidade litorânea",
                       genero=["Romance", "Comédia"], idioma="pt", ano=2023,
                       poster_url="https://picsum.photos/seed/novela3/400/600",
                       backdrop_url="https://picsum.photos/seed/novela3/1280/720",
                       rating_medio=4.5, total_votos=210, views=22100, origem=OrigemEnum.gerada_ia),
                Novela(titulo="Herança Maldita", descricao="Família rica esconde segredos sombrios",
                       genero=["Drama", "Suspense", "Mistério"], idioma="pt", ano=2024,
                       poster_url="https://picsum.photos/seed/novela4/400/600",
                       backdrop_url="https://picsum.photos/seed/novela4/1280/720",
                       rating_medio=4.0, total_votos=95, views=11200, origem=OrigemEnum.agregada),
                Novela(titulo="Jogo do Destino", descricao="Rivalidade corporativa que vira caso de amor",
                       genero=["Drama", "Romance"], idioma="pt", ano=2023,
                       poster_url="https://picsum.photos/seed/novela5/400/600",
                       backdrop_url="https://picsum.photos/seed/novela5/1280/720",
                       rating_medio=3.6, total_votos=67, views=6750, origem=OrigemEnum.gerada_ia),
            ]
            db.add_all(novelas)
            db.flush()

            from models.database import Episodio
            eps_data = [
                ("Coração Partido", "dQw4w9WgXcQ", "Episódio 1 - Piloto"),
                ("Destino Duplo", "ScMzIvxBSi4", "Episódio 1 - O Encontro"),
                ("Amor de Verão", "9bZkp7q19f0", "Episódio 1 - Verão Eterno"),
                ("Herança Maldita", "kJQP7kiw5Fk", "Episódio 1 - Segredos"),
                ("Jogo do Destino", "JGwWNGJdvx8", "Episódio 1 - Rivalidade"),
            ]
            for novela in novelas:
                for titulo_nov, yt_id, ep_titulo in eps_data:
                    if novela.titulo == titulo_nov:
                        db.add(Episodio(
                            novela_id=novela.id,
                            youtube_id=yt_id,
                            numero=1,
                            titulo=ep_titulo,
                            video_url=f"https://www.youtube.com/watch?v={yt_id}",
                            duracao_segundos=2700,
                            thumbnail_url=f"https://img.youtube.com/vi/{yt_id}/maxresdefault.jpg",
                        ))
            db.commit()
            logger.info("Seed: 5 novelas e episódios criados")

        if db.query(Usuario).count() == 0:
            admin = Usuario(
                email="tassiolucian.ljs@gmail.com",
                password_hash=hash_password("Tassio@2025"),
                nome="Tassio",
                role=UserRoleEnum.admin,
                idioma_preferido="pt",
                qualidade_padrao="1080p",
                legendas_padrao="off",
            )
            db.add(admin)
            db.commit()
            logger.info("Seed: usuário admin criado — tassiolucian.ljs@gmail.com / Tassio@2025")
    except Exception as e:
        db.rollback()
        logger.error(f"Seed error: {e}")
    finally:
        db.close()


app = FastAPI(
    title="NovelAI API",
    description="Plataforma de streaming de novelas em vídeo",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Servir vídeos locais
os.makedirs(settings.videos_path, exist_ok=True)
app.mount("/videos", StaticFiles(directory=settings.videos_path), name="videos")

app.include_router(public_routes.router, prefix="/api", tags=["Público"])
app.include_router(auth_routes.router, prefix="/api/auth", tags=["Autenticação"])
app.include_router(user_routes.router, prefix="/api/usuarios", tags=["Usuários"])
app.include_router(admin_routes.router, prefix="/api/admin", tags=["Admin"])


@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "novelai-api"}


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(status_code=500, content={"detail": "Erro interno do servidor"})


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
