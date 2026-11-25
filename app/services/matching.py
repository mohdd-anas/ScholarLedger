"""Publication matching engine: DOI → title similarity → name fallback."""

import re
import unicodedata

from rapidfuzz import fuzz

from app.config import get_settings


def normalize_doi(doi: str | None) -> str | None:
    """Normalize a DOI: lowercase, strip whitespace and URL prefix."""
    if not doi:
        return None
    doi = doi.strip().lower()
    doi = re.sub(r"^https?://(dx\.)?doi\.org/", "", doi)
    return doi


def normalize_title(title: str) -> str:
    """Normalize a title: lowercase, strip accents, remove punctuation and extra whitespace."""
    if not title:
        return ""
    # Remove accents
    title = unicodedata.normalize("NFKD", title)
    title = "".join(c for c in title if not unicodedata.combining(c))
    # Lowercase, strip punctuation
    title = title.lower()
    title = re.sub(r"[^\w\s]", " ", title)
    title = re.sub(r"\s+", " ", title).strip()
    return title


def normalize_name(name: str) -> str:
    """Normalize an author name for comparison."""
    if not name:
        return ""
    name = unicodedata.normalize("NFKD", name)
    name = "".join(c for c in name if not unicodedata.combining(c))
    name = name.lower().strip()
    name = re.sub(r"[^\w\s]", " ", name)
    name = re.sub(r"\s+", " ", name).strip()
    return name


def match_doi(doi1: str | None, doi2: str | None) -> tuple[bool, float]:
    """Check if two DOIs match exactly after normalization.

    Returns (is_match, score).
    """
    d1 = normalize_doi(doi1)
    d2 = normalize_doi(doi2)
    if d1 and d2 and d1 == d2:
        return True, 1.0
    return False, 0.0


def match_title(title1: str, title2: str) -> tuple[bool, float]:
    """Check if two titles match via fuzzy comparison.

    Uses token_sort_ratio which handles word reordering.
    Returns (is_match, score) where score is 0-100.
    """
    settings = get_settings()
    t1 = normalize_title(title1)
    t2 = normalize_title(title2)

    if not t1 or not t2:
        return False, 0.0

    score = fuzz.token_sort_ratio(t1, t2)
    return score >= settings.MATCH_TITLE_THRESHOLD, score


def match_name(name1: str, name2: str) -> tuple[bool, float]:
    """Check if two author names match via fuzzy comparison.

    Returns (is_match, score) where score is 0-100.
    """
    settings = get_settings()
    n1 = normalize_name(name1)
    n2 = normalize_name(name2)

    if not n1 or not n2:
        return False, 0.0

    score = fuzz.token_sort_ratio(n1, n2)
    return score >= settings.MATCH_NAME_THRESHOLD, score


def find_best_match(
    incoming: dict,
    existing_publications: list,
) -> tuple[str, float, int | None]:
    """Find the best match for an incoming work among existing publications.

    Returns (match_method, score, matched_pub_id).
    - match_method: 'doi', 'title', 'name', or 'none'
    - score: 0.0 to 1.0 (normalized)
    - matched_pub_id: ID of matched publication, or None
    """
    incoming_doi = normalize_doi(incoming.get("doi"))
    incoming_title = incoming.get("title", "")

    best_method = "none"
    best_score = 0.0
    best_id = None

    for pub in existing_publications:
        # 1. Try DOI match (highest confidence)
        if incoming_doi and pub.doi:
            is_match, score = match_doi(incoming_doi, pub.doi)
            if is_match:
                return "doi", 1.0, pub.id

        # 2. Try title match
        is_match, score = match_title(incoming_title, pub.title)
        if is_match and score / 100.0 > best_score:
            best_method = "title"
            best_score = score / 100.0
            best_id = pub.id

    # 3. If no match yet, try name fallback (lower threshold)
    if best_method == "none" and incoming.get("authors"):
        for pub in existing_publications:
            is_match, score = match_name(incoming.get("authors", ""), pub.authors)
            if is_match:
                # Also check partial title overlap
                _, title_score = match_title(incoming_title, pub.title)
                if title_score > 50:  # Weak title match + name match
                    combined = (score / 100.0 + title_score / 100.0) / 2
                    if combined > best_score:
                        best_method = "name"
                        best_score = combined
                        best_id = pub.id

    return best_method, best_score, best_id
