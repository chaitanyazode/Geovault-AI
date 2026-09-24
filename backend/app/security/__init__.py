"""
GeoVault AI - Security Package
"""

from app.security.clearance import (
    ClearanceLevel,
    CLEARANCE_RANKS,
    get_clearance_rank,
    is_clearance_sufficient,
)
from app.security.roles import Permission, ROLE_PERMISSIONS, has_permission, get_role_permissions
from app.security.context import UserContext, ScopeRule, AuthorizedScope
from app.security.service import AuthorizationService
from app.security.dependencies import (
    get_db,
    get_current_user,
    get_authorized_scope,
    require_permission,
)
from app.security.audit import AuditLogger

__all__ = [
    "ClearanceLevel",
    "CLEARANCE_RANKS",
    "get_clearance_rank",
    "is_clearance_sufficient",
    "Permission",
    "ROLE_PERMISSIONS",
    "has_permission",
    "get_role_permissions",
    "UserContext",
    "ScopeRule",
    "AuthorizedScope",
    "AuthorizationService",
    "get_db",
    "get_current_user",
    "get_authorized_scope",
    "require_permission",
    "AuditLogger",
]
