from pydantic import BaseModel, Field

class PaperRead(BaseModel):
    pmid: str
    title: str
    abstract: str | None = None
    journal: str | None = None
    publication_date: str | None = None
    doi: str | None = None
    authors: list[str] = Field(default_factory=list)

class PaperSearchResponse(BaseModel):
    total: int
    papers: list[PaperRead]

class StudyCharacteristics(BaseModel):
    study_type: str
    setting: str
    population: str
    sample_size: str
    intervention_or_exposure: str
    comparator: str
    outcomes: list[str]

class PaperSummary(BaseModel):
    overview: str
    research_question: str
    study_characteristics: StudyCharacteristics
    study_design: str
    population: str
    key_findings: list[str]
    limitations: list[str]
    clinical_relevance: str
    evidence_caveats: list[str]
    uncertainty: str

class PatientExplanation(BaseModel):
    plain_language_summary: str
    important_terms: list[str]
    what_the_study_does_not_show: list[str]
    uncertainty: str

class Citation(BaseModel):
    apa: str
    mla: str
    vancouver: str
