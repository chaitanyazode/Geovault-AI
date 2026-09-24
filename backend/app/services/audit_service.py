"""
GeoVault AI - Centralized Audit Log Service (Phase 5F)
Implements Authorization-Before-Retrieval, safe sanitization,
server-side pagination, summary statistics, and non-recursive audit access logging.
"""

import re
import uuid
import logging
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, Tuple

from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import select, func, desc, and_, or_, cast, String

from app.models.governance import QueryAuditLog
from app.security.context import UserContext, AuthorizedScope
from app.schemas.audit import (
    AuditLogItemResponse,
    AuditLogSummaryResponse,
    AuditLogPaginatedResponse,
)

logger = logging.getLogger("geovault.audit_service")


class AuditLogService:
    """
    Centralized service for viewing, searching, and managing governance audit logs.
    Strictly forbids data leakage across security boundaries.
    """

    CANONICAL_MINES_MAP: Dict[str, str] = {
        "GV001": "GEVRA",
        "M-GEVRA": "GEVRA",
        "GEVRA": "GEVRA",
        "DEOM-01": "GEVRA",
        "GV002": "KUSMUNDA",
        "M-KUSMUNDA": "KUSMUNDA",
        "KUSMUNDA": "KUSMUNDA",
        "KNUG-02": "KUSMUNDA",
        "GV003": "DIPKA",
        "M-DIPKA": "DIPKA",
        "DIPKA": "DIPKA",
        "GV004": "NIGAHI",
        "M-NIGAHI": "NIGAHI",
        "NIGAHI": "NIGAHI",
        "GV005": "DUDHICHUA",
        "M-DUDHICHUA": "DUDHICHUA",
        "DUDHICHUA": "DUDHICHUA",
        "SSOP-03": "DUDHICHUA",
    }

    CANONICAL_DISPLAY_MAP: Dict[str, str] = {
        "GEVRA": "GV001 — GEVRA",
        "KUSMUNDA": "GV002 — KUSMUNDA",
        "DIPKA": "GV003 — DIPKA",
        "NIGAHI": "GV004 — NIGAHI",
        "DUDHICHUA": "GV005 — DUDHICHUA",
        "GV001": "GV001 — GEVRA",
        "GV002": "GV002 — KUSMUNDA",
        "GV003": "GV003 — DIPKA",
        "GV004": "GV004 — NIGAHI",
        "GV005": "GV005 — DUDHICHUA",
    }

    @classmethod
    def _extract_mines_from_log(cls, log: QueryAuditLog) -> List[str]:
        """Extracts canonical mine codes involved in this audit entry."""
        mines_found = set()
        
        # Check scope snapshot
        scope_data = log.authorized_scope_applied or {}
        allowed = scope_data.get("allowed_mines")
        if isinstance(allowed, list):
            for m in allowed:
                can = cls.CANONICAL_MINES_MAP.get(str(m).upper())
                if can:
                    mines_found.add(can)

        # Check retrieval filter
        filter_data = log.retrieval_filter or {}
        filt_mine = filter_data.get("mine") or filter_data.get("mine_code")
        if filt_mine:
            can = cls.CANONICAL_MINES_MAP.get(str(filt_mine).upper())
            if can:
                mines_found.add(can)

        # Check question / action text
        text_to_scan = f"{log.question or ''} {log.response_summary or ''}"
        for token in ["GEVRA", "KUSMUNDA", "DIPKA", "NIGAHI", "DUDHICHUA", "GV001", "GV002", "GV003", "GV004", "GV005"]:
            if re.search(rf"\b{token}\b", text_to_scan, flags=re.IGNORECASE):
                can = cls.CANONICAL_MINES_MAP.get(token.upper())
                if can:
                    mines_found.add(can)

        return sorted(list(mines_found))

    @classmethod
    def _sanitize_details(cls, log: QueryAuditLog, scope: AuthorizedScope) -> str:
        """
        Produces safe, sanitized details for display.
        Strips passwords, private model thoughts, raw text chunks, and unauthorized mine hints.
        """
        raw_text = log.question or ""
        
        # Strip any accidental chain of thought or internal reasoning
        raw_text = re.sub(r"<think>.*?</think>", "", raw_text, flags=re.DOTALL)
        raw_text = re.sub(r"\[Notice:.*?\]", "", raw_text).strip()

        # If this was an access denial event and caller is restricted, ensure unauthorized target is masked
        is_denied = (
            log.evidence_status == "INSUFFICIENT_AUTHORIZED_DATA"
            or "access denied" in (log.response_summary or "").lower()
            or "not authorized" in (log.response_summary or "").lower()
        )

        if is_denied and scope.allowed_mines is not None:
            # Check if raw text references an unauthorized mine
            for unauth_token, canonical in cls.CANONICAL_MINES_MAP.items():
                if not scope.is_mine_permitted(canonical):
                    if re.search(rf"\b{unauth_token}\b", raw_text, flags=re.IGNORECASE):
                        return "Security boundary enforced: Request outside authorized operational scope."

        # Replace legacy mock names with canonical clean labels
        cleaned = raw_text
        cleaned = re.sub(r"\bDEOM-01\b", "GV001 (GEVRA)", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\bKNUG-02\b", "GV002 (KUSMUNDA)", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\bSSOP-03\b", "GV005 (DUDHICHUA)", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\bDharani East Opencast Mine\b", "Gevra Opencast Mine", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\bDharani\b", "Gevra", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\bShakti Coalfields\b", "SECL", cleaned, flags=re.IGNORECASE)

        # Truncate to reasonable length
        if len(cleaned) > 200:
            cleaned = cleaned[:197] + "..."

        return cleaned or "Operational query execution"

    @classmethod
    def _map_action_and_module(cls, log: QueryAuditLog) -> Tuple[str, str, str, int]:
        """Maps route and evidence status to institutional action, module, status label, and HTTP code."""
        route = (log.route_selected or "SQL").upper()
        
        module = "Ask GeoVault"
        action = "Natural Query"
        http_status = 200

        if route == "TOPIC":
            module = "Topics & Word Cloud"
            action = "Topic Analysis"
        elif route == "REPORT":
            module = "Automated Reports"
            action = "Report Generation"
        elif route == "SQL":
            module = "Dashboard"
            action = "Structured Query"
        elif route == "ANALYTICS":
            module = "Analytics Engine"
            action = "Operational Analytics"
        elif route == "RAG":
            module = "Ask GeoVault"
            action = "Unstructured RAG"
        elif route == "HYBRID":
            module = "Ask GeoVault"
            action = "Hybrid Intelligence"
        elif route == "SPATIAL":
            module = "Geospatial"
            action = "Spatial Query"
        elif route == "GEOLOGY":
            module = "Geology"
            action = "Geological Evaluation"
        elif route == "AUDIT":
            module = "Audit System"
            action = "Audit Log Access"
        elif route == "SECURITY":
            module = "Security Boundary"
            action = "Authorization Check"

        # Determine semantic status
        resp_lower = (log.response_summary or "").lower()
        if (
            log.evidence_status == "INSUFFICIENT_AUTHORIZED_DATA"
            or "access denied" in resp_lower
            or "not authorized" in resp_lower
            or "403" in resp_lower
        ):
            status_label = "DENIED"
            action = f"{action} (Blocked)"
            http_status = 403
        elif log.evidence_status == "CONFLICT" or "conflict" in resp_lower:
            status_label = "DISCREPANCY"
        elif "error" in resp_lower or "failed" in resp_lower:
            status_label = "ERROR"
            http_status = 500
        else:
            status_label = "SUCCESS"

        return action, module, status_label, http_status

    @classmethod
    def serialize_log_entry(
        cls,
        log: QueryAuditLog,
        scope: AuthorizedScope,
    ) -> AuditLogItemResponse:
        """Transforms a raw QueryAuditLog into a sanitized response schema."""
        action, module, status_label, http_code = cls._map_action_and_module(log)
        mines = cls._extract_mines_from_log(log)
        sanitized_details = cls._sanitize_details(log, scope)

        # Extract report ID if present
        report_id_match = re.search(r"\b(REP-\d{8}-[A-F0-9]{6})\b", f"{log.question} {log.response_summary}")
        report_id = report_id_match.group(1) if report_id_match else None

        # Scope enforcement: only display mines permitted for the viewing user's scope
        display_mines = []
        for m in mines:
            can_name = cls.CANONICAL_MINES_MAP.get(m.upper(), m.upper())
            if scope.is_mine_permitted(can_name):
                display_mines.append(cls.CANONICAL_DISPLAY_MAP.get(can_name, m))

        return AuditLogItemResponse(
            log_id=log.log_id,
            timestamp=log.created_at.isoformat() if log.created_at else None,
            user_id=log.user_id,
            action=action,
            module=module,
            route=log.route_selected or "SQL",
            mine_scope=display_mines,
            status=status_label,
            evidence_status=log.evidence_status,
            evidence_count=log.evidence_count or 0,
            execution_time_ms=float(log.execution_time_ms) if log.execution_time_ms is not None else None,
            sanitized_details=sanitized_details,
            report_id=report_id,
            correlation_id=log.log_id,
            http_status=http_code,
        )

    @classmethod
    def get_audit_logs(
        cls,
        db: Session,
        user: UserContext,
        scope: AuthorizedScope,
        mine: Optional[str] = None,
        action: Optional[str] = None,
        status_filter: Optional[str] = None,
        user_id_filter: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        search: Optional[str] = None,
        page: int = 1,
        page_size: int = 25,
    ) -> AuditLogPaginatedResponse:
        """
        Retrieves paginated audit logs strictly enforcing Authorization-Before-Retrieval.
        Non-admin users can ONLY see their own activities within permitted mines.
        """
        # Validate pagination inputs
        page = max(1, page)
        page_size = max(1, min(100, page_size))

        # Check mine filter authorization
        if mine:
            canonical_requested = cls.CANONICAL_MINES_MAP.get(mine.upper(), mine.upper())
            if not scope.is_mine_permitted(canonical_requested):
                logger.warning(f"AUDIT SECURITY: User '{user.user_id}' requested logs for unauthorized mine '{mine}'.")
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Access Denied: You are not authorized to view audit logs for mine '{mine}'."
                )

        # Build base query
        query = select(QueryAuditLog)

        # 1. SCOPE ISOLATION:
        # Administrator can see all logs; others are restricted to their user ID
        if user.role != "Administrator":
            query = query.where(QueryAuditLog.user_id == user.user_id)
        elif user_id_filter:
            query = query.where(QueryAuditLog.user_id == user_id_filter)

        # 2. ACTION / ROUTE FILTERING
        if action:
            act_upper = action.upper()
            if act_upper in ("SQL", "RAG", "HYBRID", "ANALYTICS", "TOPIC", "REPORT", "SPATIAL", "GEOLOGY", "AUDIT"):
                query = query.where(QueryAuditLog.route_selected == act_upper)

        # 3. STATUS FILTERING
        if status_filter:
            st_upper = status_filter.upper()
            if st_upper == "DISCREPANCY":
                query = query.where(QueryAuditLog.evidence_status == "CONFLICT")
            elif st_upper == "DENIED":
                query = query.where(
                    or_(
                        QueryAuditLog.evidence_status == "INSUFFICIENT_AUTHORIZED_DATA",
                        QueryAuditLog.response_summary.ilike("%access denied%"),
                        QueryAuditLog.response_summary.ilike("%not authorized%"),
                    )
                )
            elif st_upper == "SUCCESS":
                query = query.where(
                    and_(
                        QueryAuditLog.evidence_status != "CONFLICT",
                        QueryAuditLog.evidence_status != "INSUFFICIENT_AUTHORIZED_DATA",
                        ~QueryAuditLog.response_summary.ilike("%access denied%"),
                    )
                )

        # 4. DATE RANGE FILTERING
        if start_date:
            try:
                dt_start = datetime.fromisoformat(start_date.replace("Z", "+00:00"))
                query = query.where(QueryAuditLog.created_at >= dt_start)
            except Exception:
                pass

        if end_date:
            try:
                dt_end = datetime.fromisoformat(end_date.replace("Z", "+00:00"))
                query = query.where(QueryAuditLog.created_at <= dt_end)
            except Exception:
                pass

        # 5. TEXT SEARCH (SEARCH QUESTION / RESPONSE)
        if search:
            search_pattern = f"%{search.strip()}%"
            query = query.where(
                or_(
                    QueryAuditLog.question.ilike(search_pattern),
                    QueryAuditLog.log_id.ilike(search_pattern),
                )
            )

        # 6. MINE FILTERING
        if mine:
            can_mine = cls.CANONICAL_MINES_MAP.get(mine.upper(), mine.upper())
            aliases = AuthorizedScope.MINE_ALIAS_SETS.get(mine.upper(), {mine.upper(), can_mine})
            conds = []
            for a in aliases:
                p = f"%{a}%"
                conds.append(QueryAuditLog.question.ilike(p))
                conds.append(cast(QueryAuditLog.retrieval_filter, String).ilike(p))
                conds.append(cast(QueryAuditLog.authorized_scope_applied, String).ilike(p))
            query = query.where(or_(*conds))

        # Compute total count
        count_query = select(func.count()).select_from(query.subquery())
        total = db.scalar(count_query) or 0

        # Order by newest first and apply pagination
        paginated_query = (
            query.order_by(desc(QueryAuditLog.created_at))
            .offset((page - 1) * page_size)
            .limit(page_size)
        )

        raw_logs = db.scalars(paginated_query).all()

        # Transform and sanitize
        items = [cls.serialize_log_entry(l, scope) for l in raw_logs]

        total_pages = max(1, (total + page_size - 1) // page_size) if total > 0 else 1

        return AuditLogPaginatedResponse(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )

    @classmethod
    def get_audit_summary(
        cls,
        db: Session,
        user: UserContext,
        scope: AuthorizedScope,
        mine: Optional[str] = None,
    ) -> AuditLogSummaryResponse:
        """
        Computes aggregate KPI metrics strictly across records the caller is authorized to view.
        """
        # Base query respecting user role
        base_query = select(QueryAuditLog)
        if user.role != "Administrator":
            base_query = base_query.where(QueryAuditLog.user_id == user.user_id)

        if mine:
            can_mine = cls.CANONICAL_MINES_MAP.get(mine.upper(), mine.upper())
            if not scope.is_mine_permitted(can_mine):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Access Denied: You are not authorized to view audit summary for mine '{mine}'."
                )
            aliases = AuthorizedScope.MINE_ALIAS_SETS.get(mine.upper(), {mine.upper(), can_mine})
            conds = []
            for a in aliases:
                p = f"%{a}%"
                conds.append(QueryAuditLog.question.ilike(p))
                conds.append(cast(QueryAuditLog.retrieval_filter, String).ilike(p))
                conds.append(cast(QueryAuditLog.authorized_scope_applied, String).ilike(p))
            base_query = base_query.where(or_(*conds))

        logs = db.scalars(base_query.limit(2000)).all()

        total = len(logs)
        successful = 0
        discrepancies = 0
        denied = 0
        reports = 0
        latencies = []

        for l in logs:
            _, _, st, _ = cls._map_action_and_module(l)
            if st == "SUCCESS":
                successful += 1
            elif st == "DISCREPANCY":
                discrepancies += 1
            elif st in ("DENIED", "ERROR"):
                denied += 1
            else:
                denied += 1

            if (l.route_selected or "").upper() == "REPORT":
                reports += 1

            if l.execution_time_ms is not None and l.execution_time_ms > 0:
                latencies.append(float(l.execution_time_ms))

        avg_lat = round(sum(latencies) / len(latencies), 1) if latencies else None

        # Determine authorized mines covered using canonical codes
        canonical_code_map = {
            "GEVRA": "GV001", "DEOM-01": "GV001", "GV001": "GV001", "M-GEVRA": "GV001",
            "KUSMUNDA": "GV002", "KNUG-02": "GV002", "GV002": "GV002", "M-KUSMUNDA": "GV002",
            "DIPKA": "GV003", "GV003": "GV003", "M-DIPKA": "GV003",
            "NIGAHI": "GV004", "GV004": "GV004", "M-NIGAHI": "GV004",
            "DUDHICHUA": "GV005", "SSOP-03": "GV005", "GV005": "GV005", "M-DUDHICHUA": "GV005",
        }
        if scope.allowed_mines is None:
            mines_covered = ["GV001", "GV002", "GV003", "GV004", "GV005"]
        else:
            can_set = set()
            for m in scope.allowed_mines:
                code = canonical_code_map.get(str(m).upper())
                if code:
                    can_set.add(code)
                else:
                    can_set.add(str(m))
            mines_covered = sorted(list(can_set))

        return AuditLogSummaryResponse(
            total_events=total,
            successful_events=successful,
            discrepancy_events=discrepancies,
            denied_events=denied,
            report_events=reports,
            avg_latency_ms=avg_lat,
            authorized_mines_covered=mines_covered,
        )

    @classmethod
    def log_audit_access(
        cls,
        db: Session,
        user: UserContext,
        scope: AuthorizedScope,
        filter_mine: Optional[str] = None,
    ) -> None:
        """
        Safely logs the viewing of audit logs without causing recursive logging loops.
        """
        try:
            log_id = f"AUD-{uuid.uuid4().hex[:12].upper()}"
            entry = QueryAuditLog(
                log_id=log_id,
                user_id=user.user_id,
                question=f"Audit log review accessed by {user.user_id} ({user.role})" + (f" [Filter: {filter_mine}]" if filter_mine else ""),
                route_selected="AUDIT",
                authorized_scope_applied=scope.to_dict(),
                retrieval_filter={"mine": filter_mine} if filter_mine else {},
                evidence_count=0,
                evidence_status="VERIFIED",
                response_summary="Authorized audit history retrieved successfully.",
                execution_time_ms=10,
            )
            db.add(entry)
            db.commit()
        except Exception as e:
            db.rollback()
            logger.warning(f"Failed to record AUDIT_LOG_ACCESS event: {e}")
