import xml.etree.ElementTree as ET
import httpx
from app.core.config import get_settings

BASE_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"

class PubMedError(Exception):
    pass

class PubMedService:
    def __init__(self):
        self.settings = get_settings()

    async def _get(self, endpoint: str, params: dict) -> str:
        params = {**params, "tool": "medresearch-ai", "email": self.settings.ncbi_email}
        if self.settings.ncbi_api_key:
            params["api_key"] = self.settings.ncbi_api_key
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                response = await client.get(f"{BASE_URL}/{endpoint}", params=params)
                response.raise_for_status()
                return response.text
        except httpx.HTTPError as exc:
            raise PubMedError("PubMed request failed") from exc

    async def search(self, term: str, limit: int = 10, offset: int = 0) -> tuple[int, list[str]]:
        xml = await self._get("esearch.fcgi", {"db": "pubmed", "term": term, "retmode": "xml", "retmax": limit, "retstart": offset})
        root = ET.fromstring(xml)
        count = int(root.findtext("Count", "0"))
        ids = [node.text for node in root.findall("IdList/Id") if node.text]
        return count, ids

    async def fetch(self, pmids: list[str]) -> list[dict]:
        if not pmids:
            return []
        xml = await self._get("efetch.fcgi", {"db": "pubmed", "id": ",".join(pmids), "retmode": "xml"})
        root = ET.fromstring(xml)
        results = []
        for article in root.findall("PubmedArticle"):
            medline = article.find("MedlineCitation")
            article_data = medline.find("Article") if medline is not None else None
            if article_data is None:
                continue
            pmid = medline.findtext("PMID", "") if medline is not None else ""
            title = "".join(article_data.find("ArticleTitle").itertext()) if article_data.find("ArticleTitle") is not None else "Untitled"
            abstract_parts = []
            abstract = article_data.find("Abstract")
            if abstract is not None:
                for node in abstract.findall("AbstractText"):
                    label = node.attrib.get("Label")
                    text = "".join(node.itertext()).strip()
                    abstract_parts.append(f"{label}: {text}" if label else text)
            authors = []
            author_list = article_data.find("AuthorList")
            if author_list is not None:
               for author in author_list.findall("Author"):
                   collective = author.findtext("CollectiveName")
                   if collective:
                       authors.append(collective)
                   else:
                       last = author.findtext("LastName", "")
                       initials = author.findtext("Initials", "")
                       name = " ".join(x for x in [last, initials] if x).strip()
                       aff = None
                       aff_info = author.find("AffiliationInfo")
                       if aff_info is not None:
                           aff = aff_info.findtext("Affiliation")
                       if name:
                           if aff:
                               authors.append(f"{name} — {aff}")
                           else:
                               authors.append(name)
            journal = article_data.findtext("Journal/Title")
            pub_date = article_data.find("Journal/JournalIssue/PubDate")
            publication_date = ""
            if pub_date is not None:
                publication_date = " ".join("".join(x.itertext()).strip() for x in list(pub_date)).strip()
                publication_date = publication_date or (pub_date.findtext("Year") or pub_date.findtext("MedlineDate") or "")
            doi = None
            for aid in article.findall("PubmedData/ArticleIdList/ArticleId"):
                if aid.attrib.get("IdType") == "doi":
                    doi = aid.text
            results.append({"pmid": pmid, "title": title, "abstract": "\n\n".join(abstract_parts) or None, "journal": journal, "publication_date": publication_date or None, "doi": doi, "authors": authors})
        return results
