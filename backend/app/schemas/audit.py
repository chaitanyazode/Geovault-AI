"""
GeoVault AI - Audit Log Schemas (Phase 5F)
Pydantic models for safe, enterprise-grade audit log inspection,
filtering, summary metrics, and server-side pagination.
"""

from typing import List, Optional
from pydantic import BaseModel, Field


class AuditLogItemResponse(BaseModel):
    """Sanitized individual audit log entry."""
    log_id: str = Field(..., description="Unique audit event identifier (e.g. AUD-XXXXXXXXXXXX)")
    timestamp: Optional[str] = Field(None, description="ISO-8601 formatted event creation timestamp")
    user_id: str = Field(..., description="Authenticated user identifier")
    action: str = Field(..., description="Human-readable action description")
    module: str = Field(..., description="GeoVault AI system module")
    route: str = Field(..., description="Underlying architectural execution route (SQL, RAG, HYBRID, etc.)")
    mine_scope: List[str] = Field(default_factory=list, description="Canonical mine codes involved in the event")
    status: str = Field(..., description="Semantic outcome status: SUCCESS, DISCREPANCY, DENIED, ERROR")
    evidence_status: Optional[str] = Field(None, description="Evidence verification status: VERIFIED, PARTIAL, CONFLICT, INSUFFICIENT_AUTHORIZED_DATA")
    evidence_count: int = Field(0, description="Count of evidence items retrieved or evaluated")
    execution_time_ms: Optional[float] = Field(None, description="Execution duration in milliseconds")
    sanitized_details: str = Field(..., description="Safe, sanitized query or action description")
    report_id: Optional[str] = Field(None, description="Associated report ID if action involved a report")
    correlation_id: Optional[str] = Field(None, description="Correlation identifier for tracing workflows")
    http_status: int = Field(200, description="HTTP response status associated with event")

    class Config:
        from_attributes = True


class AuditLogSummaryResponse(BaseModel):
    """Aggregate statistics for summary KPI cards computed strictly within authorized scope."""
    total_events: int = Field(..., description="Total audit events within authorized scope")
    successful_events: int = Field(..., description="Total successful events")
    discrepancy_events: int = Field(..., description="Events with data conflicts/discrepancies")
    denied_events: int = Field(..., description="Security denials within authorized scope")
    report_events: int = Field(..., description="Report generation and download events")
    avg_latency_ms: Optional[float] = Field(None, description="Average response latency in milliseconds")
    authorized_mines_covered: List[str] = Field(default_factory=list, description="List of authorized mines included in calculation")


class AuditLogPaginatedResponse(BaseModel):
    """Standardized server-side paginated audit response envelope."""
    items: List[AuditLogItemResponse] = Field(..., description="List of sanitized audit items for the current page")
    total: int = Field(..., description="Total matching items across all pages")
    page: int = Field(..., description="Current 1-indexed page number")
    page_size: int = Field(..., description="Number of items per page")
    total_pages: int = Field(..., description="Total available pages")
