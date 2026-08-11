def format_citations(paper: dict) -> dict:
    authors = paper.get("authors") or []
    if not authors:
        author_text = "Unknown author"
        vancouver_authors = "Unknown author"
    else:
        first = authors[0]
        author_text = first if len(authors) == 1 else f"{first}, et al."
        vancouver_authors = ", ".join(authors[:6]) + (", et al." if len(authors) > 6 else "")

    title = paper.get("title") or "Untitled"
    journal = paper.get("journal") or "Journal unavailable"
    date = paper.get("publication_date") or "n.d."
    doi = paper.get("doi")
    doi_text = f" https://doi.org/{doi}" if doi else ""

    apa = f"{author_text} ({date}). {title}. {journal}. https://pubmed.ncbi.nlm.nih.gov/{paper['pmid']}/{doi_text}".strip()
    mla = f"{author_text}. \"{title}.\" {journal}, {date}. PubMed, PMID {paper['pmid']}." 
    vancouver = f"{vancouver_authors}. {title}. {journal}. {date}. PMID: {paper['pmid']}" + (f". doi:{doi}." if doi else ".")
    return {"apa": apa, "mla": mla, "vancouver": vancouver}
