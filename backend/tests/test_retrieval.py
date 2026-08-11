from types import SimpleNamespace
from app.services.retrieval_service import retrieve


def paper(pmid, title, abstract):
    return SimpleNamespace(pmid=pmid, title=title, abstract=abstract)


def test_retrieve_prioritizes_relevant_title_and_abstract():
    papers = [
        paper("1", "Hypertension exercise outcomes", "Aerobic exercise reduced systolic blood pressure in adults."),
        paper("2", "Cancer genomics", "Tumor sequencing identified recurrent variants."),
    ]
    results = retrieve("exercise blood pressure", papers)
    assert results
    assert results[0]["pmid"] == "1"
    assert results[0]["retrieval_score"] > 0


def test_retrieve_ignores_papers_without_abstracts():
    papers = [paper("1", "Missing abstract", None)]
    assert retrieve("blood pressure", papers) == []
