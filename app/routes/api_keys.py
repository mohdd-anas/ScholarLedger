"""API key management UI and programmatic JSON API routes."""

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.auth.security import generate_api_key
from app.database import get_db
from app.main import templates
from app.models.api_key import ApiKey
from app.models.faculty import Faculty, FacultyRole
from app.models.publication import Publication
from app.schemas.publication import PublicationRead

router = APIRouter(tags=["api-keys"])


def _flash(request: Request, category: str, message: str):
    if "flash_messages" not in request.session:
        request.session["flash_messages"] = []
    request.session["flash_messages"].append([category, message])


def _get_flashes(request: Request) -> list:
    return request.session.pop("flash_messages", [])


@router.get("/api-keys", response_class=HTMLResponse)
async def list_api_keys(
    request: Request,
    db: Session = Depends(get_db),
    user: Faculty = Depends(get_current_user),
):
    """List the current user's API keys."""
    keys = (
        db.query(ApiKey)
        .filter(ApiKey.faculty_id == user.id)
        .order_by(ApiKey.created_at.desc())
        .all()
    )
    new_key = request.session.pop("new_api_key", None)
    return templates.TemplateResponse(
        request,
        "api_keys/list.html",
        {
            "user": user,
            "keys": keys,
            "new_key": new_key,
            "flash_messages": _get_flashes(request),
        },
    )


@router.post("/api-keys/create")
async def create_api_key(
    request: Request,
    db: Session = Depends(get_db),
    user: Faculty = Depends(get_current_user),
):
    """Create a new API key; plaintext is shown once in the session."""
    form = await request.form()
    name = form.get("name", "").strip()
    if not name:
        _flash(request, "error", "API key name is required.")
        return RedirectResponse(url="/api-keys", status_code=302)

    plaintext, prefix, key_hash = generate_api_key()
    api_key = ApiKey(
        name=name,
        key_prefix=prefix,
        key_hash=key_hash,
        faculty_id=user.id,
        is_active=True,
    )
    db.add(api_key)
    db.commit()

    request.session["new_api_key"] = plaintext
    _flash(
        request,
        "success",
        f"API key '{name}' created. Copy it now — it will not be shown again.",
    )
    return RedirectResponse(url="/api-keys", status_code=302)


@router.post("/api-keys/{key_id}/revoke")
async def revoke_api_key(
    key_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user: Faculty = Depends(get_current_user),
):
    """Revoke an existing API key."""
    api_key = db.get(ApiKey, key_id)
    if not api_key:
        raise HTTPException(status_code=404, detail="API key not found")
    if api_key.faculty_id != user.id and user.role != FacultyRole.ADMIN:
        raise HTTPException(status_code=403, detail="Access denied")

    api_key.is_active = False
    db.commit()
    _flash(request, "warning", f"API key '{api_key.name}' revoked.")
    return RedirectResponse(url="/api-keys", status_code=302)


@router.get("/api/v1/me")
async def api_me(user: Faculty = Depends(get_current_user)):
    """Return the authenticated user's profile (works with X-API-Key or session)."""
    return {
        "id": user.id,
        "name": user.name,
        "email": user.email,
        "department": user.department,
        "role": user.role.value,
        "orcid_id": user.orcid_id,
    }


@router.get("/api/v1/publications", response_model=list[PublicationRead])
async def api_list_publications(
    db: Session = Depends(get_db),
    user: Faculty = Depends(get_current_user),
):
    """Programmatic JSON endpoint for publications (supports X-API-Key)."""
    query = db.query(Publication)
    if user.role == FacultyRole.FACULTY:
        query = query.filter(Publication.owner_faculty_id == user.id)
    return query.order_by(Publication.created_at.desc()).all()
