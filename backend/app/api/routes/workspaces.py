from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import PlainTextResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.paper import Paper
from app.models.research_workspace import ResearchWorkspace, WorkspacePaper
from app.models.user import User
from app.schemas.workspace import WorkspaceAnswer, WorkspaceAskRequest, WorkspaceCreate, WorkspacePaperRead, WorkspaceRead
from app.schemas.report import LiteratureReviewReport
from app.services.retrieval_service import retrieve
from app.services.gemini_service import GeminiService
from app.services.cache_service import get_cached, put_cached
from app.models.research_report import ResearchReport
from app.schemas.report import ResearchReportRead
import json

router = APIRouter(prefix="/workspaces", tags=["research-workspaces"])

async def owned_workspace(workspace_id: int, user_id: int, db: AsyncSession) -> ResearchWorkspace:
    ws = await db.scalar(select(ResearchWorkspace).where(ResearchWorkspace.id == workspace_id, ResearchWorkspace.user_id == user_id))
    if ws is None:
        raise HTTPException(404, "Research workspace not found")
    return ws

async def workspace_payload(ws: ResearchWorkspace, db: AsyncSession) -> dict:
    rows = await db.execute(select(Paper).join(WorkspacePaper, WorkspacePaper.paper_id == Paper.id).where(WorkspacePaper.workspace_id == ws.id).order_by(WorkspacePaper.added_at.asc()))
    papers = rows.scalars().all()
    return {"id": ws.id, "name": ws.name, "research_question": ws.research_question, "created_at": ws.created_at, "papers": [WorkspacePaperRead(pmid=p.pmid, title=p.title, journal=p.journal, publication_date=p.publication_date, abstract_available=bool(p.abstract)).model_dump() for p in papers]}

@router.post("", response_model=WorkspaceRead)
async def create_workspace(payload: WorkspaceCreate, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    ws = ResearchWorkspace(user_id=user.id, name=payload.name.strip(), research_question=payload.research_question.strip() if payload.research_question else None)
    db.add(ws); await db.commit(); await db.refresh(ws)
    return await workspace_payload(ws, db)

@router.get("", response_model=list[WorkspaceRead])
async def list_workspaces(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    rows = await db.execute(select(ResearchWorkspace).where(ResearchWorkspace.user_id == user.id).order_by(ResearchWorkspace.created_at.desc()))
    return [await workspace_payload(ws, db) for ws in rows.scalars().all()]

@router.get("/{workspace_id}", response_model=WorkspaceRead)
async def get_workspace(workspace_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    ws = await owned_workspace(workspace_id, user.id, db)
    return await workspace_payload(ws, db)

@router.patch("/{workspace_id}", response_model=WorkspaceRead)
async def rename_workspace(workspace_id: int, payload: WorkspaceCreate, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    ws = await owned_workspace(workspace_id, user.id, db)
    if not payload.name or not payload.name.strip():
        raise HTTPException(400, "Workspace name cannot be empty")
    ws.name = payload.name.strip()
    ws.research_question = payload.research_question.strip() if payload.research_question else ws.research_question
    await db.commit(); await db.refresh(ws)
    return await workspace_payload(ws, db)

@router.delete("/{workspace_id}")
async def delete_workspace(workspace_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    ws = await owned_workspace(workspace_id, user.id, db)
    # delete workspace and associated workspace papers and reports
    from sqlalchemy import delete
    await db.execute(delete(WorkspacePaper).where(WorkspacePaper.workspace_id == ws.id))
    # also delete reports
    await db.execute(delete(ResearchReport).where(ResearchReport.workspace_id == ws.id))
    await db.delete(ws)
    await db.commit()
    return {"status": "deleted"}

@router.post("/{workspace_id}/papers/{pmid}", response_model=WorkspaceRead)
async def add_paper(workspace_id: int, pmid: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    ws = await owned_workspace(workspace_id, user.id, db)
    paper = await db.scalar(select(Paper).where(Paper.pmid == pmid))
    if paper is None:
        raise HTTPException(404, "Paper must be cached before adding it to a workspace")
    existing = await db.scalar(select(WorkspacePaper).where(WorkspacePaper.workspace_id == ws.id, WorkspacePaper.paper_id == paper.id))
    if existing is None:
        db.add(WorkspacePaper(workspace_id=ws.id, paper_id=paper.id)); await db.commit()
    return await workspace_payload(ws, db)

@router.delete("/{workspace_id}/papers/{pmid}", response_model=WorkspaceRead)
async def remove_paper(workspace_id: int, pmid: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    ws = await owned_workspace(workspace_id, user.id, db)
    paper = await db.scalar(select(Paper).where(Paper.pmid == pmid))
    if paper:
        link = await db.scalar(select(WorkspacePaper).where(WorkspacePaper.workspace_id == ws.id, WorkspacePaper.paper_id == paper.id))
        if link:
            await db.delete(link); await db.commit()
    return await workspace_payload(ws, db)

@router.post("/{workspace_id}/ask", response_model=WorkspaceAnswer)
async def ask_workspace(workspace_id: int, payload: WorkspaceAskRequest, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    ws = await owned_workspace(workspace_id, user.id, db)
    rows = await db.execute(select(Paper).join(WorkspacePaper, WorkspacePaper.paper_id == Paper.id).where(WorkspacePaper.workspace_id == ws.id))
    papers = rows.scalars().all()
    retrieved = retrieve(payload.question, papers)
    if not retrieved:
        return WorkspaceAnswer(answer="I couldn't find enough relevant evidence in the papers in this workspace to answer that question.", evidence_strength="Insufficient", uncertainty="The selected papers did not contain retrievable abstract text matching the question.", sources=[], insufficient_evidence=True)
    try:
        cache_payload = {"workspace_id": ws.id, "question": payload.question, "sources": [{"pmid": c["pmid"], "excerpt": c["excerpt"]} for c in retrieved]}
        cached = await get_cached(db, "workspace_question", cache_payload)
        if cached is not None:
            return cached
        result = await GeminiService().answer_workspace_question(payload.question, retrieved)
        await put_cached(db, "workspace_question", cache_payload, result.model_dump() if hasattr(result, "model_dump") else result)
        return result
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(503, "AI service is temporarily unavailable") from exc


@router.post("/{workspace_id}/literature-review", response_model=LiteratureReviewReport)
async def generate_literature_review(workspace_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    ws = await owned_workspace(workspace_id, user.id, db)
    rows = await db.execute(
        select(Paper)
        .join(WorkspacePaper, WorkspacePaper.paper_id == Paper.id)
        .where(WorkspacePaper.workspace_id == ws.id)
        .order_by(WorkspacePaper.added_at.asc())
    )
    papers = rows.scalars().all()
    if not papers:
        raise HTTPException(400, "Add at least one paper to the workspace before generating a literature review.")
    try:
        review_payload = {"research_question": ws.research_question or "Synthesize the evidence represented by the selected papers.", "papers": [{"pmid": p.pmid, "title": p.title, "abstract": p.abstract or "No abstract available."} for p in papers]}
        cached = await get_cached(db, "literature_review", review_payload)
        if cached is not None:
            return cached
        result = await GeminiService().generate_literature_review(**review_payload)
        report_dict = result.model_dump() if hasattr(result, "model_dump") else result
        await put_cached(db, "literature_review", review_payload, report_dict)
        report = ResearchReport(user_id=user.id, workspace_id=ws.id, title=result.title, report_json=json.dumps(report_dict, ensure_ascii=False))
        db.add(report)
        await db.commit()
        return result
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(503, "AI service is temporarily unavailable") from exc


@router.get("/{workspace_id}/reports", response_model=list[ResearchReportRead])
async def list_reports(workspace_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    await owned_workspace(workspace_id, user.id, db)
    rows = await db.execute(select(ResearchReport).where(ResearchReport.workspace_id == workspace_id, ResearchReport.user_id == user.id).order_by(ResearchReport.created_at.desc()))
    return [ResearchReportRead(id=r.id, workspace_id=r.workspace_id, title=r.title, created_at=r.created_at.isoformat(), report=json.loads(r.report_json)) for r in rows.scalars().all()]

@router.get("/{workspace_id}/reports/{report_id}/markdown", response_class=PlainTextResponse)
async def export_report_markdown(workspace_id: int, report_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    await owned_workspace(workspace_id, user.id, db)
    report = await db.scalar(select(ResearchReport).where(ResearchReport.id == report_id, ResearchReport.workspace_id == workspace_id, ResearchReport.user_id == user.id))
    if report is None:
        raise HTTPException(404, "Research report not found")
    data = json.loads(report.report_json)
    lines = [f"# {data.get('title', report.title)}", "", f"**Research question:** {data.get('research_question', '')}", "", f"## Scope\n{data.get('scope', '')}", "", f"## Synthesis\n{data.get('synthesis', '')}", "", "## Areas of agreement"]
    lines += [f"- {x}" for x in data.get('areas_of_agreement', [])]
    lines += ["", "## Areas of disagreement"] + [f"- {x}" for x in data.get('areas_of_disagreement', [])]
    lines += ["", "## Evidence gaps"] + [f"- {x}" for x in data.get('evidence_gaps', [])]
    lines += ["", "## Included studies"]
    for s in data.get('included_studies', []):
        lines += [f"### {s.get('title', '')} (PMID {s.get('pmid', '')})", f"- Study design: {s.get('study_design', '')}", f"- Population: {s.get('population', '')}", f"- Sample size: {s.get('sample_size', '')}", f"- Intervention/exposure: {s.get('intervention_or_exposure', '')}", f"- Comparator: {s.get('comparator', '')}", "- Key findings:"]
        lines += [f"  - {x}" for x in s.get('key_findings', [])]
    lines += ["", "## Limitations of this review"] + [f"- {x}" for x in data.get('limitations_of_review', [])]
    lines += ["", f"## Conclusion\n{data.get('conclusion', '')}", "", f"**Uncertainty:** {data.get('uncertainty', '')}", "", f"**Cited PMIDs:** {', '.join(data.get('cited_pmids', []))}"]
    return "\n".join(lines)
