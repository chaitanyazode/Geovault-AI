"""
GeoVault AI - Production Unified AI Orchestrator
Coordinates the complete lifecycle:
Identity → Authorization → Query Router → Scoped Retrieval →
Evidence Engine → Validation Engine → Conflict/Data-gap Handling →
Controlled Qwen Context → Grounded Synthesis → Non-leaking Audit Logging.
"""

import time
from typing import Dict, Any, List, Optional, Tuple
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.security.context import UserContext, AuthorizedScope
from app.security.service import AuthorizationService
from app.security.audit import AuditLogger
from app.schemas.query import GroundedQueryResponse, EvidenceItem, ConflictItem, DataGap
from app.ai.query_router import DeterministicQueryRouter, RoutedQuery
from app.ai.qwen_reasoner import QwenReasonerClient
from app.rag.retriever import ScopedVectorRetriever
from app.services.query_service import DeterministicQueryService
from app.services.evidence_engine import EvidenceEngine
from app.services.validation_engine import ValidationEngine
from app.analytics.engine import AnalyticsEngine


class UnifiedAIOrchestrator:
    """
    Production-grade enterprise AI orchestrator.
    Strictly follows: Identity -> Authorization -> Scope -> Retrieval -> Evidence -> Validation -> Qwen Reasoning.
    """

    ORCHESTRATOR_VERSION = "5.3-prod"

    def __init__(self, db: Session, user: UserContext, scope: AuthorizedScope):
        self.db = db
        self.user = user
        self.scope = scope
        self.reasoner = QwenReasonerClient()

    def orchestrate(
        self,
        query: str,
        target_mine_hint: Optional[str] = None,
        target_year_hint: Optional[int] = None,
        top_k: int = 5,
    ) -> GroundedQueryResponse:
        """
        Executes end-to-end natural language query orchestration with complete
        authorization, retrieval scoping, evidence grounding, and latency instrumentation.
        """
        t_start = time.perf_counter()

        # 1. Deterministic Query Routing
        routed: RoutedQuery = DeterministicQueryRouter.route_query(query)
        target_mine = target_mine_hint or routed.target_mine
        target_year = target_year_hint or routed.target_year
        start_year = routed.start_year
        end_year = routed.end_year
        route = routed.route

        # 2. Authorization Pre-Filter Verification
        if target_mine and not self.scope.is_mine_permitted(target_mine):
            AuditLogger.log_query(
                db=self.db,
                user_id=self.user.user_id,
                question=query,
                route_selected=route,
                scope=self.scope,
                evidence_count=0,
                evidence_status="INSUFFICIENT_AUTHORIZED_DATA",
                response_summary=f"Access Denied: Mine '{target_mine}' outside authorized scope.",
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access Denied: User '{self.user.user_id}' is not authorized to access data for mine '{target_mine}'.",
            )

        # Check compared mines authorization
        if routed.compared_mines:
            for m in routed.compared_mines:
                if not self.scope.is_mine_permitted(m):
                    AuditLogger.log_query(
                        db=self.db,
                        user_id=self.user.user_id,
                        question=query,
                        route_selected=route,
                        scope=self.scope,
                        evidence_count=0,
                        evidence_status="INSUFFICIENT_AUTHORIZED_DATA",
                        response_summary=f"Access Denied: Compared mine '{m}' outside authorized scope.",
                    )
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail=f"Access Denied: User '{self.user.user_id}' is not authorized to access mine '{m}'.",
                    )

        facts: List[Dict[str, Any]] = []
        evidence_items: List[EvidenceItem] = []
        analytics_dict: Optional[Dict[str, Any]] = None

        # 3. Route Execution
        if route == "SQL":
            facts, evidence_items = self._execute_sql_route(target_mine, target_year, routed.domain)

        elif route == "ANALYTICS":
            facts, evidence_items, analytics_dict = self._execute_analytics_route(
                target_mine=target_mine,
                compared_mines=routed.compared_mines,
                start_year=start_year,
                end_year=end_year,
            )

        elif route == "RAG":
            evidence_items = self._execute_rag_route(query, target_mine, top_k=top_k)

        elif route == "SPATIAL":
            facts, evidence_items, analytics_dict = self._execute_spatial_route(query, target_mine)

        elif route == "GEOLOGY":
            facts, evidence_items, analytics_dict = self._execute_geology_route(query, target_mine)

        elif route == "HYBRID":
            facts, evidence_items, analytics_dict = self._execute_hybrid_route(
                query=query,
                target_mine=target_mine,
                target_year=target_year,
                start_year=start_year,
                end_year=end_year,
                top_k=top_k,
            )

        elif route == "TOPIC":
            from app.services.topic_service import TopicAnalysisService
            from app.schemas.topics import TopicAnalysisRequest

            topic_req = TopicAnalysisRequest(
                mine_code=target_mine,
                department=routed.domain if routed.domain in ["Geology", "Mining", "Safety", "Transportation"] else None,
                year=target_year,
                generate_wordcloud=True,
            )
            topic_res = TopicAnalysisService.analyze_topics(self.db, self.scope, topic_req)

            facts = [
                {
                    "topic_id": t.topic_id,
                    "title": t.title,
                    "top_keywords": t.top_keywords,
                    "chunk_count": t.document_chunk_count,
                    "mines": t.mines_covered,
                }
                for t in topic_res.topics
            ]
            analytics_dict = {
                "total_documents_analyzed": topic_res.total_documents_analyzed,
                "total_chunks_analyzed": topic_res.total_chunks_analyzed,
                "top_keywords": [k.keyword for k in topic_res.keywords[:10]],
                "wordcloud_url": topic_res.wordcloud_url,
            }
            chunks = TopicAnalysisService.get_scoped_chunks(self.db, self.scope, mine_code=target_mine, year=target_year)
            evidence_items = EvidenceEngine.from_document_chunks(chunks[:top_k])

        report_res = None
        if route == "REPORT":
            from app.services.report_service import ReportGenerationService
            from app.schemas.reports import ReportGenerateRequest

            rep_svc = ReportGenerationService()
            report_res = rep_svc.generate_report(
                db=self.db,
                user=self.user,
                request=ReportGenerateRequest(
                    query=query,
                    mine_code=target_mine,
                    compared_mines=routed.compared_mines,
                    start_year=start_year,
                    end_year=end_year,
                ),
            )
            facts = [
                {
                    "report_id": report_res.report_id,
                    "title": report_res.report_title,
                    "period": report_res.reporting_period,
                    "status": report_res.status,
                    "mines_covered": report_res.mines_covered,
                }
            ]
            analytics_dict = {
                "report_id": report_res.report_id,
                "report_title": report_res.report_title,
                "docx_download_url": report_res.docx_download_url,
                "pdf_download_url": report_res.pdf_download_url,
                "output_formats": report_res.output_formats,
                "generation_latency_ms": getattr(report_res, "generation_latency_ms", 0.0),
            }

        # 4. Deterministic Validation & Conflict Surfacing
        val_result = ValidationEngine.validate_query(
            db=self.db,
            scope=self.scope,
            records=facts,
            domain=routed.domain or "production_annual",
            mine_code=target_mine,
            year=target_year,
        )

        conflicts = val_result.conflicts_detected
        data_gaps = val_result.data_gaps
        validation_status = val_result.evidence_status

        # Confidence status resolution
        if validation_status == "CONFLICT":
            confidence_status = "CONFLICT_DETECTED"
        elif validation_status == "INSUFFICIENT_AUTHORIZED_DATA":
            confidence_status = "INSUFFICIENT_DATA"
        elif validation_status == "PARTIAL":
            confidence_status = "PARTIAL_GROUNDING"
        else:
            confidence_status = "HIGH"

        # 5. Grounded Qwen Local Reasoning (with latency tracking)
        if report_res and report_res.executive_summary:
            summary = report_res.executive_summary
            detailed_answer = (
                f"### Report Details\n"
                f"**Report Title**: {report_res.report_title}\n"
                f"**Reporting Period**: {report_res.reporting_period}\n"
                f"**Mines Covered**: {', '.join(report_res.mines_covered)}\n\n"
                f"### Download Artifacts\n"
                f"- PDF Document: `{report_res.pdf_download_url}`\n"
                f"- Word Document: `{report_res.docx_download_url}`\n\n"
                f"### Evidence & Provenance\n"
                f"Report metrics are synthesized from the GeoVault AI synthetic demonstration dataset."
            )
            answer = f"SUMMARY:\n{summary}\n\nDETAILED ANSWER:\n{detailed_answer}"
            llm_latency_ms = getattr(report_res, "generation_latency_ms", 0.0)
        else:
            answer, llm_latency_ms = self.reasoner.generate_grounded_answer(
                query=query,
                route=route,
                facts=facts,
                analytics=analytics_dict,
                evidence_items=evidence_items,
                validation_status=validation_status,
                conflicts=conflicts,
                data_gaps=data_gaps,
                return_latency=True,
            )
            summary, detailed_answer = self._parse_summary_and_detailed(answer)

        total_latency_ms = round((time.perf_counter() - t_start) * 1000, 2)

        # 6. Non-Leaking Citations List
        source_refs = [ev.citation for ev in evidence_items if ev.citation]

        # 7. Non-Leaking Audit Logging
        AuditLogger.log_query(
            db=self.db,
            user_id=self.user.user_id,
            question=query,
            route_selected=route,
            scope=self.scope,
            evidence_count=len(evidence_items),
            evidence_status=validation_status,
            response_summary=summary[:200] if summary else answer[:200],
        )

        structured_results_payload = None
        if facts or analytics_dict:
            structured_results_payload = {
                "facts": facts,
                "analytics": analytics_dict,
            }

        processing_meta = {
            "orchestrator_version": self.ORCHESTRATOR_VERSION,
            "route_selected": route,
            "routing_rationale": routed.rationale,
            "llm_latency_ms": llm_latency_ms,
            "orchestration_latency_ms": total_latency_ms,
            "total_latency_ms": total_latency_ms,
            "prompt_injection_defense": "XML_FENCED_DATA_BOUNDARY",
            "model_identifier": "Qwen3-8B-Q4_K_M.gguf",
            "evidence_count": len(evidence_items),
            "conflicts_count": len(conflicts),
            "data_gaps_count": len(data_gaps),
        }
        if analytics_dict and analytics_dict.get("wordcloud_url"):
            processing_meta["wordcloud_url"] = analytics_dict["wordcloud_url"]
        if analytics_dict and analytics_dict.get("pdf_download_url"):
            processing_meta["report_downloads"] = {
                "pdf": analytics_dict["pdf_download_url"],
                "docx": analytics_dict["docx_download_url"],
            }

        return GroundedQueryResponse(
            query=query,
            query_type=route,
            summary=summary,
            detailed_answer=detailed_answer,
            answer=answer,
            structured_results=structured_results_payload,
            evidence=evidence_items,
            conflicts=conflicts,
            data_gaps=data_gaps,
            validation_status=validation_status,
            confidence_status=confidence_status,
            source_references=source_refs,
            authorized_scope_applied=self.scope.to_dict(),
            processing_metadata=processing_meta,
        )

    @staticmethod
    def _parse_summary_and_detailed(raw_text: str) -> Tuple[str, str]:
        """
        Extracts clean Summary and Detailed Answer sections from synthesized answer text.
        """
        import re

        if not raw_text:
            return "", ""

        text = raw_text.strip()

        # 1. Explicit SUMMARY and DETAILED ANSWER blocks
        match_both = re.search(
            r"SUMMARY:\s*(.*?)\s*DETAILED ANSWER:\s*(.*)",
            text,
            re.DOTALL | re.IGNORECASE,
        )
        if match_both:
            summary = match_both.group(1).strip()
            detailed = match_both.group(2).strip()
            return summary, detailed

        # 2. Heading-based splitting (###)
        parts = text.split("\n###", 1)
        if len(parts) == 2 and len(parts[0].strip()) > 20:
            summary = re.sub(r"^SUMMARY:\s*", "", parts[0].strip(), flags=re.IGNORECASE).strip()
            detailed = "###" + parts[1].strip()
            detailed = re.sub(r"^DETAILED ANSWER:\s*", "", detailed, flags=re.IGNORECASE).strip()
            return summary, detailed

        # 3. Paragraph fallback: first paragraph is summary, rest is detailed
        paras = [p.strip() for p in text.split("\n\n") if p.strip()]
        if len(paras) >= 2:
            summary = re.sub(r"^SUMMARY:\s*", "", paras[0], flags=re.IGNORECASE).strip()
            detailed = re.sub(r"^DETAILED ANSWER:\s*", "", "\n\n".join(paras[1:]), flags=re.IGNORECASE).strip()
            return summary, detailed
        elif len(paras) == 1:
            clean = re.sub(r"^SUMMARY:\s*", "", paras[0], flags=re.IGNORECASE).strip()
            return clean, clean

        return text, text

    def _execute_sql_route(
        self, target_mine: Optional[str], target_year: Optional[int], domain_hint: Optional[str]
    ) -> Tuple[List[Dict[str, Any]], List[EvidenceItem]]:
        """Retrieves structured operational records and generates evidence."""
        domain = domain_hint or "production_annual"
        records = []
        facts = []
        evidence = []

        fy_str = f"{target_year-1}-{str(target_year)[2:]}" if target_year else None

        if domain == "production_annual":
            records = DeterministicQueryService.get_annual_production(
                self.db, self.scope, mine_code=target_mine, year=target_year
            )
            facts = [{c.name: getattr(r, c.name) for c in r.__table__.columns} for r in records]
            evidence = EvidenceEngine.from_structured_records(records, domain)
        elif domain == "equipment_fleet":
            records = DeterministicQueryService.get_equipment_fleet(
                self.db, self.scope, mine_code=target_mine, financial_year=fy_str
            )
            facts = [{c.name: getattr(r, c.name) for c in r.__table__.columns} for r in records]
            evidence = EvidenceEngine.from_structured_records(records, domain)
        elif domain == "safety_records":
            records = DeterministicQueryService.get_safety_records(
                self.db, self.scope, mine_code=target_mine, financial_year=fy_str
            )
            facts = [{c.name: getattr(r, c.name) for c in r.__table__.columns} for r in records]
            evidence = EvidenceEngine.from_structured_records(records, domain)
        elif domain == "environmental_records":
            records = DeterministicQueryService.get_environmental_records(
                self.db, self.scope, mine_code=target_mine, financial_year=fy_str
            )
            facts = [{c.name: getattr(r, c.name) for c in r.__table__.columns} for r in records]
            evidence = EvidenceEngine.from_structured_records(records, domain)
        elif domain == "coal_seams":
            records = DeterministicQueryService.get_coal_seams(
                self.db, self.scope, mine_code=target_mine
            )
            facts = [{c.name: getattr(r, c.name) for c in r.__table__.columns} for r in records]
            evidence = EvidenceEngine.from_structured_records(records, domain)
        elif domain == "geotechnical_zones":
            records = DeterministicQueryService.get_geotechnical_zones(
                self.db, self.scope, mine_code=target_mine
            )
            facts = [{c.name: getattr(r, c.name) for c in r.__table__.columns} for r in records]
            evidence = EvidenceEngine.from_structured_records(records, domain)
        elif domain == "mining_issue_log":
            records = DeterministicQueryService.get_mining_issues(
                self.db, self.scope, mine_code=target_mine, year=target_year
            )
            facts = [{c.name: getattr(r, c.name) for c in r.__table__.columns} for r in records]
            evidence = EvidenceEngine.from_structured_records(records, domain)
        elif domain == "dispatch_summary":
            records = DeterministicQueryService.get_dispatch_summary(
                self.db, self.scope, mine_code=target_mine, year=target_year
            )
            facts = [{c.name: getattr(r, c.name) for c in r.__table__.columns} for r in records]
            evidence = EvidenceEngine.from_structured_records(records, domain)
        elif domain == "coal_quality":
            records = DeterministicQueryService.get_coal_quality(
                self.db, self.scope, mine_code=target_mine, year=target_year
            )
            facts = [{c.name: getattr(r, c.name) for c in r.__table__.columns} for r in records]
            evidence = EvidenceEngine.from_structured_records(records, domain)
        elif domain == "geological_units":
            records = DeterministicQueryService.get_geological_units(
                self.db, self.scope, mine_code=target_mine
            )
            facts = [{c.name: getattr(r, c.name) for c in r.__table__.columns} for r in records]
            evidence = EvidenceEngine.from_structured_records(records, domain)
        elif domain == "inspection_register":
            records = DeterministicQueryService.get_inspections(
                self.db, self.scope, mine_code=target_mine, year=target_year
            )
            facts = [{c.name: getattr(r, c.name) for c in r.__table__.columns} for r in records]
            evidence = EvidenceEngine.from_structured_records(records, domain)
        elif domain == "conflict_check":
            facts = []
            evidence = []
        else:
            records = DeterministicQueryService.get_annual_production(
                self.db, self.scope, mine_code=target_mine, year=target_year
            )
            facts = [{c.name: getattr(r, c.name) for c in r.__table__.columns} for r in records]
            evidence = EvidenceEngine.from_structured_records(records, "production_annual")

        return facts, evidence

    def _execute_spatial_route(
        self,
        query: str,
        target_mine: Optional[str] = None,
    ) -> Tuple[List[Dict[str, Any]], List[EvidenceItem], Optional[Dict[str, Any]]]:
        """Executes PostGIS spatial analysis queries with strict pre-retrieval scope enforcement."""
        from app.services.spatial_service import SpatialIntelligenceService
        import re

        lowered = query.lower()
        facts: List[Dict[str, Any]] = []
        evidence_items: List[EvidenceItem] = []
        analytics: Dict[str, Any] = {}

        if "event" in lowered or "near" in lowered or "within" in lowered:
            dist = 500.0
            m = re.search(r"(\d+)\s*(?:m|meter|meters|metre|metres)", lowered)
            if m:
                dist = float(m.group(1))
            facts = SpatialIntelligenceService.query_boreholes_near_events(
                db=self.db,
                scope=self.scope,
                mine_code=target_mine,
                distance_meters=dist,
            )
            evidence_items = SpatialIntelligenceService.build_spatial_evidence(facts[:10], "spatial_boreholes")
            analytics = {
                "operation": "ST_DWithin",
                "distance_threshold_m": dist,
                "features_found": len(facts),
            }
        elif "intersect" in lowered or "seam" in lowered:
            seam_kw = None
            for sname in ["kusmunda", "gevra", "dipka", "nigahi", "dudhichua", "lower", "upper", "purewa"]:
                if sname in lowered:
                    seam_kw = sname.title()
                    break
            facts = SpatialIntelligenceService.query_boreholes_intersecting_seams(
                db=self.db,
                scope=self.scope,
                mine_code=target_mine,
                seam_id=seam_kw,
            )
            evidence_items = SpatialIntelligenceService.build_spatial_evidence(facts[:10], "spatial_coal_seam_belts")
            analytics = {
                "operation": "ST_Intersects",
                "seam_filter": seam_kw,
                "intersections_found": len(facts),
            }
        elif "risk" in lowered or "geotechnical" in lowered:
            facts = SpatialIntelligenceService.query_high_risk_geotechnical_zones(
                db=self.db,
                scope=self.scope,
                mine_code=target_mine,
                min_risk_level="HIGH",
            )
            evidence_items = SpatialIntelligenceService.build_spatial_evidence(facts[:10], "spatial_geotechnical_zones")
            analytics = {
                "operation": "ST_Area & High Risk Zones",
                "risk_class": "HIGH",
                "high_risk_zones_count": len(facts),
            }
        else:
            target_mine_code = target_mine or "GEVRA"
            facts = SpatialIntelligenceService.query_nearest_features(
                db=self.db,
                scope=self.scope,
                mine_code=target_mine_code,
            )
            evidence_items = SpatialIntelligenceService.build_spatial_evidence(facts[:10], "spatial_boreholes")
            analytics = {
                "operation": "ST_Distance",
                "nearest_pairs_count": len(facts),
            }

        return facts, evidence_items, analytics

    def _execute_geology_route(
        self,
        query: str,
        target_mine: Optional[str] = None,
    ) -> Tuple[List[Dict[str, Any]], List[EvidenceItem], Optional[Dict[str, Any]]]:
        """Executes structured geological queries across coal seams, boreholes, and geotechnical zones."""
        lowered = query.lower()
        facts: List[Dict[str, Any]] = []
        evidence_items: List[EvidenceItem] = []
        analytics: Dict[str, Any] = {}

        if "seam" in lowered:
            seams = DeterministicQueryService.get_coal_seams(self.db, self.scope, mine_code=target_mine)
            for s in seams:
                facts.append({
                    "mine_code": s.mine_code,
                    "seam_id": s.seam_id,
                    "avg_thickness_m": float(s.avg_thickness_m) if getattr(s, "avg_thickness_m", None) is not None else None,
                    "synthetic_dip_deg": float(s.synthetic_dip_deg) if getattr(s, "synthetic_dip_deg", None) is not None else None,
                    "synthetic_strike_deg": float(s.synthetic_strike_deg) if getattr(s, "synthetic_strike_deg", None) is not None else None,
                    "continuity": getattr(s, "continuity", None),
                    "quality_band": getattr(s, "quality_band", None),
                })
            evidence_items = [EvidenceEngine.from_structured_record(s, "coal_seams") for s in seams]
            if facts:
                th_vals = [f["avg_thickness_m"] for f in facts if f["avg_thickness_m"] is not None]
                analytics = {
                    "total_seams": len(facts),
                    "average_thickness_m": round(sum(th_vals)/len(th_vals), 2) if th_vals else None,
                }
        elif "borehole" in lowered or "drill" in lowered:
            facts = DeterministicQueryService.get_boreholes_and_intervals(self.db, self.scope, mine_code=target_mine)
            for b in facts[:10]:
                evidence_items.append(
                    EvidenceItem(
                        evidence_id=f"EV-BOREHOLE-{b['mine_code']}-{b['borehole_id']}",
                        source_type="STRUCTURED_RECORD",
                        source_name="boreholes_master",
                        record_id=b["borehole_id"],
                        mine_code=b["mine_code"],
                        department="Geology",
                        citation=f"Exploratory Drilling Master | {b['mine_code']} | {b['borehole_id']}",
                        snippet=f"Borehole {b['borehole_id']}: Depth {b['total_depth_m']}m, Seams: {', '.join(b['seams_intersected'])}",
                    )
                )
            analytics = {"total_boreholes": len(facts)}
        elif "geotechnical" in lowered or "zone" in lowered:
            zones = DeterministicQueryService.get_geotechnical_zones(self.db, self.scope, mine_code=target_mine)
            for z in zones:
                facts.append({
                    "zone_id": z.zone_id,
                    "mine_code": z.mine_code,
                    "zone_type": z.zone_type,
                    "risk_class": z.risk_class,
                    "basis": z.basis,
                })
            evidence_items = [EvidenceEngine.from_structured_record(z, "geotechnical_zones") for z in zones]
            analytics = {"total_zones": len(facts)}
        else:
            seams = DeterministicQueryService.get_coal_seams(self.db, self.scope, mine_code=target_mine)
            for s in seams:
                facts.append({"mine_code": s.mine_code, "seam_id": s.seam_id, "avg_thickness_m": float(s.avg_thickness_m) if s.avg_thickness_m else None})
            evidence_items = [EvidenceEngine.from_structured_record(s, "coal_seams") for s in seams]

        return facts, evidence_items, analytics

    def _execute_analytics_route(
        self,
        target_mine: Optional[str],
        compared_mines: List[str],
        start_year: Optional[int],
        end_year: Optional[int],
    ) -> Tuple[List[Dict[str, Any]], List[EvidenceItem], Dict[str, Any]]:
        """Executes comparisons, trends, or multi-year totals."""
        start_yr = start_year or 2021
        end_yr = end_year or 2025

        records = DeterministicQueryService.get_annual_production(
            self.db, self.scope, mine_code=target_mine, start_year=start_yr, end_year=end_yr
        )

        if compared_mines:
            records = [r for r in records if r.mine_code in compared_mines]

        facts = [{c.name: getattr(r, c.name) for c in r.__table__.columns} for r in records]
        evidence = EvidenceEngine.from_structured_records(records, "production_annual")

        analytics_dict: Dict[str, Any] = {
            "total_production_mt": AnalyticsEngine.compute_total(facts, "actual_production_mt"),
            "average_production_mt": AnalyticsEngine.compute_average(facts, "actual_production_mt"),
        }

        if compared_mines or not target_mine:
            all_mines = DeterministicQueryService.get_authorized_mines(self.db, self.scope)
            names_map = {m.mine_code: m.mine_name for m in all_mines}
            comparisons = AnalyticsEngine.compare_mines(facts, mine_names_map=names_map)
            analytics_dict["comparisons"] = [c.model_dump() for c in comparisons]
        else:
            trend = AnalyticsEngine.compute_trend_summary(facts)
            if trend:
                analytics_dict["trend"] = trend.model_dump()

        return facts, evidence, analytics_dict

    def _execute_rag_route(
        self, query: str, target_mine: Optional[str], top_k: int = 5
    ) -> List[EvidenceItem]:
        """Executes scoped semantic search via LlamaIndex ScopedVectorRetriever."""
        retriever = ScopedVectorRetriever(
            db=self.db,
            scope=self.scope,
            top_k=top_k,
            target_mine=target_mine,
        )
        _, evidence_items = retriever.retrieve_with_evidence(query)
        return evidence_items

    def _execute_hybrid_route(
        self,
        query: str,
        target_mine: Optional[str],
        target_year: Optional[int],
        start_year: Optional[int] = None,
        end_year: Optional[int] = None,
        top_k: int = 5,
    ) -> Tuple[List[Dict[str, Any]], List[EvidenceItem], Optional[Dict[str, Any]]]:
        """Combines scoped structured operational data, PostGIS spatial context, and scoped vector document evidence."""
        from app.services.spatial_service import SpatialIntelligenceService

        # 1. Structured operational metrics
        records = DeterministicQueryService.get_annual_production(
            self.db, self.scope, mine_code=target_mine, year=target_year, start_year=start_year, end_year=end_year
        )
        facts = [{c.name: getattr(r, c.name) for c in r.__table__.columns} for r in records]
        struct_ev = EvidenceEngine.from_structured_records(records, "production_annual")

        analytics_dict: Dict[str, Any] = {}
        if len(facts) >= 2:
            analytics_dict["total_production_mt"] = AnalyticsEngine.compute_total(facts, "actual_production_mt")
            trend = AnalyticsEngine.compute_trend_summary(facts)
            if trend:
                analytics_dict["trend"] = getattr(trend, "model_dump", lambda: None)()

        # 2. Vector document RAG evidence
        doc_ev = self._execute_rag_route(query, target_mine, top_k=top_k)

        # 3. PostGIS spatial context (if query involves spatial or geological impact)
        spatial_ev = []
        lowered = query.lower()
        if any(w in lowered for w in ["geolog", "fault", "strata", "zone", "water", "rain", "spatial", "event"]):
            if target_mine:
                events = SpatialIntelligenceService.query_boreholes_near_events(
                    db=self.db,
                    scope=self.scope,
                    mine_code=target_mine,
                    distance_meters=1000.0,
                )
                if events:
                    spatial_ev = SpatialIntelligenceService.build_spatial_evidence(events[:3], "spatial_geological_events")
                    analytics_dict["nearby_geological_events"] = len(events)

        combined_evidence = struct_ev + doc_ev + spatial_ev
        return facts, combined_evidence, analytics_dict

    @classmethod
    def execute_query(
        cls,
        db: Session,
        user_or_id: Any,
        query: str,
        target_mine_hint: Optional[str] = None,
        target_year_hint: Optional[int] = None,
        top_k: int = 5,
    ) -> GroundedQueryResponse:
        """
        Convenience classmethod for end-to-end query orchestration from user ID or UserContext.
        """
        if isinstance(user_or_id, UserContext):
            user = user_or_id
        else:
            user = AuthorizationService.resolve_user_context(db, str(user_or_id))
        scope = AuthorizationService.get_authorized_scope(user)
        orchestrator = cls(db=db, user=user, scope=scope)
        return orchestrator.orchestrate(
            query=query,
            target_mine_hint=target_mine_hint,
            target_year_hint=target_year_hint,
            top_k=top_k,
        )

