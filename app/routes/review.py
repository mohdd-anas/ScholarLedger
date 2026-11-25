"""Match review queue routes."""

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session, joinedload

from app.auth.dependencies import require_role
from app.database import get_db
from app.main import templates
from app.models.faculty import Faculty, FacultyRole
from app.models.match_decision import MatchDecision, MatchVerdict
from app.models.publication import Publication, PublicationStatus

router = APIRouter(prefix="/review", tags=["review"])


def _flash(request: Request, category: str, message: str):
    if "flash_messages" not in request.session:
        request.session["flash_messages"] = []
    request.session["flash_messages"].append([category, message])


def _get_flashes(request: Request) -> list:
    return request.session.pop("flash_messages", [])


@router.get("", response_class=HTMLResponse)
async def review_queue(
    request: Request,
    db: Session = Depends(get_db),
    user: Faculty = Depends(require_role(FacultyRole.ADMIN)),
    filter_status: str = "submitted",
):
    """Show publications pending review."""
    query = db.query(Publication).options(joinedload(Publication.owner))

    if filter_status == "submitted":
        query = query.filter(Publication.status == PublicationStatus.SUBMITTED)
    elif filter_status == "all":
        pass  # Show all
    else:
        query = query.filter(Publication.status == filter_status)

    publications = query.order_by(Publication.created_at.desc()).all()

    # Get pending match decisions
    pending_decisions = (
        db.query(MatchDecision)
        .filter(MatchDecision.decision == MatchVerdict.PENDING)
        .all()
    )

    return templates.TemplateResponse(
        request,
        "review/queue.html",
        {
            "user": user,
            "publications": publications,
            "pending_decisions": pending_decisions,
            "filter_status": filter_status,
            "flash_messages": _get_flashes(request),
        },
    )


@router.post("/{pub_id}/verify")
async def verify_publication(
    pub_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user: Faculty = Depends(require_role(FacultyRole.ADMIN)),
):
    """Verify (approve) a publication."""
    pub = db.get(Publication, pub_id)
    if not pub:
        raise HTTPException(status_code=404, detail="Publication not found")

    pub.status = PublicationStatus.VERIFIED
    db.commit()
    _flash(request, "success", f"Publication '{pub.title[:50]}...' verified.")
    return RedirectResponse(url="/review", status_code=302)


@router.post("/{pub_id}/reject")
async def reject_publication(
    pub_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user: Faculty = Depends(require_role(FacultyRole.ADMIN)),
):
    """Reject a publication."""
    pub = db.get(Publication, pub_id)
    if not pub:
        raise HTTPException(status_code=404, detail="Publication not found")

    pub.status = PublicationStatus.REJECTED
    db.commit()
    _flash(request, "warning", f"Publication '{pub.title[:50]}...' rejected.")
    return RedirectResponse(url="/review", status_code=302)


@router.post("/decision/{decision_id}/accept")
async def accept_match(
    decision_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user: Faculty = Depends(require_role(FacultyRole.ADMIN)),
):
    """Accept a match decision."""
    decision = db.get(MatchDecision, decision_id)
    if not decision:
        raise HTTPException(status_code=404, detail="Match decision not found")

    decision.decision = MatchVerdict.ACCEPTED
    decision.reviewer = user.email
    decision.decided_at = datetime.now(UTC)
    db.commit()
    _flash(request, "success", "Match accepted.")
    return RedirectResponse(url="/review", status_code=302)


@router.post("/decision/{decision_id}/reject")
async def reject_match(
    decision_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user: Faculty = Depends(require_role(FacultyRole.ADMIN)),
):
    """Reject a match decision."""
    decision = db.get(MatchDecision, decision_id)
    if not decision:
        raise HTTPException(status_code=404, detail="Match decision not found")

    decision.decision = MatchVerdict.REJECTED
    decision.reviewer = user.email
    decision.decided_at = datetime.now(UTC)
    db.commit()
    _flash(request, "warning", "Match rejected.")
    return RedirectResponse(url="/review", status_code=302)
