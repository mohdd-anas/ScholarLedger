"""ORCID public API client."""

import contextlib

import httpx
import structlog

from app.config import get_settings

logger = structlog.get_logger()


async def fetch_works(orcid_id: str) -> list[dict]:
    """Fetch works for an ORCID iD from the ORCID public API.

    Returns a list of work dicts with keys: title, doi, year, venue, authors, type.
    """
    settings = get_settings()
    url = f"{settings.ORCID_API_BASE}/{orcid_id}/works"

    headers = {"Accept": "application/json"}
    if settings.ORCID_ACCESS_TOKEN:
        headers["Authorization"] = f"Bearer {settings.ORCID_ACCESS_TOKEN}"

    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()

    works = []
    for group in data.get("group", []):
        summary_list = group.get("work-summary", [])
        if not summary_list:
            continue
        summary = summary_list[0]  # Take the preferred source

        title_obj = summary.get("title", {})
        title = ""
        if title_obj and title_obj.get("title"):
            title = title_obj["title"].get("value", "")

        # Extract DOI from external IDs
        doi = None
        for ext_id in summary.get("external-ids", {}).get("external-id", []):
            if ext_id.get("external-id-type") == "doi":
                doi = ext_id.get("external-id-value", "").lower()
                break

        # Year
        pub_date = summary.get("publication-date", {})
        year = None
        if pub_date and pub_date.get("year"):
            with contextlib.suppress(ValueError, TypeError):
                year = int(pub_date["year"].get("value", 0))

        # Venue
        venue = ""
        journal = summary.get("journal-title")
        if journal:
            venue = journal.get("value", "")

        # Type mapping
        work_type = summary.get("type", "other")
        type_map = {
            "journal-article": "journal-article",
            "conference-paper": "conference-paper",
            "book-chapter": "book-chapter",
            "book": "book",
            "dissertation": "thesis",
            "preprint": "preprint",
        }
        pub_type = type_map.get(work_type, "other")

        if title:
            works.append({
                "title": title,
                "doi": doi,
                "year": year,
                "venue": venue,
                "authors": "",  # ORCID works endpoint doesn't include full author lists
                "type": pub_type,
                "source": "orcid",
            })

    logger.info("orcid_fetch_complete", orcid_id=orcid_id, works_count=len(works))
    return works
