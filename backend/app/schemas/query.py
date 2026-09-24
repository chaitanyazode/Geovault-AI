"""
GeoVault AI - Query Intelligence & Analytics Schemas
Defines request/response models for facts, evidence, analytics, validation, and synthesis packages.
"""

from typing import Optional, List, Dict, Any, Union
from pydantic import BaseModel, Field


class EvidenceItem(BaseModel):
    """Represents a traceable, verifiable citation from structured database or unstructured document chunk."""
    evidence_id: str
    source_type: str  # STRUCTURED_RECORD, DOCUMENT_CHUNK
    source_name: str  # table name or document filename
    record_id: Optional[str] = None
    document_id: Optional[str] = None
    page_number: Optional[int] = None
    mine_code: Optional[str] = None
    department: Optional[str] = None
    classification: str = "INTERNAL"
    citation: str  # Human-readable citation string (e.g. "Production Database | DEOM-01 | FY2024")
    raw_data: Optional[Dict[str, Any]] = None
    snippet: Optional[str] = None


class ConflictItem(BaseModel):
    """Represents an identified discrepancy between authoritative sources."""
    conflict_id: str
    mine_code: Optional[str] = None
    year: Optional[int] = None
    metric_or_topic: str
    source_a_type: str
    source_a_reference: str
    source_a_value: str
    source_b_type: str
    source_b_reference: str
    source_b_value: str
    status: str = "CONFLICT"
    resolution_policy: Optional[str] = None


class MathCheck(BaseModel):
    """Validation check comparing database values against deterministic recalculations."""
    field_name: str
    database_value: Optional[float] = None
    calculated_value: Optional[float] = None
    is_valid: bool
    discrepancy: Optional[float] = None


class DataGap(BaseModel):
    """Represents missing data identified during query execution."""
    gap_type: str  # MISSING_YEAR, MISSING_MONTH, MISSING_FIELD, UNRECORDED_MINE
    entity: str
    description: str


class ValidationResult(BaseModel):
    """Outcome of deterministic mathematical cross-checking and conflict detection."""
    evidence_status: str = "VERIFIED"  # VERIFIED, PARTIAL, CONFLICT, INSUFFICIENT_AUTHORIZED_DATA
    math_checks: List[MathCheck] = Field(default_factory=list)
    data_gaps: List[DataGap] = Field(default_factory=list)
    conflicts_detected: List[ConflictItem] = Field(default_factory=list)
    is_complete: bool = True


class TrendPoint(BaseModel):
    time_label: Union[str, int]
    value: float
    target: Optional[float] = None
    yoy_change_mt: Optional[float] = None
    yoy_growth_pct: Optional[float] = None


class TrendSummary(BaseModel):
    direction: str  # UPWARD, DOWNWARD, FLUCTUATING, FLAT
    start_value: float
    end_value: float
    net_change: float
    net_change_pct: float
    min_point: Dict[str, Any]
    max_point: Dict[str, Any]
    series: List[TrendPoint]


class MineComparisonItem(BaseModel):
    mine_code: str
    mine_name: Optional[str] = None
    mine_type: Optional[str] = None
    total_production_mt: float
    avg_annual_production_mt: float
    target_mt: Optional[float] = None
    achievement_pct: Optional[float] = None
    avg_availability_pct: Optional[float] = None


class AnalyticsResult(BaseModel):
    """Standardized numerical analytics container (Python calculates)."""
    operation: str
    metric: str
    total: Optional[float] = None
    average: Optional[float] = None
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    target_achievement_pct: Optional[float] = None
    variance_mt: Optional[float] = None
    trend: Optional[TrendSummary] = None
    comparisons: Optional[List[MineComparisonItem]] = None
    series: Optional[List[Dict[str, Any]]] = None


class QueryResultPackage(BaseModel):
    """
    Unified query context package.
    Cleanly prepares facts, evidence, analytics, validation, and conflicts
    for downstream RAG and LLM synthesis.
    """
    domain: str
    query_description: str
    authorized_scope_applied: Dict[str, Any]
    facts: List[Dict[str, Any]]
    analytics: Optional[AnalyticsResult] = None
    evidence: List[EvidenceItem]
    validation: ValidationResult


# --- Request Schemas ---

class IntelligenceQueryRequest(BaseModel):
    domain: str = Field(..., description="Operational domain: production_annual, production_monthly, dispatch_summary, coal_quality, geological_units, mining_issue_log, inspection_register")
    mine_code: Optional[str] = Field(None, description="Optional mine code (e.g. DEOM-01)")
    year: Optional[int] = Field(None, description="Optional single reporting year")
    start_year: Optional[int] = Field(None, description="Optional start year for range")
    end_year: Optional[int] = Field(None, description="Optional end year for range")
    month: Optional[int] = Field(None, description="Optional month (1-12) for monthly production")
    category: Optional[str] = Field(None, description="Optional category filter (for issues/geology/inspections)")
    limit: int = Field(50, ge=1, le=500)


class IntelligenceAnalyticsRequest(BaseModel):
    operation: str = Field(..., description="Analytics operation: summary, yoy, trend, target_vs_actual, compare")
    domain: str = Field("production_annual", description="Operational domain")
    metric: str = Field("actual_production_mt", description="Numeric column to analyze")
    mine_code: Optional[str] = Field(None, description="Target mine code or None for enterprise/manager scope")
    year: Optional[int] = Field(None, description="Specific year if applicable")
    start_year: Optional[int] = Field(None, description="Range start year")
    end_year: Optional[int] = Field(None, description="Range end year")


class MineCompareRequest(BaseModel):
    mine_codes: Optional[List[str]] = Field(None, description="List of mines to compare (must be within authorized scope)")
    start_year: int = Field(2021, description="Start year")
    end_year: int = Field(2025, description="End year")


class NaturalQueryRequest(BaseModel):
    query: str = Field(..., description="Natural language question (e.g. 'What was DEOM-01 production in FY2024?')")
    target_mine: Optional[str] = Field(None, description="Optional mine hint (e.g. DEOM-01)")
    target_year: Optional[int] = Field(None, description="Optional year hint (e.g. 2024)")
    top_k: int = Field(5, ge=1, le=20, description="Maximum evidence items to retrieve")


class GroundedQueryResponse(BaseModel):
    """
    Standard GeoVault AI Grounded Response.
    Integrates evidence-grounded Qwen narrative, deterministic structured results,
    verifiable citations, math validation, and explicit conflict surfacing.
    """
    query: str
    query_type: str = Field(..., description="Selected route: SQL, RAG, HYBRID, ANALYTICS, TOPIC, REPORT")
    summary: Optional[str] = Field(None, description="Concise, 2-5 sentence descriptive executive summary")
    detailed_answer: Optional[str] = Field(None, description="Descriptive, structured explanation with headings and context")
    answer: str = Field(..., description="Complete evidence-grounded explanation synthesized by local Qwen3-8B")
    structured_results: Optional[Dict[str, Any]] = None
    evidence: List[EvidenceItem] = Field(default_factory=list)
    conflicts: List[ConflictItem] = Field(default_factory=list)
    data_gaps: List[DataGap] = Field(default_factory=list)
    validation_status: str = Field(..., description="VERIFIED, PARTIAL, CONFLICT, or INSUFFICIENT_AUTHORIZED_DATA")
    confidence_status: str = Field(..., description="HIGH, GROUNDED, CONFLICT_DETECTED, or INSUFFICIENT_DATA")
    source_references: List[str] = Field(default_factory=list)
    authorized_scope_applied: Dict[str, Any] = Field(default_factory=dict)
    processing_metadata: Dict[str, Any] = Field(default_factory=dict)

    @property
    def route_used(self) -> str:
        return self.query_type

    @property
    def grounded_explanation(self) -> str:
        return self.answer

    @property
    def metadata(self) -> Dict[str, Any]:
        return self.processing_metadata

    @property
    def evidence_items(self) -> List[EvidenceItem]:
        return self.evidence

