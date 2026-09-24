"""
GeoVault AI - Report Generation Schemas (Phase 6B)
Pydantic schemas for professional report generation, metadata inspection, and download.
"""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class ReportGenerateRequest(BaseModel):
    """Request payload for generating a professional mining / geological report."""
    query: Optional[str] = Field(
        None,
        description="Natural language request, e.g. 'Generate a FY2024-25 production report for GEVRA'"
    )
    report_type: Optional[str] = Field(
        None,
        description="Report classification: PERFORMANCE, COMPARISON, GEOLOGY_ISSUES, EXECUTIVE, or CONFLICT"
    )
    mine_code: Optional[str] = Field(
        None,
        description="Primary target mine code (e.g. GV001). Must be in authorized scope."
    )
    compared_mines: Optional[List[str]] = Field(
        None,
        description="List of mine codes for comparison reports. All must be in authorized scope."
    )
    start_year: Optional[int] = Field(None, description="Starting calendar or fiscal year")
    end_year: Optional[int] = Field(None, description="Ending calendar or fiscal year")
    include_charts: bool = Field(True, description="Whether to generate and embed visualization charts")
    formats: List[str] = Field(default=["DOCX", "PDF"], description="Desired file formats")


class ReportMetadataResponse(BaseModel):
    """Metadata response for a generated professional report."""
    report_id: str
    report_title: str
    report_type: str
    mine_code: Optional[str] = None
    mines_covered: List[str] = Field(default_factory=list)
    reporting_period: str
    generated_at: str
    requested_by: str
    status: str = "GENERATED"
    output_formats: List[str] = Field(default_factory=lambda: ["DOCX", "PDF"])
    docx_download_url: Optional[str] = None
    pdf_download_url: Optional[str] = None
    evidence_count: int = 0
    conflict_count: int = 0
    data_gap_count: int = 0
    validation_status: str = "VERIFIED"
    executive_summary: Optional[str] = None
    production_annual: List[Dict[str, Any]] = Field(default_factory=list)
    evidence_citations: List[Dict[str, Any]] = Field(default_factory=list)
    key_indicators: List[Dict[str, Any]] = Field(default_factory=list)


class ReportDataPackage(BaseModel):
    """
    Validated container aggregating deterministic database results, analytics,
    evidence citations, conflicts, and synthesized narrative for document assembly.
    """
    report_id: str
    report_title: str
    report_type: str
    mines: List[str] = Field(default_factory=list)
    reporting_period: str
    generated_at: str
    requested_by: str
    role: str
    department: str
    executive_summary: str = ""
    mine_overviews: List[Dict[str, Any]] = Field(default_factory=list)
    production_annual: List[Dict[str, Any]] = Field(default_factory=list)
    target_vs_actual: List[Dict[str, Any]] = Field(default_factory=list)
    dispatch_records: List[Dict[str, Any]] = Field(default_factory=list)
    coal_quality: List[Dict[str, Any]] = Field(default_factory=list)
    geological_units: List[Dict[str, Any]] = Field(default_factory=list)
    mining_issues: List[Dict[str, Any]] = Field(default_factory=list)
    inspections: List[Dict[str, Any]] = Field(default_factory=list)
    mine_comparisons: List[Dict[str, Any]] = Field(default_factory=list)
    analytics_summary: Dict[str, Any] = Field(default_factory=dict)
    conflicts: List[Dict[str, Any]] = Field(default_factory=list)
    data_gaps: List[str] = Field(default_factory=list)
    evidence_citations: List[Dict[str, Any]] = Field(default_factory=list)
    chart_paths: Dict[str, str] = Field(default_factory=dict)
