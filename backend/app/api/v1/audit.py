"""
GeoVault AI - Audit Log Router (Phase 5F)
Provides enterprise-grade, authorization-aware endpoints for audit logs,
safe filtering, pagination, and KPI metrics.
"""

from typing import Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.security.context import UserContext, AuthorizedScope
from app.security.dependencies import get_current_user, get_authorized_scope
from app.schemas.audit import AuditLogPaginatedResponse, AuditLogSummaryResponse
from app.services.audit_service import AuditLogService

router = APIRouter(prefix="/audit-logs", tags=["Audit & Governance"])


@router.get(
    "/",
    response_model=AuditLogPaginatedResponse,
    status_code=status.HTTP_200_OK,
    summary="Get paginated, scope-filtered audit logs",
)
def get_audit_logs(
    mine: Optional[str] = Query(None, description="Filter logs by canonical mine code"),
    action: Optional[str] = Query(None, description="Filter logs by action/route (SQL, RAG, REPORT, etc.)"),
    status: Optional[str] = Query(None, description="Filter logs by semantic status (SUCCESS, DISCREPANCY, DENIED)"),
    user_id: Optional[str] = Query(None, description="Filter logs by user ID (Administrator scope only)"),
    start_date: Optional[str] = Query(None, description="Filter logs on or after ISO timestamp"),
    end_date: Optional[str] = Query(None, description="Filter logs on or before ISO timestamp"),
    search: Optional[str] = Query(None, description="Free text search over details and IDs"),
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(25, ge=1, le=100, description="Records per page (max 100)"),
    log_access: bool = Query(False, description="Optionally record an AUDIT_LOG_ACCESS event"),
    db: Session = Depends(get_db),
    user: UserContext = Depends(get_current_user),
    scope: AuthorizedScope = Depends(get_authorized_scope),
) -> AuditLogPaginatedResponse:
    """
    Returns sanitized, permission-filtered audit history.
    - Regular users: strictly limited to their own actions and authorized mine scope.
    - Administrators: enterprise-wide access with optional user filtering.
    """
    if log_access:
        AuditLogService.log_audit_access(db=db, user=user, scope=scope, filter_mine=mine)

    return AuditLogService.get_audit_logs(
        db=db,
        user=user,
        scope=scope,
        mine=mine,
        action=action,
        status_filter=status,
        user_id_filter=user_id,
        start_date=start_date,
        end_date=end_date,
        search=search,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/summary",
    response_model=AuditLogSummaryResponse,
    status_code=status.HTTP_200_OK,
    summary="Get aggregate audit summary statistics",
)
def get_audit_summary(
    mine: Optional[str] = Query(None, description="Optional mine filter"),
    db: Session = Depends(get_db),
    user: UserContext = Depends(get_current_user),
    scope: AuthorizedScope = Depends(get_authorized_scope),
) -> AuditLogSummaryResponse:
    """
    Returns summary statistics (total, success, discrepancies, denials, avg latency)
    computed strictly from records within the caller's authorized scope.
    """
    return AuditLogService.get_audit_summary(
        db=db,
        user=user,
        scope=scope,
        mine=mine,
    )
