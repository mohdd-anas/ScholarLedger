"""Parse faculty-uploaded BibTeX/CSV exports (e.g., Google Scholar)."""

import contextlib
import csv
import io
import re

import structlog

logger = structlog.get_logger()


def parse_bibtex(content: str) -> list[dict]:
    """Parse BibTeX content into a list of publication dicts.

    Handles common BibTeX exported from Google Scholar.
    """
    works = []
    # Simple regex-based BibTeX parser (handles Scholar exports)
    entries = re.findall(r"@(\w+)\{([^,]*),(.*?)\n\}", content, re.DOTALL)

    for entry_type, _key, body in entries:
        fields = {}
        for match in re.finditer(r"(\w+)\s*=\s*\{(.*?)\}", body, re.DOTALL):
            fields[match.group(1).lower()] = match.group(2).strip()

        title = fields.get("title", "")
        if not title:
            continue

        authors = fields.get("author", "").replace(" and ", "; ")
        year = None
        if fields.get("year"):
            with contextlib.suppress(ValueError):
                year = int(fields["year"])

        venue = fields.get("journal") or fields.get("booktitle") or ""
        doi = fields.get("doi")
        if doi:
            doi = doi.lower()

        # Map BibTeX entry types
        type_map = {
            "article": "journal-article",
            "inproceedings": "conference-paper",
            "inbook": "book-chapter",
            "incollection": "book-chapter",
            "book": "book",
            "phdthesis": "thesis",
            "mastersthesis": "thesis",
            "techreport": "preprint",
            "misc": "other",
        }
        pub_type = type_map.get(entry_type.lower(), "other")

        works.append({
            "title": title,
            "doi": doi,
            "year": year,
            "venue": venue,
            "authors": authors,
            "type": pub_type,
            "source": "scholar_export",
        })

    logger.info("bibtex_parse_complete", entries_found=len(works))
    return works


def parse_csv_export(content: str) -> list[dict]:
    """Parse CSV export (e.g., from Google Scholar) into publication dicts.

    Expected columns: Title, Authors, Year, Venue/Journal, DOI (optional).
    """
    works = []
    reader = csv.DictReader(io.StringIO(content))

    # Normalize header names
    for row in reader:
        # Try common column name variations
        normalized = {k.lower().strip(): v for k, v in row.items() if k}

        title = (
            normalized.get("title")
            or normalized.get("article title")
            or normalized.get("paper title")
            or ""
        ).strip()
        if not title:
            continue

        authors = (
            normalized.get("authors")
            or normalized.get("author")
            or ""
        ).strip()

        year = None
        year_str = normalized.get("year") or normalized.get("publication year") or ""
        if year_str.strip():
            with contextlib.suppress(ValueError):
                year = int(year_str.strip())

        venue = (
            normalized.get("venue")
            or normalized.get("journal")
            or normalized.get("source")
            or normalized.get("publication")
            or ""
        ).strip()

        doi = (normalized.get("doi") or "").strip().lower() or None

        works.append({
            "title": title,
            "doi": doi,
            "year": year,
            "venue": venue,
            "authors": authors,
            "type": "other",
            "source": "scholar_export",
        })

    logger.info("csv_parse_complete", entries_found=len(works))
    return works
