"""
GeoVault AI - Hybrid Intelligence Pipeline
Coordinates Deterministic Routing, Authorization Pre-Filtering,
Structured Querying, LlamaIndex Vector RAG, Validation & Grounded Qwen Reasoning.
"""

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


class HybridIntelligencePipeline:
    """
    Unified end-to-end intelligence orchestrator.
    Strictly follows: Identity -> Authorization -> Scope -> Retrieval -> Evidence -> Validation -> Qwen Reasoning.
    """

    def __init__(self, db: Session, user: UserContext, scope: AuthorizedScope):
        self.db = db
        self.user = user
        self.scope = scope
        self.reasoner = QwenReasonerClient()

    def process_query(
        self,
        query: str,
        target_mine_hint: Optional[str] = None,
        target_year_hint: Optional[int] = None,
        top_k: int = 5,
    ) -> GroundedQueryResponse:
        """
        Processes a natural language query end-to-end with complete authorization,
        retrieval, validation, and grounded reasoning.
        """
        # 1. Deterministic Query Routing
        routed: RoutedQuery = DeterministicQueryRouter.route_query(query)
        target_mine = target_mine_hint or routed.target_mine
        target_year = target_year_hint or routed.target_year
        start_year = routed.start_year
        end_year = routed.end_year
        route = routed.route

        # 2. Authorization Pre-Filter Validation
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

        elif route == "HYBRID":
            facts, evidence_items, analytics_dict = self._execute_hybrid_route(
                query=query,
                target_mine=target_mine,
                target_year=target_year,
                top_k=top_k,
            )

        elif route in ["TOPIC", "REPORT"]:
            # Baseline data collection for topics/reports
            facts, doc_ev = self._execute_hybrid_route(
                query=query, target_mine=target_mine, target_year=target_year, top_k=top_k
            )
            evidence_items = doc_ev

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

        # Confidence status mapping
        if validation_status == "CONFLICT":
            confidence_status = "CONFLICT_DETECTED"
        elif validation_status == "INSUFFICIENT_AUTHORIZED_DATA":
            confidence_status = "INSUFFICIENT_DATA"
        elif validation_status == "PARTIAL":
            confidence_status = "PARTIAL_GROUNDING"
        else:
            confidence_status = "HIGH"

        # 5. Grounded Qwen Reasoning
        answer = self.reasoner.generate_grounded_answer(
            query=query,
            route=route,
            facts=facts,
            analytics=analytics_dict,
            evidence_items=evidence_items,
            validation_status=validation_status,
            conflicts=conflicts,
            data_gaps=data_gaps,
        )

        # 6. Citations list
        source_refs = [ev.citation for ev in evidence_items if ev.citation]

        # 7. Audit Logging
        AuditLogger.log_query(
            db=self.db,
            user_id=self.user.user_id,
            question=query,
            route_selected=route,
            scope=self.scope,
            evidence_count=len(evidence_items),
            evidence_status=validation_status,
            response_summary=answer[:200],
        )

        structured_results_payload = None
        if facts or analytics_dict:
            structured_results_payload = {
                "facts": facts,
                "analytics": analytics_dict,
            }

        return GroundedQueryResponse(
            query=query,
            query_type=route,
            answer=answer,
            structured_results=structured_results_payload,
            evidence=evidence_items,
            conflicts=conflicts,
            data_gaps=data_gaps,
            validation_status=validation_status,
            confidence_status=confidence_status,
            source_references=source_refs,
            authorized_scope_applied=self.scope.to_dict(),
        )

    def _execute_sql_route(
        self, target_mine: Optional[str], target_year: Optional[int], domain_hint: Optional[str]
    ) -> Tuple[List[Dict[str, Any]], List[EvidenceItem]]:
        """Retrieves structured operational records and generates evidence."""
        domain = domain_hint or "production_annual"
        records = []

        if domain == "production_annual":
            records = DeterministicQueryService.get_annual_production(
                self.db, self.scope, mine_code=target_mine, year=target_year
            )
        elif domain == "dispatch_summary":
            records = DeterministicQueryService.get_dispatch_summary(
                self.db, self.scope, mine_code=target_mine, year=target_year
            )
        elif domain == "coal_quality":
            records = DeterministicQueryService.get_coal_quality(
                self.db, self.scope, mine_code=target_mine, year=target_year
            )
        elif domain == "geological_units":
            records = DeterministicQueryService.get_geological_units(
                self.db, self.scope, mine_code=target_mine
            )
        elif domain == "mining_issue_log":
            records = DeterministicQueryService.get_mining_issues(
                self.db, self.scope, mine_code=target_mine, year=target_year
            )
        elif domain == "inspection_register":
            records = DeterministicQueryService.get_inspections(
                self.db, self.scope, mine_code=target_mine, year=target_year
            )
        elif domain == "conflict_check":
            # Direct conflict query: return empty records; validation engine surfaces conflicts
            records = []
        else:
            records = DeterministicQueryService.get_annual_production(
                self.db, self.scope, mine_code=target_mine, year=target_year
            )

        facts = [{c.name: getattr(r, c.name) for c in r.__table__.columns} for r in records]
        evidence = EvidenceEngine.from_structured_records(records, domain)
        return facts, evidence

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

        # Check compared mines authorization
        if compared_mines:
            for m in compared_mines:
                if not self.scope.is_mine_permitted(m):
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail=f"Access Denied: User '{self.user.user_id}' is not authorized to compare mine '{m}'.",
                    )

        records = DeterministicQueryService.get_annual_production(
            self.db, self.scope, mine_code=target_mine, start_year=start_yr, end_year=end_yr
        )

        # Filter by compared mines if specified
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
        top_k: int = 5,
    ) -> Tuple[List[Dict[str, Any]], List[EvidenceItem], Optional[Dict[str, Any]]]:
        """Combines scoped structured production data with scoped vector document evidence."""
        # Structured part
        facts, struct_ev = self._execute_sql_route(target_mine, target_year, "production_annual")

        # Trend context if multiple records
        analytics_dict = None
        if len(facts) >= 2:
            analytics_dict = {
                "total_production_mt": AnalyticsEngine.compute_total(facts, "actual_production_mt"),
                "trend": getattr(AnalyticsEngine.compute_trend_summary(facts), "model_dump", lambda: None)(),
            }

        # Vector RAG part
        doc_ev = self._execute_rag_route(query, target_mine, top_k=top_k)

        # Merge evidence items (structured first, then document evidence)
        combined_evidence = struct_ev + doc_ev
        return facts, combined_evidence, analytics_dict
