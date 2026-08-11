"""Database connection and session management."""

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import NullPool
from app.config import settings
from app.utils.logger import logger


def _engine_kwargs() -> dict:
    """
    Opções do engine conforme o pool escolhido.

    NullPool não aceita `pool_size`/`max_overflow` — passá-los junto faz o
    create_async_engine estourar TypeError, então em debug só o NullPool vai.
    """
    if settings.debug:
        return {"poolclass": NullPool}
    return {"pool_size": 20, "max_overflow": 40, "pool_pre_ping": True}


# Create async engine
engine = create_async_engine(
    settings.database_url.replace("postgresql://", "postgresql+asyncpg://"),
    echo=settings.debug,
    **_engine_kwargs(),
)

# Create async session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_db_session() -> AsyncSession:
    """Get database session for dependency injection."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


async def init_db():
    """Initialize database: check connection and create missing tables."""
    logger.info("🔄 Initializing database...")
    try:
        # `text()` é obrigatório no SQLAlchemy 2.x — string crua não é aceita.
        async with engine.begin() as conn:
            await conn.execute(text("SELECT 1"))
        logger.info("✅ Database connection successful")

        # Sem migrações Alembic ainda, o schema nasce dos próprios models.
        # create_all é idempotente: só cria o que ainda não existe.
        from app.db.models import Base

        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("✅ Database schema ready")
    except Exception as e:
        logger.error(f"❌ Database initialization failed: {e}")
        raise


async def close_db():
    """Close database connection."""
    logger.info("🔄 Closing database connections...")
    await engine.dispose()
    logger.info("✅ Database connections closed")


async def health_check() -> bool:
    """Check database health."""
    try:
        async with engine.begin() as conn:
            await conn.execute(text("SELECT 1"))
        return True
    except Exception as e:
        logger.error(f"❌ Database health check failed: {e}")
        return False
