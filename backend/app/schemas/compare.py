from pydantic import BaseModel, Field

class CompareRequest(BaseModel):
    pmids: list[str] = Field(min_length=2, max_length=5)

class PaperComparison(BaseModel):
    papers: list[str]
    research_questions: str
    populations: str
    study_design_comparison: str
    interventions_or_exposures: str
    outcomes: str
    similarities: list[str]
    differences: list[str]
    findings_comparison: str
    limitations_comparison: str
    overall_takeaway: str
    uncertainty: str
