"""
GeoVault AI - Roles & Permissions Registry (RBAC)
Defines granular actions and role-to-permission mappings.
"""

from typing import Set, Dict


class Permission:
    QUERY_STRUCTURED = "query:structured"
    QUERY_VECTOR = "query:vector"
    QUERY_AGGREGATE = "query:aggregate"
    VIEW_EVIDENCE = "view:evidence"
    VIEW_CONFLICTS = "view:conflicts"
    ADMIN_ALL = "admin:all"


ROLE_PERMISSIONS: Dict[str, Set[str]] = {
    "Mining Engineer": {
        Permission.QUERY_STRUCTURED,
        Permission.QUERY_VECTOR,
        Permission.QUERY_AGGREGATE,
        Permission.VIEW_EVIDENCE,
        Permission.VIEW_CONFLICTS,
    },
    "Geology Engineer": {
        Permission.QUERY_STRUCTURED,
        Permission.QUERY_VECTOR,
        Permission.QUERY_AGGREGATE,
        Permission.VIEW_EVIDENCE,
        Permission.VIEW_CONFLICTS,
    },
    "Transportation Engineer": {
        Permission.QUERY_STRUCTURED,
        Permission.QUERY_VECTOR,
        Permission.QUERY_AGGREGATE,
        Permission.VIEW_EVIDENCE,
        Permission.VIEW_CONFLICTS,
    },
    "Safety Engineer": {
        Permission.QUERY_STRUCTURED,
        Permission.QUERY_VECTOR,
        Permission.QUERY_AGGREGATE,
        Permission.VIEW_EVIDENCE,
        Permission.VIEW_CONFLICTS,
    },
    "Mine Manager": {
        Permission.QUERY_STRUCTURED,
        Permission.QUERY_VECTOR,
        Permission.QUERY_AGGREGATE,
        Permission.VIEW_EVIDENCE,
        Permission.VIEW_CONFLICTS,
    },
    "Administrator": {
        Permission.QUERY_STRUCTURED,
        Permission.QUERY_VECTOR,
        Permission.QUERY_AGGREGATE,
        Permission.VIEW_EVIDENCE,
        Permission.VIEW_CONFLICTS,
        Permission.ADMIN_ALL,
    },
}


def get_role_permissions(role: str) -> Set[str]:
    """Returns the set of permissions associated with a given role."""
    return ROLE_PERMISSIONS.get(role, set())


def has_permission(role: str, permission: str) -> bool:
    """Checks whether a role possesses a specific permission."""
    perms = get_role_permissions(role)
    if Permission.ADMIN_ALL in perms:
        return True
    return permission in perms
