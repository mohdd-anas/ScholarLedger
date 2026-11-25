"""Deduplication logic for publications."""

import structlog

from app.services.matching import normalize_doi, normalize_title

logger = structlog.get_logger()


def deduplicate_works(works: list[dict]) -> list[dict]:
    """Remove duplicate works from a list.

    Deduplication order:
    1. Exact DOI match
    2. Normalized title match

    When duplicates are found, prefer the record with more metadata.
    """
    seen_dois: dict[str, int] = {}
    seen_titles: dict[str, int] = {}
    unique_works: list[dict] = []
    duplicates_removed = 0

    for work in works:
        doi = normalize_doi(work.get("doi"))
        title = normalize_title(work.get("title", ""))

        # Check DOI duplicate
        if doi and doi in seen_dois:
            duplicates_removed += 1
            # Merge: keep the one with more data
            existing_idx = seen_dois[doi]
            existing = unique_works[existing_idx]
            unique_works[existing_idx] = _merge_records(existing, work)
            continue

        # Check title duplicate
        if title and title in seen_titles:
            duplicates_removed += 1
            existing_idx = seen_titles[title]
            existing = unique_works[existing_idx]
            unique_works[existing_idx] = _merge_records(existing, work)
            continue

        # New unique work
        idx = len(unique_works)
        unique_works.append(work)
        if doi:
            seen_dois[doi] = idx
        if title:
            seen_titles[title] = idx

    logger.info(
        "dedup_complete",
        input_count=len(works),
        output_count=len(unique_works),
        duplicates_removed=duplicates_removed,
    )
    return unique_works


def _merge_records(existing: dict, incoming: dict) -> dict:
    """Merge two publication records, preferring non-empty fields."""
    merged = dict(existing)
    for key, value in incoming.items():
        if value and not merged.get(key):
            merged[key] = value
    return merged
