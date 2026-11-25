"""FastAPI dependencies for authentication and role-based access control."""

from datetime import UTC, datetime

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.auth.security import hash_api_key
from app.database import get_db
from app.models.api_key import ApiKey
from app.models.faculty import Faculty, FacultyRole


def get_current_user(request: Request, db: Session = Depends(get_db)) -> Faculty:
    """Extract the current user from the session cookie or X-API-Key header."""
    api_key_header = request.headers.get("X-API-Key")
    if api_key_header:
        key_hash = hash_api_key(api_key_header.strip())
        api_key = (
            db.query(ApiKey)
            .filter(ApiKey.key_hash == key_hash, ApiKey.is_active.is_(True))
            .first()
        )
        if not api_key:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or revoked API key",
            )
        user = db.get(Faculty, api_key.faculty_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found"
            )
        api_key.last_used_at = datetime.now(UTC)
        db.commit()
        return user

    user_id = request.session.get("user_id")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated"
        )
    user = db.get(Faculty, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found"
        )
    return user


def require_role(*roles: FacultyRole):
    """Return a dependency that enforces one of the given roles."""

    def _check(user: Faculty = Depends(get_current_user)) -> Faculty:
        if user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )
        return user

    return _check

