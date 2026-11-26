"""Orchestrates publication ingestion, matching, deduplication, and sync_run tracking."""

from datetime import UTC, datetime

import structlog
from sqlalchemy.orm import Session

from app.models.faculty import Faculty
from app.models.match_decision import MatchDecision, MatchMethod, MatchVerdict
from app.models.publication import (
    Publication,
    PublicationSource,
    PublicationStatus,
    PublicationType,
)
from app.models.sync_run import SyncRun, SyncStatus
from app.services.coauthor_service import attribute_coauthor, attributed_to_faculty_filter
from app.services.dedup import deduplicate_works
from app.services.ingestion import crossref, openalex, orcid
from app.services.matching import find_best_match, normalize_doi

logger = structlog.get_logger()


def _parse_pub_type(raw_type: str | None) -> PublicationType:
    """Safely map string type to PublicationType enum."""
    if not raw_type:
        return PublicationType.OTHER
    for pt in PublicationType:
        if pt.value == raw_type:
            return pt
    return PublicationType.OTHER


def _parse_source(raw_source: str | None) -> PublicationSource:
    """Safely map string source to PublicationSource enum."""
    if not raw_source:
        return PublicationSource.MANUAL
    for ps in PublicationSource:
        if ps.value == raw_source:
            return ps
    return PublicationSource.MANUAL


def ingest_works_for_faculty(
    db: Session,
    faculty: Faculty,
    works: list[dict],
    source_name: str,
) -> tuple[int, int, int]:
    """Deduplicate, match, and persist works for a faculty member.

    Returns (fetched, merged, queued).
    """
    fetched = len(works)
    deduped = deduplicate_works(works)
    existing = (
        db.query(Publication)
        .filter(attributed_to_faculty_filter(faculty.id))
        .all()
    )

    merged = 0
    queued = 0

    for work in deduped:
        method, score, matched_id = find_best_match(work, existing)
        if matched_id is not None and method == "doi":
            # Exact DOI match already stored for this faculty member
            merged += 1
            continue

        if matched_id is not None and score >= 0.85:
            merged += 1
            continue

        # Create new publication record or attribute co-author on existing DOI
        doi = normalize_doi(work.get("doi"))
        if doi:
            existing_global = (
                db.query(Publication).filter(Publication.doi == doi).first()
            )
            if existing_global is not None:
                # Shared publication (e.g. co-author at same institution)
                if attribute_coauthor(existing_global, faculty):
                    db.flush()
                    existing.append(existing_global)
                merged += 1
                continue

        needs_review = matched_id is not None or score > 0.0
        pub = Publication(
            title=work["title"],
            authors=work.get("authors") or faculty.name,
            venue=work.get("venue") or None,
            year=work.get("year"),
            doi=doi,
            pub_type=_parse_pub_type(work.get("type")),
            department=faculty.department,
            status=PublicationStatus.SUBMITTED if needs_review else PublicationStatus.DRAFT,
            source=_parse_source(work.get("source") or source_name),
            owner_faculty_id=faculty.id,
            match_confidence=score if score > 0 else 1.0,
        )
        db.add(pub)
        db.flush()
        existing.append(pub)

        if needs_review:
            queued += 1
            match_method = (
                MatchMethod.TITLE if method == "title"
                else MatchMethod.NAME if method == "name"
                else MatchMethod.DOI
            )
            db.add(
                MatchDecision(
                    publication_id=pub.id,
                    matched_by=match_method,
                    score=score,
                    decision=MatchVerdict.PENDING,
                )
            )
        else:
            merged += 1

    return fetched, merged, queued


async def run_sync(
    db: Session,
    source: str = "all",
    dry_run: bool = False,
) -> list[SyncRun]:
    """Run ingestion sync for all faculty with an ORCID iD."""
    sources = ["orcid", "openalex", "crossref"] if source == "all" else [source]
    faculty_list = db.query(Faculty).filter(Faculty.orcid_id.isnot(None)).all()
    runs: list[SyncRun] = []

    for src in sources:
        sync_run = SyncRun(source=src, status=SyncStatus.RUNNING)
        if not dry_run:
            db.add(sync_run)
            db.flush()

        total_fetched = 0
        total_merged = 0
        total_queued = 0
        had_error = False

        for fac in faculty_list:
            if not fac.orcid_id:
                continue
            try:
                if src == "orcid":
                    works = await orcid.fetch_works(fac.orcid_id)
                elif src == "openalex":
                    works = await openalex.fetch_works_by_orcid(fac.orcid_id)
                elif src == "crossref":
                    works = await crossref.fetch_works_by_orcid(fac.orcid_id)
                else:
                    works = []

                if dry_run:
                    total_fetched += len(works)
                else:
                    f, m, q = ingest_works_for_faculty(db, fac, works, src)
                    total_fetched += f
                    total_merged += m
                    total_queued += q
            except Exception as exc:
                had_error = True
                logger.error("sync_faculty_failed", source=src, faculty_id=fac.id, error=str(exc))

        sync_run.records_fetched = total_fetched
        sync_run.records_merged = total_merged
        sync_run.records_queued = total_queued
        sync_run.finished_at = datetime.now(UTC)
        sync_run.status = (
            SyncStatus.PARTIAL if had_error and total_fetched > 0
            else SyncStatus.FAILED if had_error
            else SyncStatus.SUCCESS
        )
        if not dry_run:
            db.commit()
        runs.append(sync_run)
        logger.info(
            "sync_run_complete",
            source=src,
            status=sync_run.status.value,
            fetched=total_fetched,
            merged=total_merged,
            queued=total_queued,
        )

    return runs
