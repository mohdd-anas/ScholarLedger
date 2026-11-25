"""Crossref API client."""

import httpx
import structlog

from app.config import get_settings

logger = structlog.get_logger()


async def fetch_works_by_orcid(orcid_id: str) -> list[dict]:
    """Fetch works from Crossref for an author identified by ORCID.

    Returns a list of work dicts with keys: title, doi, year, venue, authors, type.
    """
    settings = get_settings()
    base = settings.CROSSREF_API_BASE

    params = {
        "filter": f"orcid:{orcid_id}",
        "rows": 200,
        "sort": "published",
        "order": "desc",
    }
    headers = {}
    if settings.OPENALEX_EMAIL:
        headers["User-Agent"] = f"PB1-PublicationTracker/0.1.0 (mailto:{settings.OPENALEX_EMAIL})"
    if settings.CROSSREF_PLUS_API_TOKEN:
        headers["Crossref-Plus-API-Token"] = f"Bearer {settings.CROSSREF_PLUS_API_TOKEN}"

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(f"{base}/works", params=params, headers=headers)
        resp.raise_for_status()
        data = resp.json()

    works = []
    for item in data.get("message", {}).get("items", []):
        titles = item.get("title", [])
        title = titles[0] if titles else ""
        if not title:
            continue

        doi = item.get("DOI", "").lower() if item.get("DOI") else None

        # Year from published-print or published-online
        year = None
        for date_field in ["published-print", "published-online", "created"]:
            date_parts = item.get(date_field, {}).get("date-parts", [[]])
            if date_parts and date_parts[0]:
                try:
                    year = int(date_parts[0][0])
                    break
                except (ValueError, TypeError, IndexError):
                    pass

        # Venue
        containers = item.get("container-title", [])
        venue = containers[0] if containers else ""

        # Authors
        author_names = []
        for author in item.get("author", []):
            given = author.get("given", "")
            family = author.get("family", "")
            if family:
                name = f"{family}, {given[0]}." if given else family
                author_names.append(name)
        authors = "; ".join(author_names)

        # Type
        cr_type = item.get("type", "other")
        type_map = {
            "journal-article": "journal-article",
            "proceedings-article": "conference-paper",
            "book-chapter": "book-chapter",
            "book": "book",
            "dissertation": "thesis",
            "posted-content": "preprint",
        }
        pub_type = type_map.get(cr_type, "other")

        works.append({
            "title": title,
            "doi": doi,
            "year": year,
            "venue": venue,
            "authors": authors,
            "type": pub_type,
            "source": "crossref",
        })

    logger.info("crossref_fetch_complete", orcid_id=orcid_id, works_count=len(works))
    return works
