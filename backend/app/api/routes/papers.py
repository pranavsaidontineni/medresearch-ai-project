import json
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.paper import Paper
from app.models.search_history import SearchHistory
from app.models.user import User
from app.schemas.compare import CompareRequest, PaperComparison
from app.schemas.paper import PaperRead, PaperSearchResponse, PaperSummary, PatientExplanation, Citation
from app.services.citation_service import format_citations
from app.services.gemini_service import GeminiService
from app.services.pubmed_service import PubMedError, PubMedService
from app.services.cache_service import get_cached, put_cached

router = APIRouter(prefix="/papers", tags=["papers"])
pubmed = PubMedService()


def cache_paper(db: AsyncSession, data: dict) -> Paper:
    return Paper(pmid=data["pmid"], title=data["title"], abstract=data.get("abstract"), journal=data.get("journal"), publication_date=data.get("publication_date"), doi=data.get("doi"), authors_json=json.dumps(data.get("authors", [])))

async def persist_papers(db: AsyncSession, papers: list[dict]):
    cached = []
    for data in papers:
        existing = await db.scalar(select(Paper).where(Paper.pmid == data["pmid"]))
        if existing:
            existing.title = data["title"]; existing.abstract = data.get("abstract"); existing.journal = data.get("journal"); existing.publication_date = data.get("publication_date"); existing.doi = data.get("doi"); existing.authors_json = json.dumps(data.get("authors", [])); cached.append(existing)
        else:
            item = cache_paper(db, data); db.add(item); cached.append(item)
    await db.commit()
    for item in cached: await db.refresh(item)
    return cached

def read_paper(p: Paper) -> dict:
    return {"pmid": p.pmid, "title": p.title, "abstract": p.abstract, "journal": p.journal, "publication_date": p.publication_date, "doi": p.doi, "authors": json.loads(p.authors_json or "[]")}

@router.get("/search", response_model=PaperSearchResponse)
async def search_papers(q: str = Query(min_length=2, max_length=300), limit: int = Query(default=10, ge=1, le=20), offset: int = Query(default=0, ge=0), user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    try:
        total, ids = await pubmed.search(q, limit, offset); papers = await pubmed.fetch(ids); cached = await persist_papers(db, papers)
        db.add(SearchHistory(user_id=user.id, query=q, result_count=total)); await db.commit()
        return {"total": total, "papers": [read_paper(p) for p in cached]}
    except PubMedError as exc: raise HTTPException(status_code=502, detail=str(exc)) from exc

@router.get("/history")
async def search_history(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    rows = await db.execute(select(SearchHistory).where(SearchHistory.user_id == user.id).order_by(SearchHistory.created_at.desc()).limit(20))
    return [{"id": r.id, "query": r.query, "result_count": r.result_count, "created_at": r.created_at} for r in rows.scalars()]

@router.post("/compare", response_model=PaperComparison)
async def compare_papers(payload: CompareRequest, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    if len(set(payload.pmids)) != len(payload.pmids): raise HTTPException(400, "PMIDs must be unique")
    try:
        papers = await pubmed.fetch(payload.pmids)
        found = {p["pmid"] for p in papers}; missing = [p for p in payload.pmids if p not in found]
        if missing: raise HTTPException(404, f"Papers not found: {', '.join(missing)}")
        cache_payload = [{"pmid": p["pmid"], "title": p["title"], "abstract": p.get("abstract") or ""} for p in papers]
        cached = await get_cached(db, "paper_comparison", cache_payload)
        if cached is not None:
            return cached
        result = await (await get_ai()).compare_papers(papers)
        await put_cached(db, "paper_comparison", cache_payload, result.model_dump())
        return result
    except RuntimeError as exc: raise HTTPException(503, "AI service is temporarily unavailable") from exc
    except PubMedError as exc: raise HTTPException(502, str(exc)) from exc

@router.get("/{pmid}", response_model=PaperRead)
async def get_paper(pmid: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    try: papers = await pubmed.fetch([pmid])
    except PubMedError as exc: raise HTTPException(status_code=502, detail=str(exc)) from exc
    if not papers: raise HTTPException(status_code=404, detail="Paper not found")
    cached = await persist_papers(db, papers); return read_paper(cached[0])

async def get_ai() -> GeminiService:
    try: return GeminiService()
    except RuntimeError as exc: raise HTTPException(status_code=503, detail=str(exc)) from exc

@router.post("/{pmid}/summarize", response_model=PaperSummary)
async def summarize_paper(pmid: str, _: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    try:
        papers = await pubmed.fetch([pmid]);
        if not papers: raise HTTPException(404, "Paper not found")
        paper = papers[0]
        payload = {"pmid": paper["pmid"], "title": paper["title"], "abstract": paper.get("abstract") or ""}
        cached = await get_cached(db, "paper_summary", payload)
        if cached is not None:
            return cached
        result = await (await get_ai()).summarize_paper(paper["title"], paper.get("abstract") or "")
        await put_cached(db, "paper_summary", payload, result.model_dump())
        return result
    except ValueError as exc: raise HTTPException(400, str(exc)) from exc
    except RuntimeError as exc: raise HTTPException(503, "AI service is temporarily unavailable") from exc
    except PubMedError as exc: raise HTTPException(502, str(exc)) from exc

@router.post("/{pmid}/patient-explanation", response_model=PatientExplanation)
async def patient_explanation(pmid: str, _: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    try:
        papers = await pubmed.fetch([pmid]);
        if not papers: raise HTTPException(404, "Paper not found")
        paper = papers[0]
        payload = {"pmid": paper["pmid"], "title": paper["title"], "abstract": paper.get("abstract") or ""}
        cached = await get_cached(db, "patient_explanation", payload)
        if cached is not None:
            return cached
        result = await (await get_ai()).patient_explanation(paper["title"], paper.get("abstract") or "")
        await put_cached(db, "patient_explanation", payload, result.model_dump())
        return result
    except ValueError as exc: raise HTTPException(400, str(exc)) from exc
    except RuntimeError as exc: raise HTTPException(503, "AI service is temporarily unavailable") from exc
    except PubMedError as exc: raise HTTPException(502, str(exc)) from exc


@router.get("/{pmid}/citation", response_model=Citation)
async def citation(pmid: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    paper = await db.scalar(select(Paper).where(Paper.pmid == pmid))
    if paper is None:
        try:
            papers = await pubmed.fetch([pmid])
        except PubMedError as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc
        if not papers:
            raise HTTPException(status_code=404, detail="Paper not found")
        paper = (await persist_papers(db, papers))[0]
    return format_citations(read_paper(paper))
