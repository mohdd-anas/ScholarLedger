"""Publication CRUD routes with HTMX support."""


from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from sqlalchemy import or_
from sqlalchemy.orm import Session, selectinload

from app.auth.dependencies import get_current_user
from app.database import get_db
from app.main import templates
from app.models.faculty import Faculty, FacultyRole
from app.models.publication import (
    Publication,
    PublicationSource,
    PublicationStatus,
    PublicationType,
)
from app.services.coauthor_service import (
    attribute_coauthor,
    attributed_to_faculty_filter,
    department_publication_filter,
    sync_coauthors,
)
from app.services.ingestion.openalex import (
    fetch_work_by_doi,
    fetch_works_by_orcid,
    search_works,
    search_works_by_author,
)
from app.services.ingestion.scholar_import import parse_bibtex, parse_csv_export
from app.services.matching import normalize_doi
from app.services.proof_service import build_publication_proof_pdf
from app.services.sync_service import ingest_works_for_faculty

router = APIRouter(prefix="/publications", tags=["publications"])


def _flash(request: Request, category: str, message: str):
    if "flash_messages" not in request.session:
        request.session["flash_messages"] = []
    request.session["flash_messages"].append([category, message])


def _get_flashes(request: Request) -> list:
    return request.session.pop("flash_messages", [])


def _can_manage_publication(pub: Publication, user: Faculty) -> bool:
    """Return True if the user owns the publication or is an admin."""
    return user.role == FacultyRole.ADMIN or pub.owner_faculty_id == user.id


def _get_publication_or_404(db: Session, pub_id: int) -> Publication:
    """Fetch a publication with owner and co-authors, or raise 404."""
    pub = (
        db.query(Publication)
        .options(selectinload(Publication.owner), selectinload(Publication.coauthors))
        .filter(Publication.id == pub_id)
        .first()
    )
    if not pub:
        raise HTTPException(status_code=404, detail="Publication not found")
    return pub


@router.get("", response_class=HTMLResponse)
async def list_publications(
    request: Request,
    db: Session = Depends(get_db),
    user: Faculty = Depends(get_current_user),
    search: str = "",
    status_filter: str = "",
    department: str = "",
    page: int = 1,
):
    """List publications with search, filter, and pagination."""
    per_page = 20
    query = db.query(Publication).options(
        selectinload(Publication.owner),
        selectinload(Publication.coauthors),
    )

    # Faculty sees owned and co-authored; admin/viewer sees all
    if user.role == FacultyRole.FACULTY:
        query = query.filter(attributed_to_faculty_filter(user.id))

    if search:
        query = query.filter(
            or_(
                Publication.title.ilike(f"%{search}%"),
                Publication.authors.ilike(f"%{search}%"),
                Publication.doi.ilike(f"%{search}%"),
            )
        )
    if status_filter:
        query = query.filter(Publication.status == status_filter)
    if department:
        query = query.filter(department_publication_filter(department))

    total = query.count()
    publications = (
        query.order_by(Publication.created_at.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
        .all()
    )

    # Get unique departments for filter dropdown
    departments = [
        r[0]
        for r in db.query(Publication.department).distinct().all()
        if r[0]
    ]

    return templates.TemplateResponse(
        request,
        "publications/list.html",
        {
            "user": user,
            "publications": publications,
            "search": search,
            "status_filter": status_filter,
            "department": department,
            "departments": departments,
            "page": page,
            "total": total,
            "per_page": per_page,
            "flash_messages": _get_flashes(request),
            "PublicationStatus": PublicationStatus,
        },
    )


@router.get("/openalex", response_class=HTMLResponse)
async def openalex_search_page(
    request: Request,
    q: str = "",
    search_type: str = "title",
    user: Faculty = Depends(get_current_user),
):
    """Search OpenAlex works by title, author name, or DOI."""
    results = []
    error = None
    query = q.strip()
    if query:
        try:
            if search_type == "doi" or query.startswith("10.") or "doi.org/" in query:
                work = await fetch_work_by_doi(query)
                results = [work] if work else []
            elif search_type == "author":
                results = await search_works_by_author(query, per_page=20)
            else:
                results = await search_works(query, per_page=20)
        except Exception as exc:
            error = f"OpenAlex lookup failed: {exc}"

    return templates.TemplateResponse(
        request,
        "publications/openalex_search.html",
        {
            "user": user,
            "query": query,
            "search_type": search_type,
            "results": results,
            "error": error,
            "flash_messages": _get_flashes(request),
        },
    )


@router.post("/openalex/import")
async def openalex_import_work(
    request: Request,
    db: Session = Depends(get_db),
    user: Faculty = Depends(get_current_user),
):
    """Import a single OpenAlex search result into the user's publications."""
    form = await request.form()
    year_val = form.get("year", "").strip()
    work = {
        "title": form.get("title", "").strip(),
        "authors": form.get("authors", "").strip() or user.name,
        "venue": form.get("venue", "").strip(),
        "year": int(year_val) if year_val.isdigit() else None,
        "doi": form.get("doi", "").strip() or None,
        "type": form.get("pub_type", "other"),
        "source": "openalex",
    }
    if not work["title"]:
        _flash(request, "error", "Cannot import a work without a title.")
        return RedirectResponse(url="/publications/openalex", status_code=302)

    _fetched, merged, queued = ingest_works_for_faculty(db, user, [work], "openalex")
    db.commit()
    _flash(
        request,
        "success",
        f"OpenAlex import complete ({merged} merged, {queued} queued for review).",
    )
    return RedirectResponse(url="/publications", status_code=302)


@router.post("/openalex/sync-mine")
async def openalex_sync_mine(
    request: Request,
    db: Session = Depends(get_db),
    user: Faculty = Depends(get_current_user),
):
    """Sync the logged-in faculty member's publications from OpenAlex using their ORCID."""
    if not user.orcid_id:
        _flash(request, "error", "No ORCID iD configured on your profile.")
        return RedirectResponse(url="/publications/openalex", status_code=302)

    try:
        works = await fetch_works_by_orcid(user.orcid_id)
    except Exception as exc:
        _flash(request, "error", f"OpenAlex sync failed: {exc}")
        return RedirectResponse(url="/publications/openalex", status_code=302)

    fetched, merged, queued = ingest_works_for_faculty(db, user, works, "openalex")
    db.commit()
    _flash(
        request,
        "success",
        f"Synced from OpenAlex: {fetched} fetched ({merged} merged, {queued} queued).",
    )
    return RedirectResponse(url="/publications", status_code=302)


@router.get("/upload-scholar", response_class=HTMLResponse)
async def upload_scholar_page(
    request: Request,
    user: Faculty = Depends(get_current_user),
):
    """Show form to upload a Google Scholar BibTeX or CSV export."""
    return templates.TemplateResponse(
        request,
        "publications/upload_scholar.html",
        {
            "user": user,
            "flash_messages": _get_flashes(request),
        },
    )


@router.post("/upload-scholar")
async def upload_scholar(
    request: Request,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: Faculty = Depends(get_current_user),
):
    """Parse and ingest a faculty-uploaded BibTeX or CSV export."""
    raw_bytes = await file.read()
    content = raw_bytes.decode("utf-8", errors="replace")
    filename = (file.filename or "").lower()

    if filename.endswith(".bib"):
        works = parse_bibtex(content)
    elif filename.endswith(".csv"):
        works = parse_csv_export(content)
    else:
        _flash(request, "error", "Unsupported file format. Please upload a .bib or .csv file.")
        return RedirectResponse(url="/publications/upload-scholar", status_code=302)

    fetched, merged, queued = ingest_works_for_faculty(db, user, works, "scholar_export")
    db.commit()
    _flash(
        request,
        "success",
        f"Imported {fetched} entries ({merged} merged, {queued} queued for review).",
    )
    return RedirectResponse(url="/publications", status_code=302)


@router.get("/new", response_class=HTMLResponse)
async def new_publication(
    request: Request,
    db: Session = Depends(get_db),
    user: Faculty = Depends(get_current_user),
):
    """Show form for creating a new publication."""
    faculty_list = (
        db.query(Faculty)
        .filter(Faculty.id != user.id)
        .order_by(Faculty.name)
        .all()
    )
    return templates.TemplateResponse(
        request,
        "publications/form.html",
        {
            "user": user,
            "publication": None,
            "pub_types": PublicationType,
            "faculty_list": faculty_list,
            "flash_messages": _get_flashes(request),
        },
    )


@router.post("/new")
async def create_publication(
    request: Request,
    db: Session = Depends(get_db),
    user: Faculty = Depends(get_current_user),
):
    """Create a new publication or link the user as a co-author on an existing DOI."""
    form = await request.form()

    doi = normalize_doi(form.get("doi", ""))
    if doi:
        existing = db.query(Publication).filter(Publication.doi == doi).first()
        if existing:
            if existing.is_attributed_to(user.id):
                _flash(
                    request,
                    "info",
                    f"You are already attributed to the publication with DOI {doi}.",
                )
            else:
                attribute_coauthor(existing, user)
                db.commit()
                _flash(
                    request,
                    "success",
                    f"Publication with DOI {doi} already exists. "
                    "You have been linked as a co-author.",
                )
            return RedirectResponse(url=f"/publications/{existing.id}", status_code=302)

    pub = Publication(
        title=form.get("title", "").strip(),
        authors=form.get("authors", "").strip(),
        venue=form.get("venue", "").strip() or None,
        year=int(form.get("year")) if form.get("year") else None,
        doi=doi,
        pub_type=form.get("pub_type", "other"),
        department=form.get("department", "").strip() or user.department,
        status=PublicationStatus.DRAFT,
        source=PublicationSource.MANUAL,
        owner_faculty_id=user.id,
    )
    db.add(pub)
    db.flush()
    sync_coauthors(db, pub, form.getlist("coauthor_ids"))
    db.commit()
    _flash(request, "success", "Publication created successfully.")
    return RedirectResponse(url="/publications", status_code=302)


@router.get("/{pub_id}", response_class=HTMLResponse)
async def view_publication(
    pub_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user: Faculty = Depends(get_current_user),
):
    """View a single publication."""
    pub = _get_publication_or_404(db, pub_id)
    if user.role == FacultyRole.FACULTY and not pub.is_attributed_to(user.id):
        raise HTTPException(status_code=403, detail="Access denied")

    excluded_ids = {pub.owner_faculty_id, *pub.coauthor_ids}
    available_coauthors = (
        db.query(Faculty)
        .filter(Faculty.id.notin_(excluded_ids))
        .order_by(Faculty.name)
        .all()
    )
    return templates.TemplateResponse(
        request,
        "publications/detail.html",
        {
            "user": user,
            "publication": pub,
            "owner": pub.owner,
            "can_manage": _can_manage_publication(pub, user),
            "available_coauthors": available_coauthors,
            "flash_messages": _get_flashes(request),
        },
    )


@router.get("/{pub_id}/proof")
async def download_publication_proof(
    pub_id: int,
    db: Session = Depends(get_db),
    user: Faculty = Depends(get_current_user),
):
    """Download a PDF verification proof for a publication record."""
    pub = _get_publication_or_404(db, pub_id)
    if user.role == FacultyRole.FACULTY and not pub.is_attributed_to(user.id):
        raise HTTPException(status_code=403, detail="Access denied")

    pdf_bytes = build_publication_proof_pdf(pub)
    filename = f"scholarledger_publication_{pub.id}_proof.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/{pub_id}/edit", response_class=HTMLResponse)
async def edit_publication_page(
    pub_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user: Faculty = Depends(get_current_user),
):
    """Show edit form for a publication."""
    pub = _get_publication_or_404(db, pub_id)
    if not _can_manage_publication(pub, user):
        raise HTTPException(status_code=403, detail="Access denied")

    faculty_list = (
        db.query(Faculty)
        .filter(Faculty.id != pub.owner_faculty_id)
        .order_by(Faculty.name)
        .all()
    )
    return templates.TemplateResponse(
        request,
        "publications/form.html",
        {
            "user": user,
            "publication": pub,
            "pub_types": PublicationType,
            "faculty_list": faculty_list,
            "flash_messages": _get_flashes(request),
        },
    )


@router.post("/{pub_id}/edit")
async def edit_publication(
    pub_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user: Faculty = Depends(get_current_user),
):
    """Update a publication."""
    pub = _get_publication_or_404(db, pub_id)
    if not _can_manage_publication(pub, user):
        raise HTTPException(status_code=403, detail="Access denied")

    form = await request.form()
    pub.title = form.get("title", pub.title).strip()
    pub.authors = form.get("authors", pub.authors).strip()
    pub.venue = form.get("venue", "").strip() or None
    pub.year = int(form.get("year")) if form.get("year") else None
    new_doi = normalize_doi(form.get("doi", ""))
    if new_doi and new_doi != pub.doi:
        existing = db.query(Publication).filter(Publication.doi == new_doi).first()
        if existing and existing.id != pub.id:
            _flash(request, "error", f"DOI {new_doi} is already in use.")
            return RedirectResponse(url=f"/publications/{pub_id}/edit", status_code=302)
    pub.doi = new_doi
    pub.pub_type = form.get("pub_type", pub.pub_type)
    pub.department = form.get("department", "").strip() or pub.department
    if form.get("_coauthors_submitted") or "coauthor_ids" in form:
        sync_coauthors(db, pub, form.getlist("coauthor_ids"))

    db.commit()
    _flash(request, "success", "Publication updated successfully.")
    return RedirectResponse(url=f"/publications/{pub_id}", status_code=302)


@router.post("/{pub_id}/coauthors/add")
async def add_coauthor(
    pub_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user: Faculty = Depends(get_current_user),
):
    """Attach an internal faculty co-author to a publication."""
    pub = _get_publication_or_404(db, pub_id)
    if not _can_manage_publication(pub, user):
        raise HTTPException(status_code=403, detail="Access denied")

    form = await request.form()
    raw_faculty_id = form.get("faculty_id", "").strip()
    try:
        target_id = int(raw_faculty_id)
    except ValueError:
        _flash(request, "error", "Please select a valid faculty member.")
        return RedirectResponse(url=f"/publications/{pub_id}", status_code=302)

    target = db.get(Faculty, target_id)
    if not target:
        raise HTTPException(status_code=404, detail="Faculty member not found")

    if attribute_coauthor(pub, target):
        db.commit()
        _flash(request, "success", f"Added {target.name} as a co-author.")
    else:
        _flash(request, "info", f"{target.name} is already attributed to this publication.")
    return RedirectResponse(url=f"/publications/{pub_id}", status_code=302)


@router.post("/{pub_id}/coauthors/{faculty_id}/remove")
async def remove_coauthor(
    pub_id: int,
    faculty_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user: Faculty = Depends(get_current_user),
):
    """Remove an internal faculty co-author (by owner, admin, or the co-author themselves)."""
    pub = _get_publication_or_404(db, pub_id)
    if not (_can_manage_publication(pub, user) or user.id == faculty_id):
        raise HTTPException(status_code=403, detail="Access denied")

    target = next((fac for fac in pub.coauthors if fac.id == faculty_id), None)
    if not target:
        _flash(request, "warning", "Co-author link not found.")
        return RedirectResponse(url=f"/publications/{pub_id}", status_code=302)

    pub.coauthors.remove(target)
    db.commit()
    _flash(request, "success", f"Removed {target.name} from co-authors.")

    if (
        user.role == FacultyRole.FACULTY
        and user.id == faculty_id
        and pub.owner_faculty_id != user.id
    ):
        return RedirectResponse(url="/publications", status_code=302)
    return RedirectResponse(url=f"/publications/{pub_id}", status_code=302)


@router.post("/{pub_id}/submit")
async def submit_publication(
    pub_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user: Faculty = Depends(get_current_user),
):
    """Submit a draft publication for verification."""
    pub = _get_publication_or_404(db, pub_id)
    if not _can_manage_publication(pub, user):
        raise HTTPException(status_code=403, detail="Access denied")
    if pub.status != PublicationStatus.DRAFT:
        _flash(request, "warning", "Only draft publications can be submitted.")
        return RedirectResponse(url=f"/publications/{pub_id}", status_code=302)

    pub.status = PublicationStatus.SUBMITTED
    db.commit()
    _flash(request, "success", "Publication submitted for verification.")
    return RedirectResponse(url=f"/publications/{pub_id}", status_code=302)
