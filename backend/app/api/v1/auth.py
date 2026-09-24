"""
GeoVault AI - Authentication & Scope Discovery Endpoints
Provides identity inspection and demo user listing.
"""

from typing import List, Dict, Any
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.models.master import User
from app.security.context import UserContext, AuthorizedScope
from app.security.dependencies import get_current_user, get_authorized_scope, get_db

router = APIRouter(prefix="/auth", tags=["Authentication & Identity"])


@router.get("/me")
def get_current_user_profile(
    user: UserContext = Depends(get_current_user),
    scope: AuthorizedScope = Depends(get_authorized_scope),
) -> Dict[str, Any]:
    """Returns the authenticated user's profile and active authorization boundary."""
    scope_dict = scope.to_dict()
    return {
        "user": user.model_dump(),
        "authorized_scope": scope_dict,
        "scope": scope_dict,
    }


@router.get("/users")
def list_demo_users(db: Session = Depends(get_db)) -> List[Dict[str, Any]]:
    """Lists available demo users for prototype testing and evaluation."""
    users = db.scalars(select(User).order_by(User.user_id)).all()
    results = []
    for u in users:
        results.append({
            "user_id": u.user_id,
            "username": u.username,
            "name": u.username,
            "role": u.role,
            "department": u.department,
            "clearance_level": u.clearance_level,
            "clearance": u.clearance_level,
            "assigned_mine_code": u.assigned_mine_code,
            "assigned_mine": u.assigned_mine_code,
            "description": f"{u.role} · {u.department} · {u.assigned_mine_code or 'HQ/ALL'}",
            "scopes": [
                {
                    "mine_code": s.mine_code,
                    "department": s.department,
                    "max_classification": s.max_classification,
                }
                for s in u.scopes
            ],
        })
    return results
