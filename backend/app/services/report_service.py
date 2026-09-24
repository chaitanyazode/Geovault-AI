"""
GeoVault AI - Report Generation Service (Phase 6B)
Enterprise report generation orchestrator enforcing 'Authorization Before Retrieval'.
Coordinates deterministic data gathering, mathematical validation, chart rendering,
grounded Qwen synthesis, and dual DOCX + PDF document construction.
"""

import os
import re
import time
import uuid
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple

from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.security.context import AuthorizedScope, UserContext
from app.security.service import AuthorizationService
from app.models.master import Mine
from app.models.governance import GeneratedReport, Conflict
from app.models.operational import ProductionAnnual, DispatchSummary, MiningIssueLog, InspectionRegister, CoalQuality, GeologicalUnit
from app.schemas.reports import ReportGenerateRequest, ReportMetadataResponse, ReportDataPackage
from app.schemas.query import EvidenceItem
from app.services.query_service import DeterministicQueryService
from app.analytics.engine import AnalyticsEngine
from app.services.evidence_engine import EvidenceEngine
from app.services.validation_engine import ValidationEngine
from app.services.report_charts import ReportChartGenerator
from app.services.report_docx import DocxReportBuilder
from app.services.report_pdf import PdfReportBuilder
from app.ai.qwen_reasoner import QwenReasonerClient, sanitize_llm_output

logger = logging.getLogger("geovault.report_service")


class ReportGenerationService:
    """
    Central service for generating verified mining, geological, and operational reports.
    Strictly forbids raw LLM data access or unauthorized retrieval.
    """

    REPORTS_DIR = "/data/reports"
    CHARTS_DIR = "/data/reports/charts"

    CANONICAL_MINES_MAP: Dict[str, str] = {
        "GV001": "GEVRA",
        "M-GEVRA": "GEVRA",
        "GEVRA": "GEVRA",
        "GV002": "KUSMUNDA",
        "M-KUSMUNDA": "KUSMUNDA",
        "KUSMUNDA": "KUSMUNDA",
        "GV003": "DIPKA",
        "M-DIPKA": "DIPKA",
        "DIPKA": "DIPKA",
        "GV004": "NIGAHI",
        "M-NIGAHI": "NIGAHI",
        "NIGAHI": "NIGAHI",
        "GV005": "DUDHICHUA",
        "M-DUDHICHUA": "DUDHICHUA",
        "DUDHICHUA": "DUDHICHUA",
        "DEOM-01": "GEVRA",
        "KNUG-02": "KUSMUNDA",
        "SSOP-03": "DUDHICHUA",
    }

    # Human-readable display names for PDF/DOCX report headers
    CANONICAL_DISPLAY_NAMES: Dict[str, str] = {
        "GV001": "Gevra Opencast Coal Mine",
        "GV002": "Kusmunda Opencast Coal Mine",
        "GV003": "Dipka Opencast Coal Mine",
        "GV004": "Nigahi Opencast Coal Mine",
        "GV005": "Dudhichua Opencast Coal Mine",
        "GEVRA": "Gevra Opencast Coal Mine",
        "KUSMUNDA": "Kusmunda Opencast Coal Mine",
        "DIPKA": "Dipka Opencast Coal Mine",
        "NIGAHI": "Nigahi Opencast Coal Mine",
        "DUDHICHUA": "Dudhichua Opencast Coal Mine",
    }

    def __init__(self):
        os.makedirs(self.REPORTS_DIR, exist_ok=True)
        os.makedirs(self.CHARTS_DIR, exist_ok=True)
        self.chart_generator = ReportChartGenerator(self.CHARTS_DIR)
        self.docx_builder = DocxReportBuilder(self.REPORTS_DIR)
        self.pdf_builder = PdfReportBuilder(self.REPORTS_DIR)
        self.qwen_client = QwenReasonerClient()

    @classmethod
    def _parse_report_query(cls, query: str) -> Dict[str, Any]:
        """
        Parses intent, target mine codes, and years from natural language query.
        """
        result = {
            "mines": [],
            "report_type": "PERFORMANCE",
            "start_year": None,
            "end_year": None,
            "is_comparison": False,
        }
        if not query:
            return result

        # Extract canonical mine names & codes (case-insensitive)
        pattern = r"\b(GEVRA|KUSMUNDA|DIPKA|NIGAHI|DUDHICHUA|GV001|GV002|GV003|GV004|GV005|M-GEVRA|M-KUSMUNDA|M-DIPKA|M-NIGAHI|M-DUDHICHUA|KNUG-02|DEOM-01|SSOP-03)\b"
        mines_found = re.findall(pattern, query, flags=re.IGNORECASE)
        # Normalize and map to canonical representation
        normalized_mines = []
        for m in mines_found:
            m_upper = m.upper()
            canonical = cls.CANONICAL_MINES_MAP.get(m_upper, m_upper)
            if canonical not in normalized_mines:
                normalized_mines.append(canonical)
        result["mines"] = normalized_mines

        # Detect comparison intent
        if len(result["mines"]) > 1 or any(k in query.lower() for k in ["compare", "comparison", " vs ", "versus"]):
            result["report_type"] = "COMPARISON"
            result["is_comparison"] = True
        elif any(k in query.lower() for k in ["conflict", "discrepanc"]):
            result["report_type"] = "CONFLICT"
        elif any(k in query.lower() for k in ["geolog", "strata", "fault", "issue", "equipment"]):
            result["report_type"] = "GEOLOGY_ISSUES"
        elif any(k in query.lower() for k in ["executive", "summary", "assigned"]):
            result["report_type"] = "EXECUTIVE"

        # Detect multi-year or specific years
        five_year = re.search(r"\b5[ -]?year\b", query, flags=re.IGNORECASE)
        if five_year:
            result["start_year"] = 2021
            result["end_year"] = 2025

        years = re.findall(r"\b(202[0-9])\b", query)
        if years and not result["start_year"]:
            int_years = sorted([int(y) for y in years])
            result["start_year"] = int_years[0]
            result["end_year"] = int_years[-1]

        return result

    def generate_report(
        self,
        db: Session,
        user: UserContext,
        request: ReportGenerateRequest,
        scope: Optional[AuthorizedScope] = None,
    ) -> ReportMetadataResponse:
        """
        Main pipeline:
        Authorization check -> Scoped Retrieval -> Deterministic Validation -> Qwen Narrative -> Charts -> DOCX/PDF -> DB Persistence
        """
        start_time = time.time()
        if scope is None:
            scope = AuthorizationService.get_authorized_scope(user)

        # 1. Parse parameters and natural query
        parsed = self._parse_report_query(request.query or "")
        
        target_mines = list(request.compared_mines or [])
        if request.mine_code and request.mine_code not in target_mines:
            target_mines.insert(0, request.mine_code)
        
        # Merge parsed mines if request didn't supply them explicitly
        if not target_mines and parsed["mines"]:
            target_mines = parsed["mines"]

        # Default to user's assigned mine if no mine specified
        if not target_mines:
            if user.assigned_mine_code:
                target_mines = [user.assigned_mine_code]
            elif scope.allowed_mines is not None and len(scope.allowed_mines) > 0:
                target_mines = list(scope.allowed_mines)
            elif scope.allowed_mines is None or user.role == "Administrator":
                # Admin with full scope defaults to all known primary canonical mines
                target_mines = ["GEVRA", "KUSMUNDA", "DIPKA", "NIGAHI", "DUDHICHUA"]

        report_type = request.report_type or parsed["report_type"]
        if len(target_mines) > 1:
            report_type = "COMPARISON"

        start_year = request.start_year or parsed["start_year"] or 2021
        end_year = request.end_year or parsed["end_year"] or 2025

        # 2. CRITICAL: AUTHORIZATION BEFORE RETRIEVAL
        # Verify that EVERY requested mine is strictly permitted
        for m in target_mines:
            if not scope.is_mine_permitted(m):
                logger.warning(
                    f"SECURITY DENIAL: User '{user.user_id}' requested unauthorized mine '{m}' in report generation."
                )
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Access Denied: You are not authorized to view or generate reports for mine '{m}'. "
                           f"Authorized mines: {list(scope.allowed_mines) if scope.allowed_mines else 'Assigned only'}"
                )

        # 3. Canonicalize all authorized mine targets to database primary keys
        target_mines = [self.CANONICAL_MINES_MAP.get(m.upper(), m.upper()) for m in target_mines]
        target_mines = list(dict.fromkeys(target_mines))

        # 4. Scoped Structured Data Gathering (Deterministic)
        all_annual_prod: List[Dict[str, Any]] = []
        all_dispatch: List[Dict[str, Any]] = []
        all_issues: List[Dict[str, Any]] = []
        all_inspections: List[Dict[str, Any]] = []
        all_quality: List[Dict[str, Any]] = []
        mine_overviews: List[Dict[str, Any]] = []

        for m in target_mines:
            # Query mine metadata
            mine_obj = db.scalar(select(Mine).where(Mine.mine_code == m))
            if mine_obj:
                mine_overviews.append({
                    "mine_code": mine_obj.mine_code,
                    "mine_name": mine_obj.mine_name,
                    "subsidiary_id": mine_obj.subsidiary_id,
                    "mine_type": mine_obj.mine_type,
                    "coal_type": mine_obj.coal_type,
                    "location": mine_obj.location
                })

            # Annual Production
            prod_records = DeterministicQueryService.get_annual_production(
                db=db, scope=scope, mine_code=m, start_year=start_year, end_year=end_year
            )
            for p in prod_records:
                all_annual_prod.append({
                    "mine_code": p.mine_code,
                    "year": p.year,
                    "target_mt": float(p.target_mt or 0.0),
                    "actual_production_mt": float(p.actual_production_mt or 0.0),
                    "variance_mt": float(p.variance_mt or 0.0) if p.variance_mt is not None else None,
                    "achievement_pct": float(p.achievement_pct or 0.0) if p.achievement_pct is not None else None,
                    "dispatch_mt": float(p.dispatch_mt or 0.0) if p.dispatch_mt is not None else None,
                    "face_availability_pct": float(p.equipment_or_face_availability_pct or 0.0) if p.equipment_or_face_availability_pct is not None else None,
                })

            # Dispatch Records
            disp_records = DeterministicQueryService.get_dispatch_summary(
                db=db, scope=scope, mine_code=m, year=None
            )
            for d in disp_records:
                if start_year <= d.year <= end_year:
                    all_dispatch.append({
                        "mine_code": d.mine_code,
                        "year": d.year,
                        "dispatch_mt": float(d.dispatch_mt or 0.0),
                        "gap_mt": float(d.production_dispatch_gap_mt or 0.0),
                        "mode": d.mode,
                        "logistics_status": d.logistics_status,
                    })

            # Mining issues (if geology/issues or full report)
            issues = DeterministicQueryService.get_mining_issues(db=db, scope=scope, mine_code=m)
            for iss in issues:
                all_issues.append({
                    "mine_code": iss.mine_code,
                    "year": iss.year,
                    "issue_category": iss.issue_category,
                    "observed_issue": iss.observed_issue,
                    "operational_impact": iss.operational_impact,
                    "corrective_action": iss.corrective_action
                })

            # Statutory inspections
            insps = DeterministicQueryService.get_inspections(db=db, scope=scope, mine_code=m)
            for ins in insps:
                all_inspections.append({
                    "mine_code": ins.mine_code,
                    "year": ins.year,
                    "inspection_focus": ins.inspection_focus,
                    "status": ins.status,
                    "observation": ins.observation,
                    "responsible_officer": ins.responsible_officer
                })

        # 4. Multi-Mine Comparisons (if applicable)
        mine_comparisons: List[Dict[str, Any]] = []
        if len(target_mines) > 1:
            comparison_year = end_year or 2025
            for m in target_mines:
                m_prod = [p for p in all_annual_prod if p["mine_code"] == m and p["year"] == comparison_year]
                if m_prod:
                    p0 = m_prod[0]
                    mine_comparisons.append({
                        "mine_code": m,
                        "subsidiary_name": "CMPDI/CIL",
                        "year": comparison_year,
                        "actual_production_mt": p0["actual_production_mt"],
                        "target_production_mt": p0["target_mt"],
                    })

        # 5. Validation Engine & Conflict Detection
        conflicts: List[Dict[str, Any]] = []
        data_gaps: List[str] = []
        validation_status = "VERIFIED"

        # Check for registered conflicts matching target mines
        for m in target_mines:
            conf_records = list(db.scalars(
                select(Conflict).where(Conflict.mine_code == m)
            ).all())
            for c in conf_records:
                conflicts.append({
                    "conflict_id": c.conflict_id,
                    "mine_code": c.mine_code,
                    "metric_or_topic": c.metric_or_topic,
                    "source_a_type": c.source_a_type,
                    "source_a_reference": c.source_a_reference,
                    "source_a_value": c.source_a_value,
                    "source_b_type": c.source_b_type,
                    "source_b_reference": c.source_b_reference,
                    "source_b_value": c.source_b_value,
                    "status": c.status,
                    "resolution_policy": c.resolution_policy or "Independent engineering verification required"
                })

        if conflicts:
            validation_status = "CONFLICT"

        # Check data gaps
        if not all_annual_prod:
            data_gaps.append("Data unavailable for the requested scope/period: No annual production records found.")
        if not all_dispatch:
            data_gaps.append("Dispatch performance data unavailable for selected mines/years.")

        # 6. Evidence Engine Citations
        evidence_citations: List[Dict[str, Any]] = []
        ev_items = EvidenceEngine.from_structured_records(
            records=all_annual_prod[:5],
            domain="production_annual"
        )
        for ev in ev_items:
            evidence_citations.append({
                "evidence_id": ev.evidence_id,
                "source_type": ev.source_type,
                "source_name": ev.source_name,
                "record_id": ev.record_id,
                "source_text": ev.snippet,
                "citation": ev.citation
            })

        # 7. Render Charts (Headless Matplotlib)
        chart_paths: Dict[str, str] = {}
        report_id_str = f"REP-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"

        if request.include_charts:
            if len(target_mines) == 1:
                trend_file = f"{report_id_str}_trend.png"
                trend_path = self.chart_generator.generate_production_trend_chart(
                    production_data=all_annual_prod,
                    mine_code=target_mines[0],
                    output_filename=trend_file
                )
                if trend_path:
                    chart_paths["production_trend"] = trend_path

                if all_dispatch:
                    disp_file = f"{report_id_str}_dispatch.png"
                    disp_path = self.chart_generator.generate_dispatch_trend_chart(
                        dispatch_data=all_dispatch,
                        mine_code=target_mines[0],
                        output_filename=disp_file
                    )
                    if disp_path:
                        chart_paths["dispatch_breakdown"] = disp_path
            elif len(target_mines) > 1 and mine_comparisons:
                comp_file = f"{report_id_str}_comparison.png"
                comp_path = self.chart_generator.generate_comparison_chart(
                    comparisons=mine_comparisons,
                    output_filename=comp_file,
                    year=end_year
                )
                if comp_path:
                    chart_paths["mine_comparison"] = comp_path

        # 8. Grounded Executive Summary via Qwen
        executive_summary = self._synthesize_executive_summary(
            target_mines=target_mines,
            report_type=report_type,
            reporting_period=f"FY{start_year}-FY{end_year}",
            annual_prod=all_annual_prod,
            conflicts=conflicts,
            data_gaps=data_gaps,
            comparisons=mine_comparisons,
            query=request.query or ""
        )

        # 9. Assemble Report Data Package
        period_str = f"FY{start_year} – FY{end_year}" if start_year != end_year else f"FY{start_year}"
        title_prefix = "Comprehensive Operational Performance Report"
        if report_type == "COMPARISON":
            title_prefix = "Comparative Operational Analysis"
        elif report_type == "CONFLICT":
            title_prefix = "Operational Discrepancy & Conflict Audit Report"
        elif report_type == "GEOLOGY_ISSUES":
            title_prefix = "Geological Assessment & Mining Issues Report"

        report_title = f"{title_prefix} — {', '.join(target_mines)} ({period_str})"

        pkg = ReportDataPackage(
            report_id=report_id_str,
            report_title=report_title,
            report_type=report_type,
            mines=target_mines,
            reporting_period=period_str,
            generated_at=datetime.now().strftime("%d-%b-%Y %H:%M:%S IST"),
            requested_by=user.user_id,
            role=user.role,
            department=user.department,
            executive_summary=executive_summary,
            mine_overviews=mine_overviews,
            production_annual=all_annual_prod,
            dispatch_records=all_dispatch,
            mining_issues=all_issues[:10],
            inspections=all_inspections[:10],
            mine_comparisons=mine_comparisons,
            conflicts=conflicts,
            data_gaps=data_gaps,
            evidence_citations=evidence_citations,
            chart_paths=chart_paths
        )

        # 10. Generate DOCX & PDF
        docx_filename = f"{report_id_str}.docx"
        pdf_filename = f"{report_id_str}.pdf"

        self.docx_builder.build_report(pkg, docx_filename)
        self.pdf_builder.build_report(pkg, pdf_filename)

        latency_ms = round((time.time() - start_time) * 1000, 2)

        # 11. Database Persistence
        generated_rep = GeneratedReport(
            report_id=report_id_str,
            user_id=user.user_id,
            report_title=report_title,
            report_type=report_type,
            mine_code=target_mines[0] if len(target_mines) == 1 else None,
            mines_covered=target_mines,
            reporting_period=period_str,
            docx_filename=docx_filename,
            pdf_filename=pdf_filename,
            evidence_count=len(evidence_citations),
            conflict_count=len(conflicts),
            data_gap_count=len(data_gaps),
            validation_status=validation_status,
            scope_snapshot={
                "user_id": user.user_id,
                "role": user.role,
                "clearance": user.clearance_level,
                "allowed_mines": list(scope.allowed_mines) if scope.allowed_mines is not None else "ALL"
            },
            generation_latency_ms=latency_ms,
            status="GENERATED"
        )
        db.add(generated_rep)
        try:
            db.commit()
            db.refresh(generated_rep)
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to persist generated report metadata: {e}")
            raise

        tot_target = sum(float(p.get("target_mt") or 0.0) for p in all_annual_prod)
        tot_actual = sum(float(p.get("actual_production_mt") or 0.0) for p in all_annual_prod)
        avg_ach = (tot_actual / tot_target * 100) if tot_target > 0 else 0.0
        tot_disp = sum(float(d.get("dispatch_mt") or 0.0) for d in all_dispatch)

        # Build key indicators strictly from retrieved data — no fabricated values
        key_indicators = [
            {"metric": "Raw Coal Production", "value": f"{tot_actual:.2f} MT", "source": "Production Database"},
            {"metric": "Production Target", "value": f"{tot_target:.2f} MT", "source": "Annual Plan Register"},
        ]
        if tot_target > 0:
            key_indicators.append({"metric": "Target Achievement", "value": f"{avg_ach:.1f}%", "source": "Calculated (Actual / Target)"})
        else:
            key_indicators.append({"metric": "Target Achievement", "value": "Insufficient authorized data", "source": "Calculated Metric"})
        if tot_disp > 0:
            key_indicators.append({"metric": "Total Dispatch", "value": f"{tot_disp:.2f} MT", "source": "Logistics Register"})
        else:
            key_indicators.append({"metric": "Total Dispatch", "value": "Insufficient authorized data", "source": "Logistics Register"})
        key_indicators.append({"metric": "Data Integrity Status", "value": validation_status, "source": "Pre-Retrieval Governance"})

        return ReportMetadataResponse(
            report_id=report_id_str,
            report_title=report_title,
            report_type=report_type,
            mine_code=target_mines[0] if len(target_mines) == 1 else None,
            mines_covered=target_mines,
            reporting_period=period_str,
            generated_at=pkg.generated_at,
            requested_by=user.user_id,
            status="GENERATED",
            output_formats=["DOCX", "PDF"],
            docx_download_url=f"/api/v1/reports/{report_id_str}/download/docx",
            pdf_download_url=f"/api/v1/reports/{report_id_str}/download/pdf",
            evidence_count=len(evidence_citations),
            conflict_count=len(conflicts),
            data_gap_count=len(data_gaps),
            validation_status=validation_status,
            generation_latency_ms=latency_ms,
            executive_summary=executive_summary,
            production_annual=all_annual_prod,
            evidence_citations=evidence_citations,
            key_indicators=key_indicators
        )

    def _synthesize_executive_summary(
        self,
        target_mines: List[str],
        report_type: str,
        reporting_period: str,
        annual_prod: List[Dict[str, Any]],
        conflicts: List[Dict[str, Any]],
        data_gaps: List[str],
        comparisons: List[Dict[str, Any]],
        query: str
    ) -> str:
        """
        Invokes local Qwen3-8B reasoner to synthesize a clean, grounded narrative.
        Strictly provides only validated metrics and forbids hallucination.
        """
        # Format structured bullet points for the LLM
        fact_lines = []
        for p in annual_prod:
            act = p.get("actual_production_mt") or p.get("actual_raw_coal_production_mt") or 0.0
            tgt = p.get("target_mt") or p.get("target_raw_coal_production_mt") or 0.0
            ach = f"{(act / tgt * 100):.1f}%" if tgt > 0 else "N/A"
            fact_lines.append(
                f"- Mine {p['mine_code']} (FY{p['year']}): Actual={act:.2f} MT, Target={tgt:.2f} MT (Achievement: {ach})"
            )

        conflict_lines = []
        for c in conflicts:
            conflict_lines.append(
                f"- Conflict {c['conflict_id']}: {c['source_a_type']} ({c['source_a_value']}) vs {c['source_b_type']} ({c['source_b_value']}). Notice: Requires human review."
            )

        gap_lines = [f"- {g}" for g in data_gaps]

        user_content = f"""You are generating an Executive Summary for a formal board/management report.
Target Mines: {', '.join(target_mines)}
Reporting Period: {reporting_period}
Report Classification: {report_type}
User Query: {query or 'General performance synthesis'}

<operational_facts>
{chr(10).join(fact_lines) if fact_lines else 'No historical production data available.'}
</operational_facts>

<detected_conflicts>
{chr(10).join(conflict_lines) if conflict_lines else 'No data conflicts recorded.'}
</detected_conflicts>

<data_gaps>
{chr(10).join(gap_lines) if gap_lines else 'No critical data gaps.'}
</data_gaps>

INSTRUCTIONS:
1. Provide a concise, professional executive narrative (2-3 paragraphs max).
2. Use ONLY the figures provided in <operational_facts>. Do not invent or recalculate any numbers.
3. If <detected_conflicts> contains any conflict, you MUST explicitly state that a discrepancy was identified between official registers and requires human engineering verification.
4. If <data_gaps> contains missing items, briefly highlight them.
5. Do NOT output <think> tags, markdown code fences, or conversational greetings.
"""
        try:
            summary = self.qwen_client.generate_grounded_answer(
                query=f"Generate executive summary for {report_type} report covering {', '.join(target_mines)} ({reporting_period}). Query: {query}",
                route="REPORT",
                facts=annual_prod,
                analytics={"mine_comparisons": comparisons} if comparisons else None,
                evidence_items=[],
                validation_status="CONFLICT" if conflicts else "VERIFIED",
                conflicts=conflicts,
                data_gaps=data_gaps,
                max_tokens=150,
            )
            clean_summary = sanitize_llm_output(summary)
            if clean_summary and len(clean_summary) > 20:
                return clean_summary
        except Exception as e:
            logger.warning(f"Local LLM executive summary synthesis unavailable: {e}. Using deterministic synthesis.")

        # Fallback deterministic summary if LLM service is offline
        lines = [
            f"This operational report compiles verified performance records for {', '.join(target_mines)} during {reporting_period}."
        ]
        if annual_prod:
            latest = annual_prod[-1]
            lines.append(
                f"For {latest.get('mine_code')} in FY{latest.get('year')}, actual production reached "
                f"{float(latest.get('actual_production_mt') or latest.get('actual_raw_coal_production_mt') or 0.0):.2f} MT against a target of "
                f"{float(latest.get('target_mt') or latest.get('target_raw_coal_production_mt') or 0.0):.2f} MT."
            )
        if conflicts:
            lines.append(
                f"NOTICE: {len(conflicts)} data conflict(s) were flagged in this scope (including {conflicts[0]['conflict_id']}). "
                f"Per CMPDI governance rules, human verification is required."
            )
        return " ".join(lines)

    def get_report_file(
        self,
        db: Session,
        user: UserContext,
        report_id: str,
        fmt: str,
        scope: Optional[AuthorizedScope] = None,
    ) -> Tuple[str, str]:
        """
        Retrieves generated report file with strict authorization and path traversal defenses.
        Returns: (absolute_file_path, download_media_type)
        """
        if scope is None:
            scope = AuthorizationService.get_authorized_scope(user)

        report = db.scalar(select(GeneratedReport).where(GeneratedReport.report_id == report_id))
        if not report:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Report '{report_id}' not found."
            )

        # 1. Scope / Authorization Verification for Download
        mines_covered = report.mines_covered or []
        for m in mines_covered:
            if not scope.is_mine_permitted(m):
                logger.warning(
                    f"SECURITY DENIAL: User '{user.user_id}' attempted to download unauthorized report '{report_id}' covering '{m}'."
                )
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Access Denied: You are not authorized to access reports covering mine '{m}'."
                )

        # 2. Format Resolution
        norm_fmt = fmt.lower().strip()
        if norm_fmt in ["docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"]:
            filename = report.docx_filename
            media_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        elif norm_fmt in ["pdf", "application/pdf"]:
            filename = report.pdf_filename
            media_type = "application/pdf"
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported format '{fmt}'. Must be 'docx' or 'pdf'."
            )

        if not filename:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Report format '{fmt}' not generated for report '{report_id}'."
            )

        # 3. Path Traversal Defense
        clean_basename = os.path.basename(filename)
        resolved_path = os.path.abspath(os.path.join(self.REPORTS_DIR, clean_basename))
        expected_dir = os.path.abspath(self.REPORTS_DIR)

        if not resolved_path.startswith(expected_dir) or not os.path.exists(resolved_path):
            logger.error(f"Security Alert: Attempted path traversal or missing report file: {resolved_path}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Report file not found or invalid directory path."
            )

        return resolved_path, media_type
