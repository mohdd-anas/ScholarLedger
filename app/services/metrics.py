"""Application metrics computation."""

from sqlalchemy.orm import Session

from app.models.match_decision import MatchDecision, MatchVerdict
from app.models.publication import Publication, PublicationSource
from app.models.sync_run import SyncRun, SyncStatus


def compute_coverage(db: Session) -> dict:
    """Compute coverage: papers found per single source vs all combined."""
    total = db.query(Publication).count()
    if total == 0:
        return {"total": 0, "by_source": {}}

    by_source = {}
    for source in PublicationSource:
        count = db.query(Publication).filter(Publication.source == source).count()
        by_source[source.value] = {
            "count": count,
            "percentage": (count / total) * 100,
        }

    return {"total": total, "by_source": by_source}


def compute_attribution_metrics(db: Session) -> dict:
    """Compute attribution precision/recall against verified publications."""
    verified = db.query(Publication).filter(
        Publication.status == "verified"
    ).all()

    if not verified:
        return {"precision": 0, "recall": 0, "f1": 0}

    # True positives: verified publications with accepted match decisions
    decisions = db.query(MatchDecision).filter(
        MatchDecision.decision == MatchVerdict.ACCEPTED
    ).all()
    matched_pub_ids = {d.publication_id for d in decisions}

    verified_ids = {p.id for p in verified}

    true_positives = len(matched_pub_ids & verified_ids)
    false_positives = len(matched_pub_ids - verified_ids)
    false_negatives = len(verified_ids - matched_pub_ids)

    tp_fp = true_positives + false_positives
    tp_fn = true_positives + false_negatives
    precision = true_positives / tp_fp if tp_fp > 0 else 0
    recall = true_positives / tp_fn if tp_fn > 0 else 0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0

    return {"precision": precision, "recall": recall, "f1": f1}


def compute_duplicate_rate(db: Session) -> float:
    """Compute duplicate rate: ratio of publications sharing a DOI."""
    total = db.query(Publication).count()
    if total == 0:
        return 0.0

    unique_dois = db.query(Publication.doi).filter(
        Publication.doi.isnot(None)
    ).distinct().count()

    pubs_with_doi = db.query(Publication).filter(
        Publication.doi.isnot(None)
    ).count()

    if pubs_with_doi == 0:
        return 0.0

    duplicates = pubs_with_doi - unique_dois
    return duplicates / pubs_with_doi


def compute_sync_reliability(db: Session) -> float:
    """Compute sync reliability: share of sync runs completing without failure."""
    total_runs = db.query(SyncRun).count()
    if total_runs == 0:
        return 0.0

    successful_runs = db.query(SyncRun).filter(
        SyncRun.status == SyncStatus.SUCCESS
    ).count()

    return successful_runs / total_runs
