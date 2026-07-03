from typing import List, Optional
from loguru import logger
from models.database import db
from models.schemas import NovelaOut


async def get_recommendations(user_id: Optional[str], limit: int = 20) -> List[dict]:
    """
    Algoritmo de recomendação baseado em:
    - Histórico do usuário (gêneros mais assistidos)
    - Trending global
    - Colaborativo simples
    """
    try:
        if user_id:
            return await _personalized(user_id, limit)
        return await _trending(limit)
    except Exception as e:
        logger.error(f"get_recommendations error: {e}")
        return await _trending(limit)


async def _personalized(user_id: str, limit: int) -> List[dict]:
    try:
        # 1. Pega histórico recente do usuário
        historico = (
            db.table("historico_reproducao")
            .select("episode_id, episodios(novela_id, novelas(genero))")
            .eq("user_id", user_id)
            .order("assistido_em", desc=True)
            .limit(20)
            .execute()
        )

        generos_freq: dict = {}
        novelas_assistidas: set = set()

        for h in (historico.data or []):
            ep = h.get("episodios") or {}
            novela = ep.get("novelas") or {}
            novela_id = ep.get("novela_id")
            if novela_id:
                novelas_assistidas.add(novela_id)
            for g in (novela.get("genero") or []):
                generos_freq[g] = generos_freq.get(g, 0) + 1

        # Gênero favorito
        top_genero = max(generos_freq, key=generos_freq.get) if generos_freq else None

        # 2. Busca novelas do mesmo gênero que o usuário não assistiu
        if top_genero:
            candidates = (
                db.table("novelas")
                .select("*")
                .contains("genero", [top_genero])
                .order("rating_medio", desc=True)
                .limit(limit * 2)
                .execute()
            )
            novelas = [n for n in (candidates.data or []) if n["id"] not in novelas_assistidas]
        else:
            novelas = []

        # 3. Complementa com trending se necessário
        if len(novelas) < limit:
            trending = (
                db.table("novelas")
                .select("*")
                .order("views", desc=True)
                .limit(limit - len(novelas) + 10)
                .execute()
            )
            seen_ids = {n["id"] for n in novelas}
            for n in (trending.data or []):
                if n["id"] not in seen_ids and n["id"] not in novelas_assistidas:
                    novelas.append(n)

        return [_to_novela_out(n) for n in novelas[:limit]]
    except Exception as e:
        logger.error(f"_personalized error: {e}")
        return await _trending(limit)


async def _trending(limit: int) -> List[dict]:
    result = (
        db.table("novelas")
        .select("*")
        .order("views", desc=True)
        .limit(limit)
        .execute()
    )
    return [_to_novela_out(n) for n in (result.data or [])]


def _to_novela_out(data: dict) -> dict:
    data.pop("episodios", None)
    return data
