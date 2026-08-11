import hashlib
import json
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.ai_cache import AIAnalysisCache


def make_cache_key(analysis_type: str, payload: object) -> str:
    canonical = json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(f"{analysis_type}:{canonical}".encode("utf-8")).hexdigest()


async def get_cached(db: AsyncSession, analysis_type: str, payload: object):
    key = make_cache_key(analysis_type, payload)
    row = await db.scalar(select(AIAnalysisCache).where(AIAnalysisCache.cache_key == key))
    if row is None:
        return None
    return json.loads(row.response_json)


async def put_cached(db: AsyncSession, analysis_type: str, payload: object, response: dict) -> None:
    key = make_cache_key(analysis_type, payload)
    row = await db.scalar(select(AIAnalysisCache).where(AIAnalysisCache.cache_key == key))
    encoded = json.dumps(response, ensure_ascii=False, separators=(",", ":"))
    if row is None:
        db.add(AIAnalysisCache(cache_key=key, analysis_type=analysis_type, response_json=encoded))
    else:
        row.response_json = encoded
    await db.commit()
