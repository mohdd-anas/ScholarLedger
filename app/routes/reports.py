"""Reports and CSV export routes."""

import csv
import io
from collections import defaultdict

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, StreamingResponse
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.database import get_db
from app.main import templates
from app.models.faculty import Faculty
from app.models.publication import Publication
from app.models.sync_run import SyncRun, SyncStatus

router = APIRouter(prefix="/reports", tags=["reports"])


def _get_flashes(request: Request) -> list:
    return request.session.pop("flash_messages", [])


@router.get("", response_class=HTMLResponse)
async def reports_dashboard(
    request: Request,
    db: Session = Depends(get_db),
    user: Faculty = Depends(get_current_user),
    department: str = "",
    year: str = "",
):
    """Department-wise reports: counts by year, type, department."""
    query = db.query(Publication)
    if department:
        query = query.filter(Publication.department == department)
    if year:
        query = query.filter(Publication.year == int(year))

    publications = query.all()

    # Aggregate statistics
    total = len(publications)
    by_status = defaultdict(int)
    by_type = defaultdict(int)
    by_department = defaultdict(int)
    by_year = defaultdict(int)
    by_source = defaultdict(int)

    for pub in publications:
        by_status[pub.status.value] += 1
        by_type[pub.pub_type.value] += 1
        if pub.department:
            by_department[pub.department] += 1
        if pub.year:
            by_year[pub.year] += 1
        by_source[pub.source.value] += 1

    # Available filter values
    departments = [
        r[0] for r in db.query(Publication.department).distinct().all() if r[0]
    ]
    years = sorted(
        [r[0] for r in db.query(Publication.year).distinct().all() if r[0]],
        reverse=True,
    )

    # Sync run stats
    sync_runs = db.query(SyncRun).order_by(SyncRun.started_at.desc()).limit(10).all()
    total_syncs = db.query(SyncRun).count()
    successful_syncs = db.query(SyncRun).filter(SyncRun.status == SyncStatus.SUCCESS).count()
    sync_reliability = (successful_syncs / total_syncs * 100) if total_syncs > 0 else 0

    # Coverage metric: papers per source
    source_coverage = {}
    for source_name, count in by_source.items():
        source_coverage[source_name] = {
            "count": count,
            "percentage": (count / total * 100) if total > 0 else 0,
        }

    return templates.TemplateResponse(
        request,
        "reports/department.html",
        {
            "user": user,
            "total": total,
            "by_status": dict(by_status),
            "by_type": dict(by_type),
            "by_department": dict(by_department),
            "by_year": dict(by_year),
            "by_source": dict(by_source),
            "source_coverage": source_coverage,
            "departments": departments,
            "years": years,
            "department": department,
            "year": year,
            "sync_runs": sync_runs,
            "sync_reliability": sync_reliability,
            "flash_messages": _get_flashes(request),
        },
    )


@router.get("/export/csv")
async def export_csv(
    request: Request,
    db: Session = Depends(get_db),
    user: Faculty = Depends(get_current_user),
    department: str = "",
    year: str = "",
):
    """Export publications as CSV."""
    query = db.query(Publication).join(Faculty, Publication.owner_faculty_id == Faculty.id)
    if department:
        query = query.filter(Publication.department == department)
    if year:
        query = query.filter(Publication.year == int(year))

    publications = query.all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "ID", "Title", "Authors", "Venue", "Year", "DOI",
        "Type", "Department", "Status", "Source", "Owner", "Confidence",
    ])

    for pub in publications:
        owner = db.get(Faculty, pub.owner_faculty_id)
        writer.writerow([
            pub.id, pub.title, pub.authors, pub.venue or "", pub.year or "",
            pub.doi or "", pub.pub_type.value, pub.department or "",
            pub.status.value, pub.source.value,
            owner.name if owner else "", pub.match_confidence or "",
        ])

    output.seek(0)
    return StreamingResponse(
        io.BytesIO(output.getvalue().encode("utf-8")),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=publications_report.csv"},
    )
