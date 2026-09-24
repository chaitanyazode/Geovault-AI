"""
GeoVault AI - FastAPI Security Dependencies
Injects authenticated user context, authorized scope, and permissions into route handlers.
"""

from typing import Generator, Optional
from fastapi import Header, HTTPException, Depends, status
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.security.context import UserContext, AuthorizedScope
from app.security.service import AuthorizationService
from app.security.roles import has_permission


def get_db() -> Generator[Session, None, None]:
    """Provides a transactional database session per request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_current_user(
    x_user_id: Optional[str] = Header(None, description="Demo User ID (e.g. USR001, USR002)"),
    db: Session = Depends(get_db),
) -> UserContext:
    """
    Resolves the authenticated user from the X-User-Id header.
    In development mode, defaults to USR001 (Mining Engineer, DEOM-01) if header is omitted.
    """
    user_id = x_user_id.strip() if x_user_id else "USR001"

    try:
        return AuthorizationService.resolve_user_context(db, user_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Authentication failed: {str(e)}",
        )


def get_authorized_scope(
    current_user: UserContext = Depends(get_current_user),
) -> AuthorizedScope:
    """Derives and injects the user's active AuthorizedScope."""
    return AuthorizationService.get_authorized_scope(current_user)


def require_permission(required_perm: str):
    """Factory dependency ensuring current user holds the required RBAC permission."""

    def _dependency(current_user: UserContext = Depends(get_current_user)) -> UserContext:
        if not has_permission(current_user.role, required_perm):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access Denied: Role '{current_user.role}' lacks permission '{required_perm}'.",
            )
        return current_user

    return _dependency
