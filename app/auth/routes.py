"""Auth routes — register, login, logout."""

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.auth.security import hash_password, verify_password
from app.database import get_db
from app.main import templates
from app.models.faculty import Faculty, FacultyRole

router = APIRouter(tags=["auth"])


def _flash(request: Request, category: str, message: str):
    """Add a flash message to the session."""
    if "flash_messages" not in request.session:
        request.session["flash_messages"] = []
    request.session["flash_messages"].append([category, message])


def _get_flashes(request: Request) -> list:
    """Pop flash messages from the session."""
    messages = request.session.pop("flash_messages", [])
    return messages


def _get_user(request: Request, db: Session) -> Faculty | None:
    """Get the current user from session, or None."""
    user_id = request.session.get("user_id")
    if user_id:
        return db.get(Faculty, user_id)
    return None


@router.get("/register", response_class=HTMLResponse)
async def register_page(request: Request, db: Session = Depends(get_db)):
    user = _get_user(request, db)
    if user:
        return RedirectResponse(url="/publications", status_code=302)
    return templates.TemplateResponse(
        request,
        "register.html",
        {"user": None, "flash_messages": _get_flashes(request)},
    )


@router.post("/register")
async def register(request: Request, db: Session = Depends(get_db)):
    form = await request.form()
    name = form.get("name", "").strip()
    email = form.get("email", "").strip().lower()
    department = form.get("department", "").strip()
    orcid_id = form.get("orcid_id", "").strip() or None
    password = form.get("password", "")
    confirm_password = form.get("confirm_password", "")

    # Validation
    errors = []
    if not name or not email or not department:
        errors.append("Name, email, and department are required.")
    if len(password) < 8:
        errors.append("Password must be at least 8 characters.")
    if password != confirm_password:
        errors.append("Passwords do not match.")
    if db.query(Faculty).filter(Faculty.email == email).first():
        errors.append("An account with this email already exists.")
    if orcid_id and db.query(Faculty).filter(Faculty.orcid_id == orcid_id).first():
        errors.append("This ORCID iD is already registered.")

    if errors:
        for e in errors:
            _flash(request, "error", e)
        return RedirectResponse(url="/register", status_code=302)

    faculty = Faculty(
        name=name,
        email=email,
        department=department,
        orcid_id=orcid_id,
        role=FacultyRole.FACULTY,
        password_hash=hash_password(password),
    )
    db.add(faculty)
    db.commit()
    db.refresh(faculty)

    request.session["user_id"] = faculty.id
    _flash(request, "success", f"Welcome, {faculty.name}! Your account has been created.")
    return RedirectResponse(url="/publications", status_code=302)


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request, db: Session = Depends(get_db)):
    user = _get_user(request, db)
    if user:
        return RedirectResponse(url="/publications", status_code=302)
    return templates.TemplateResponse(
        request,
        "login.html",
        {"user": None, "flash_messages": _get_flashes(request)},
    )


@router.post("/login")
async def login(request: Request, db: Session = Depends(get_db)):
    form = await request.form()
    email = form.get("email", "").strip().lower()
    password = form.get("password", "")

    faculty = db.query(Faculty).filter(Faculty.email == email).first()
    if not faculty or not verify_password(password, faculty.password_hash):
        _flash(request, "error", "Invalid email or password.")
        return RedirectResponse(url="/login", status_code=302)

    request.session["user_id"] = faculty.id
    _flash(request, "success", f"Welcome back, {faculty.name}!")
    return RedirectResponse(url="/publications", status_code=302)


@router.post("/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/login", status_code=302)
