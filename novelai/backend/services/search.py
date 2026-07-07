"""
Busca avançada com autocomplete.
Usa Supabase full-text search quando disponível.
"""
from typing import List, Optional, Dict
from loguru import logger

from models.database import db


async def search_autocomplete(q: str, limit: int = 10) -> List[Dict]:
    if len(q) < 2:
        return []

    try:
        result = (
            db.table("novelas")
            .select("id, titulo, poster_url, genero")
            .ilike("titulo", f"%{q}%")
            .order("views", desc=True)
            .limit(limit)
            .execute()
        )
        return [
            {
                "id": n["id"],
                "titulo": n["titulo"],
                "poster_url": n.get("poster_url"),
                "genero": n.get("genero", []),
                "tipo": "novela",
            }
            for n in (result.data or [])
        ]
    except Exception as e:
        logger.error(f"search_autocomplete error: {e}")
        return []
