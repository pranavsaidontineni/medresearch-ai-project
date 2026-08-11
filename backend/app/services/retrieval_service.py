import math
import re
from collections import Counter
from app.models.paper import Paper

STOPWORDS = {
    "the","and","for","with","that","this","from","into","about","what",
    "which","were","was","are","how","does","did","have","has","their",
    "they","than","then","using","among","study","paper","papers","research",
    "a","an","of","to","in","on","by","is","be","or","as","at","it",
}

def tokenize(text: str) -> list[str]:
    return [x for x in re.findall(r"[a-zA-Z0-9]{3,}", text.lower()) if x not in STOPWORDS]

def _cosine(a: Counter, b: Counter) -> float:
    if not a or not b:
        return 0.0
    common = set(a) & set(b)
    numerator = sum(a[t] * b[t] for t in common)
    denom_a = math.sqrt(sum(v * v for v in a.values()))
    denom_b = math.sqrt(sum(v * v for v in b.values()))
    return numerator / (denom_a * denom_b) if denom_a and denom_b else 0.0

def retrieve(question: str, papers: list[Paper], top_k: int = 10) -> list[dict]:
    """Hybrid deterministic retrieval: term overlap + cosine similarity + title boost.

    This deliberately has no paid vector database dependency. It is a transparent
    baseline that can later be replaced by an embedding index without changing
    the API contract.
    """
    q_tokens = tokenize(question)
    q = Counter(q_tokens)
    docs = []
    document_frequency = Counter()
    for p in papers:
        text = f"{p.title}\n{p.abstract or ''}"
        tokens = tokenize(text)
        counts = Counter(tokens)
        document_frequency.update(set(counts))
        docs.append((p, text, counts))

    n_docs = max(1, len(docs))
    candidates = []
    for p, text, counts in docs:
        if not p.abstract:
            continue
        overlap = sum(min(q[t], counts[t]) for t in q)
        coverage = sum(1 for t in q if t in counts) / max(1, len(q))
        title_tokens = Counter(tokenize(p.title))
        title_overlap = sum(min(q[t], title_tokens[t]) for t in q)
        # Light TF-IDF weighting keeps common medical terms from dominating.
        weighted_q = Counter({t: q[t] * math.log((n_docs + 1) / (document_frequency[t] + 1)) + 1 for t in q})
        weighted_d = Counter({t: counts[t] * math.log((n_docs + 1) / (document_frequency[t] + 1)) + 1 for t in counts})
        cosine = _cosine(weighted_q, weighted_d)
        score = 0.45 * cosine + 0.30 * coverage + 0.15 * min(1.0, overlap / max(1, len(q_tokens))) + 0.10 * min(1.0, title_overlap)
        if score > 0:
            candidates.append((score, p, text))

    candidates.sort(key=lambda x: x[0], reverse=True)
    selected = []
    for score, p, text in candidates[:top_k]:
        abstract = p.abstract or ""
        # Keep the full abstract when it is short; otherwise choose a compact evidence excerpt.
        excerpt = abstract if len(abstract) <= 1800 else abstract[:1800].rsplit(" ", 1)[0] + "…"
        selected.append({"pmid": p.pmid, "title": p.title, "excerpt": excerpt, "retrieval_score": round(score, 4)})
    return selected
