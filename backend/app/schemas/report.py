from pydantic import BaseModel, Field

class StudySnapshot(BaseModel):
    pmid: str
    title: str
    study_design: str
    population: str
    sample_size: str
    intervention_or_exposure: str
    comparator: str
    outcomes: list[str]
    key_findings: list[str]
    limitations: list[str]

class LiteratureReviewReport(BaseModel):
    title: str
    research_question: str
    scope: str
    included_studies: list[StudySnapshot]
    synthesis: str
    areas_of_agreement: list[str]
    areas_of_disagreement: list[str]
    evidence_gaps: list[str]
    limitations_of_review: list[str]
    conclusion: str
    uncertainty: str
    cited_pmids: list[str] = Field(default_factory=list)

class ResearchReportRead(BaseModel):
    id: int
    workspace_id: int
    title: str
    created_at: str
    report: LiteratureReviewReport
