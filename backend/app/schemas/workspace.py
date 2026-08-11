from datetime import datetime
from pydantic import BaseModel, Field

class WorkspaceCreate(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    research_question: str | None = Field(default=None, max_length=1000)

class WorkspacePaperRead(BaseModel):
    pmid: str
    title: str
    journal: str | None
    publication_date: str | None
    abstract_available: bool

class WorkspaceRead(BaseModel):
    id: int
    name: str
    research_question: str | None
    created_at: datetime
    papers: list[WorkspacePaperRead]

class WorkspaceAskRequest(BaseModel):
    question: str = Field(min_length=5, max_length=1200)

class GroundedSource(BaseModel):
    pmid: str
    title: str
    supporting_excerpt: str

class WorkspaceAnswer(BaseModel):
    answer: str
    evidence_strength: str
    uncertainty: str
    sources: list[GroundedSource]
    insufficient_evidence: bool
