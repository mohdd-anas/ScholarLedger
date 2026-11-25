"""Sync management routes."""

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.auth.dependencies import require_role
from app.database import get_db
from app.main import templates
from app.models.faculty import Faculty, FacultyRole
from app.models.sync_run import SyncRun
from app.services.sync_service import run_sync

router = APIRouter(prefix="/sync", tags=["sync"])


def _flash(request: Request, category: str, message: str):
    if "flash_messages" not in request.session:
        request.session["flash_messages"] = []
    request.session["flash_messages"].append([category, message])


def _get_flashes(request: Request) -> list:
    return request.session.pop("flash_messages", [])


@router.get("", response_class=HTMLResponse)
async def sync_dashboard(
    request: Request,
    db: Session = Depends(get_db),
    user: Faculty = Depends(require_role(FacultyRole.ADMIN)),
):
    """Show sync run history and manual sync triggers."""
    runs = db.query(SyncRun).order_by(SyncRun.started_at.desc()).limit(50).all()
    return templates.TemplateResponse(
        request,
        "sync/dashboard.html",
        {
            "user": user,
            "runs": runs,
            "flash_messages": _get_flashes(request),
        },
    )


@router.post("/run")
async def trigger_sync(
    request: Request,
    source: str = Form("openalex"),
    db: Session = Depends(get_db),
    user: Faculty = Depends(require_role(FacultyRole.ADMIN)),
):
    """Trigger an ingestion sync run from the Admin UI."""
    allowed = {"orcid", "openalex", "crossref", "all"}
    if source not in allowed:
        _flash(request, "error", f"Invalid sync source: {source}")
        return RedirectResponse(url="/sync", status_code=302)

    runs = await run_sync(db, source=source)
    total_fetched = sum(r.records_fetched for r in runs)
    total_merged = sum(r.records_merged for r in runs)
    total_queued = sum(r.records_queued for r in runs)
    _flash(
        request,
        "success",
        f"Sync ({source}) completed: {total_fetched} fetched, "
        f"{total_merged} merged, {total_queued} queued.",
    )
    return RedirectResponse(url="/sync", status_code=302)
