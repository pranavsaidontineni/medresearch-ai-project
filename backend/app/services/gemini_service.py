import asyncio
import logging
import re
from google import genai
from google.genai import types
from google.genai.errors import ClientError
from app.core.config import get_settings
from app.schemas.compare import PaperComparison
from app.schemas.paper import PaperSummary, PatientExplanation

logger = logging.getLogger(__name__)

class GeminiService:
    def __init__(self):
        settings = get_settings()
        if not settings.gemini_api_key:
            raise RuntimeError("GEMINI_API_KEY is not configured")
        self.model = settings.gemini_model or "gemini-flash-latest"
        self.fallback_models = [
            model for model in ["gemini-flash-latest", "gemini-flash-lite-latest"]
            if model and model != self.model
        ]
        self.client = genai.Client(api_key=settings.gemini_api_key)

    def _generate(self, prompt: str, schema, model_name: str | None = None):
        return self.client.models.generate_content(
            model=model_name or self.model,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=schema,
                temperature=0.15,
            ),
        )

    @staticmethod
    def _extract_status_code(exc: Exception) -> int | None:
        status = getattr(exc, "status_code", None)
        if isinstance(status, int):
            return status
        code = getattr(exc, "code", None)
        if isinstance(code, int):
            return code
        text = str(exc)
        match = re.search(r"(\d{3})\s+[A-Z_]+", text)
        if match:
            return int(match.group(1))
        return None

    @classmethod
    def _should_fallback(cls, exc: Exception) -> bool:
        status = cls._extract_status_code(exc)
        return status in {400, 404, 429, 500, 502, 503} or \
            ("UNAVAILABLE" in str(exc).upper() or "NOT_FOUND" in str(exc).upper())

    async def _run(self, prompt: str, schema):
        last_error = None
        models_to_try = [self.model, *self.fallback_models]
        for model_name in models_to_try:
            max_attempts = 3
            for attempt in range(1, max_attempts + 1):
                try:
                    logger.info("Gemini generate_content attempt: model=%s attempt=%d", model_name, attempt)
                    response = await asyncio.to_thread(self._generate, prompt, schema, model_name)
                    if not response.text:
                        raise RuntimeError("Gemini returned an empty response")
                    return schema.model_validate_json(response.text)
                except Exception as exc:
                    last_error = exc
                    status = self._extract_status_code(exc)
                    logger.error(
                        "Gemini error (model=%s) status=%s message=%s repr=%s",
                        model_name,
                        status,
                        str(exc),
                        repr(exc),
                    )

                    if not self._should_fallback(exc):
                        logger.debug("Not falling back after non-retryable error for model=%s: %s", model_name, repr(exc))
                        break

                    should_retry = status in {429, 500, 502, 503}
                    if attempt < max_attempts and should_retry:
                        backoff = 2 ** (attempt - 1)
                        logger.info("Transient error for model=%s, retrying after %s seconds (attempt %d/%d)", model_name, backoff, attempt + 1, max_attempts)
                        await asyncio.sleep(backoff)
                        continue

                    logger.info("Giving up on model=%s after attempt %d due to error", model_name, attempt)
                    break
            logger.info("Falling back from model=%s to next model", model_name)
        logger.critical("All Gemini model attempts failed. Tried models=%s. Last error: %s", models_to_try, repr(last_error))
        raise RuntimeError("Gemini request failed") from last_error

    async def summarize_paper(self, title: str, abstract: str) -> PaperSummary:
        if not abstract:
            raise ValueError("This paper does not contain an abstract to summarize.")
        prompt = f"""You are a medical literature analysis assistant. Analyze ONLY the title and abstract below. Never invent details. For every unavailable field, write 'Not reported in the provided abstract'. Do not infer a sample size, intervention, comparator, statistical result, or clinical recommendation that is not supported by the abstract. Distinguish reported findings from interpretation. This is research assistance, not diagnosis or treatment.

Return a structured evidence extraction covering study type, setting, population, sample size, intervention/exposure, comparator, outcomes, research question, key findings, limitations, clinical relevance, evidence caveats, and uncertainty.

TITLE:\n{title}\n\nABSTRACT:\n{abstract}"""
        return await self._run(prompt, PaperSummary)

    async def patient_explanation(self, title: str, abstract: str) -> PatientExplanation:
        if not abstract:
            raise ValueError("This paper does not contain an abstract to explain.")
        prompt = f"""Rewrite the following research abstract into accurate patient-friendly language. Use ONLY information supported by the abstract. Do not give medical advice, treatment recommendations, or imply causation when the study design does not establish it. Explain important technical terms briefly. Clearly state what the study does not show.

TITLE:\n{title}\n\nABSTRACT:\n{abstract}"""
        return await self._run(prompt, PatientExplanation)

    async def compare_papers(self, papers: list[dict]) -> PaperComparison:
        blocks = []
        for i, p in enumerate(papers, 1):
            blocks.append(f"PAPER {i} | PMID {p['pmid']}\nTITLE: {p['title']}\nABSTRACT: {p.get('abstract') or 'No abstract available.'}")
        prompt = """Compare ONLY the provided PubMed abstracts. Never invent missing data. For every unavailable comparison point, explicitly state that it is not reported. Do not infer that different results are contradictory unless the abstracts support that conclusion. Distinguish direct evidence from interpretation. Do not provide medical advice.\n\n""" + "\n\n".join(blocks)
        return await self._run(prompt, PaperComparison)

    async def answer_workspace_question(self, question: str, context_chunks: list[dict]) -> dict:
        if not context_chunks:
            raise ValueError("No evidence was retrieved from the workspace.")
        context = "\n\n".join(
            f"SOURCE {i}: PMID {c['pmid']}\nTITLE: {c['title']}\nEXCERPT: {c['excerpt']}"
            for i, c in enumerate(context_chunks, 1)
        )
        prompt = f"""You are an evidence-grounded medical literature research assistant.
Answer the user's research question using ONLY the retrieved source excerpts below.
Do not use outside knowledge. Do not diagnose, prescribe, or provide treatment advice.
If the excerpts do not contain enough evidence to answer, say so explicitly and set
insufficient_evidence to true. Never invent study results or citations.

Every substantive claim must be traceable to one or more PMIDs in the sources.
Use PMIDs in the source list rather than inventing references.

Return:
- answer: concise synthesis grounded in the excerpts
- evidence_strength: one of "Strong", "Moderate", "Limited", "Insufficient"
- uncertainty: what remains unknown or cannot be concluded
- sources: only sources that actually support the answer, each with a short excerpt
- insufficient_evidence: boolean

USER QUESTION:
{question}

RETRIEVED SOURCES:
{context}"""
        from app.schemas.workspace import WorkspaceAnswer
        result = await self._run(prompt, WorkspaceAnswer)
        return result.model_dump()

# The report method is intentionally kept in the same AI service so all model
# calls share retry/error handling and the same Gemini configuration.
async def _report_method(self, research_question: str, papers: list[dict]):
    from app.schemas.report import LiteratureReviewReport
    if not papers:
        raise ValueError("No papers were supplied for the literature review.")
    blocks = []
    for i, p in enumerate(papers, 1):
        blocks.append(
            f"STUDY {i} | PMID {p['pmid']}\nTITLE: {p['title']}\nABSTRACT: {p.get('abstract') or 'No abstract available.'}"
        )
    prompt = f"""You are a medical literature synthesis assistant. Build a structured literature review using ONLY the supplied PubMed titles and abstracts. Do not use outside knowledge. Do not invent sample sizes, methods, outcomes, statistical results, or limitations. If a field is not reported, say 'Not reported in the provided abstract'. Distinguish what the abstracts directly report from synthesis. Do not provide diagnosis or treatment advice.\n\nResearch question:\n{research_question}\n\nFor each included study, extract study design, population, sample size, intervention/exposure, comparator, outcomes, key findings, and limitations. Then synthesize areas of agreement, disagreement, evidence gaps, review limitations, and a cautious conclusion. Include only PMIDs actually supplied.\n\nSUPPLIED STUDIES:\n""" + "\n\n".join(blocks)
    return await self._run(prompt, LiteratureReviewReport)

GeminiService.generate_literature_review = _report_method
