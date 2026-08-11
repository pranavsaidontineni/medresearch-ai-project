import json
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.collection import Collection
from app.models.paper import Paper
from app.models.saved_paper import SavedPaper
from app.models.user import User
from app.schemas.library import CollectionCreate, CollectionRead, SavePaperRequest, SavedPaperRead

router = APIRouter(prefix="/library", tags=["library"])

def paper_read(p: Paper) -> dict:
    return {"pmid": p.pmid, "title": p.title, "abstract": p.abstract, "journal": p.journal, "publication_date": p.publication_date, "doi": p.doi, "authors": json.loads(p.authors_json or "[]")}

@router.post("/collections", response_model=CollectionRead, status_code=201)
async def create_collection(payload: CollectionCreate, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    existing = await db.scalar(select(Collection).where(Collection.user_id == user.id, Collection.name == payload.name.strip()))
    if existing:
        raise HTTPException(409, "A collection with this name already exists")
    collection = Collection(user_id=user.id, name=payload.name.strip(), description=payload.description)
    db.add(collection); await db.commit(); await db.refresh(collection)
    return {"id": collection.id, "name": collection.name, "description": collection.description, "created_at": collection.created_at, "paper_count": 0}

@router.get("/collections", response_model=list[CollectionRead])
async def list_collections(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    rows = await db.execute(select(Collection, func.count(SavedPaper.id)).outerjoin(SavedPaper, SavedPaper.collection_id == Collection.id).where(Collection.user_id == user.id).group_by(Collection.id).order_by(Collection.created_at.desc()))
    return [{"id": c.id, "name": c.name, "description": c.description, "created_at": c.created_at, "paper_count": count} for c, count in rows]

@router.delete("/collections/{collection_id}", status_code=204)
async def delete_collection(collection_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    collection = await db.scalar(select(Collection).where(Collection.id == collection_id, Collection.user_id == user.id))
    if not collection: raise HTTPException(404, "Collection not found")
    await db.delete(collection); await db.commit()

@router.post("/papers/{pmid}", response_model=SavedPaperRead, status_code=201)
async def save_paper(pmid: str, payload: SavePaperRequest, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    paper = await db.scalar(select(Paper).where(Paper.pmid == pmid))
    if not paper: raise HTTPException(404, "Paper has not been cached. Search or open it first.")
    if payload.collection_id:
        collection = await db.scalar(select(Collection).where(Collection.id == payload.collection_id, Collection.user_id == user.id))
        if not collection: raise HTTPException(404, "Collection not found")
    existing = await db.scalar(select(SavedPaper).where(SavedPaper.user_id == user.id, SavedPaper.paper_id == paper.id))
    if existing:
        existing.collection_id = payload.collection_id
        await db.commit(); await db.refresh(existing)
        return {"id": existing.id, "collection_id": existing.collection_id, "created_at": existing.created_at, "paper": paper_read(paper)}
    saved = SavedPaper(user_id=user.id, paper_id=paper.id, collection_id=payload.collection_id)
    db.add(saved); await db.commit(); await db.refresh(saved)
    return {"id": saved.id, "collection_id": saved.collection_id, "created_at": saved.created_at, "paper": paper_read(paper)}

@router.get("/papers", response_model=list[SavedPaperRead])
async def list_saved_papers(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    rows = await db.execute(select(SavedPaper, Paper).join(Paper, Paper.id == SavedPaper.paper_id).where(SavedPaper.user_id == user.id).order_by(SavedPaper.created_at.desc()))
    return [{"id": s.id, "collection_id": s.collection_id, "created_at": s.created_at, "paper": paper_read(p)} for s, p in rows]

@router.delete("/papers/{pmid}", status_code=204)
async def unsave_paper(pmid: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    saved = await db.scalar(select(SavedPaper).join(Paper, Paper.id == SavedPaper.paper_id).where(SavedPaper.user_id == user.id, Paper.pmid == pmid))
    if not saved: raise HTTPException(404, "Saved paper not found")
    await db.delete(saved); await db.commit()
