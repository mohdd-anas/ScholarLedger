"""OpenAlex API client."""

import httpx
import structlog

from app.config import get_settings

logger = structlog.get_logger()

_TYPE_MAP = {
    "journal-article": "journal-article",
    "proceedings-article": "conference-paper",
    "book-chapter": "book-chapter",
    "book": "book",
    "dissertation": "thesis",
    "posted-content": "preprint",
}


def _base_params() -> dict:
    """Build common OpenAlex query params (polite pool email & optional API key)."""
    settings = get_settings()
    params: dict = {}
    if settings.OPENALEX_EMAIL:
        params["mailto"] = settings.OPENALEX_EMAIL
    if settings.OPENALEX_API_KEY:
        params["api_key"] = settings.OPENALEX_API_KEY
    return params


def _parse_openalex_work(work: dict) -> dict | None:
    """Normalize a single OpenAlex work JSON object into an internal work dict."""
    title = (work.get("title") or "").strip()
    if not title:
        return None

    doi = work.get("doi") or ""
    if doi:
        doi = doi.replace("https://doi.org/", "").replace("http://dx.doi.org/", "").lower().strip()

    year = work.get("publication_year")

    venue = ""
    primary_location = work.get("primary_location") or {}
    source_obj = primary_location.get("source") or {}
    if source_obj:
        venue = source_obj.get("display_name") or ""

    author_names = []
    for authorship in work.get("authorships") or []:
        author_obj = authorship.get("author") or {}
        display_name = author_obj.get("display_name")
        if display_name:
            author_names.append(display_name)
    authors = "; ".join(author_names)

    pub_type = _TYPE_MAP.get(work.get("type") or "other", "other")

    return {
        "title": title,
        "doi": doi or None,
        "year": year,
        "venue": venue,
        "authors": authors,
        "type": pub_type,
        "source": "openalex",
        "openalex_id": work.get("id", ""),
    }


async def fetch_works_by_orcid(orcid_id: str) -> list[dict]:
    """Fetch works from OpenAlex for an author identified by ORCID."""
    settings = get_settings()
    base = settings.OPENALEX_API_BASE

    params = {"filter": f"orcid:{orcid_id}", **_base_params()}

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(f"{base}/authors", params=params)
        resp.raise_for_status()
        authors_data = resp.json()

        results = authors_data.get("results", [])
        if not results:
            logger.info("openalex_no_author", orcid_id=orcid_id)
            return []

        author_id = results[0].get("id", "")

        works_params = {
            "filter": f"author.id:{author_id}",
            "per_page": 200,
            "sort": "publication_year:desc",
            **_base_params(),
        }

        resp = await client.get(f"{base}/works", params=works_params)
        resp.raise_for_status()
        works_data = resp.json()

    works = [
        parsed
        for work in works_data.get("results", [])
        if (parsed := _parse_openalex_work(work)) is not None
    ]
    logger.info("openalex_fetch_complete", orcid_id=orcid_id, works_count=len(works))
    return works


async def search_works(query: str, per_page: int = 20) -> list[dict]:
    """Search OpenAlex works by free-text query (title, author, or topic)."""
    if not query.strip():
        return []
    settings = get_settings()
    base = settings.OPENALEX_API_BASE
    params = {
        "search": query.strip(),
        "per_page": min(max(per_page, 1), 50),
        **_base_params(),
    }

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(f"{base}/works", params=params)
        resp.raise_for_status()
        data = resp.json()

    works = [
        parsed
        for work in data.get("results", [])
        if (parsed := _parse_openalex_work(work)) is not None
    ]
    logger.info("openalex_search_complete", query=query, works_count=len(works))
    return works


async def search_works_by_author(author_name: str, per_page: int = 20) -> list[dict]:
    """Search OpenAlex works authored by someone matching author_name."""
    if not author_name.strip():
        return []
    settings = get_settings()
    base = settings.OPENALEX_API_BASE

    async with httpx.AsyncClient(timeout=30) as client:
        author_resp = await client.get(
            f"{base}/authors",
            params={"search": author_name.strip(), "per_page": 3, **_base_params()},
        )
        author_resp.raise_for_status()
        authors = author_resp.json().get("results", [])
        if not authors:
            logger.info("openalex_author_not_found", author_name=author_name)
            return []

        author_ids = [a["id"].replace("https://openalex.org/", "") for a in authors if a.get("id")]
        if not author_ids:
            return []

        works_resp = await client.get(
            f"{base}/works",
            params={
                "filter": f"author.id:{'|'.join(author_ids)}",
                "per_page": min(max(per_page, 1), 50),
                "sort": "publication_year:desc",
                **_base_params(),
            },
        )
        works_resp.raise_for_status()
        data = works_resp.json()

    works = [
        parsed
        for work in data.get("results", [])
        if (parsed := _parse_openalex_work(work)) is not None
    ]
    logger.info("openalex_author_search_complete", author_name=author_name, works_count=len(works))
    return works


async def fetch_work_by_doi(doi: str) -> dict | None:
    """Fetch a single work from OpenAlex by DOI."""
    clean_doi = doi.strip().lower()
    if clean_doi.startswith("https://doi.org/"):
        clean_doi = clean_doi.replace("https://doi.org/", "")
    if not clean_doi:
        return None

    settings = get_settings()
    base = settings.OPENALEX_API_BASE
    params = _base_params()

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(f"{base}/works/https://doi.org/{clean_doi}", params=params)
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        return _parse_openalex_work(resp.json())
