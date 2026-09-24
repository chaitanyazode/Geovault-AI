"""
GeoVault AI - Security & Query Audit Logger
Persists query execution logs, applied scopes, and evidence statuses
to query_audit_logs without leaking confidential payload.
"""

import uuid
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from app.models.governance import QueryAuditLog
from app.security.context import AuthorizedScope


class AuditLogger:
    """Safely logs query activities without leaking unauthorized data."""

    @staticmethod
    def log_query(
        db: Session,
        user_id: str,
        question: str,
        route_selected: str,
        scope: AuthorizedScope,
        evidence_count: int,
        evidence_status: str,
        response_summary: Optional[str] = None,
        retrieval_filter: Optional[Dict[str, Any]] = None,
        execution_time_ms: Optional[int] = None,
    ) -> QueryAuditLog:
        """Persists audit record to PostgreSQL."""
        log_id = f"AUD-{uuid.uuid4().hex[:12].upper()}"

        audit_entry = QueryAuditLog(
            log_id=log_id,
            user_id=user_id,
            question=question,
            route_selected=route_selected,
            authorized_scope_applied=scope.to_dict(),
            retrieval_filter=retrieval_filter or {},
            evidence_count=evidence_count,
            evidence_status=evidence_status,
            response_summary=response_summary,
            execution_time_ms=execution_time_ms,
        )

        db.add(audit_entry)
        db.commit()
        return audit_entry
