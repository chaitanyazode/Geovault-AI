"""
GeoVault AI - Query Intelligence & Analytics Endpoints
Integrates DeterministicQueryService, AnalyticsEngine, EvidenceEngine, and ValidationEngine
to produce synthesis-ready QueryResultPackage payloads.
"""

from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.schemas.query import (
    IntelligenceQueryRequest,
    IntelligenceAnalyticsRequest,
    MineCompareRequest,
    NaturalQueryRequest,
    GroundedQueryResponse,
    QueryResultPackage,
    AnalyticsResult,
)
from app.services.query_service import DeterministicQueryService
from app.services.evidence_engine import EvidenceEngine
from app.services.validation_engine import ValidationEngine
from app.analytics.engine import AnalyticsEngine
from app.ai.hybrid_pipeline import HybridIntelligencePipeline
from app.ai.orchestrator import UnifiedAIOrchestrator
from app.security.context import UserContext, AuthorizedScope
from app.security.dependencies import (
    get_current_user,
    get_authorized_scope,
    require_permission,
    get_db,
)
from app.security.roles import Permission, has_permission
from app.security.audit import AuditLogger

router = APIRouter(prefix="/intelligence", tags=["Query Intelligence & Analytics"])


@router.post("/query", response_model=QueryResultPackage)
def execute_intelligence_query(
    req: IntelligenceQueryRequest,
    user: UserContext = Depends(require_permission(Permission.QUERY_STRUCTURED)),
    scope: AuthorizedScope = Depends(get_authorized_scope),
    db: Session = Depends(get_db),
) -> QueryResultPackage:
    """
    Executes a deterministic operational query with complete evidence tracking
    and validation under the user's active authorized scope.
    """
    if req.mine_code and not scope.is_mine_permitted(req.mine_code):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Access Denied: User '{user.user_id}' is not authorized to access mine '{req.mine_code}'.",
        )

    records: List[Any] = []
    domain = req.domain.lower()

    if domain == "production_annual":
        records = DeterministicQueryService.get_annual_production(
            db, scope, mine_code=req.mine_code, year=req.year, start_year=req.start_year, end_year=req.end_year
        )
    elif domain == "production_monthly":
        records = DeterministicQueryService.get_monthly_production(
            db, scope, mine_code=req.mine_code, year=req.year, month=req.month
        )
    elif domain == "dispatch_summary":
        records = DeterministicQueryService.get_dispatch_summary(
            db, scope, mine_code=req.mine_code, year=req.year
        )
    elif domain == "coal_quality":
        records = DeterministicQueryService.get_coal_quality(
            db, scope, mine_code=req.mine_code, year=req.year
        )
    elif domain == "geological_units":
        records = DeterministicQueryService.get_geological_units(
            db, scope, mine_code=req.mine_code, risk=req.category
        )
    elif domain == "mining_issue_log":
        records = DeterministicQueryService.get_mining_issues(
            db, scope, mine_code=req.mine_code, year=req.year, category=req.category
        )
    elif domain == "inspection_register":
        records = DeterministicQueryService.get_inspections(
            db, scope, mine_code=req.mine_code, year=req.year, focus=req.category
        )
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported domain '{req.domain}'.",
        )

    # Convert records to list of dicts for facts
    facts = []
    for r in records[:req.limit]:
        d = {c.name: getattr(r, c.name) for c in r.__table__.columns}
        facts.append(d)

    # Generate evidence items
    evidence_items = EvidenceEngine.from_structured_records(records[:req.limit], domain)

    # Run validation engine
    expected_years = None
    if req.start_year and req.end_year:
        expected_years = list(range(req.start_year, req.end_year + 1))

    val_result = ValidationEngine.validate_query(
        db=db,
        scope=scope,
        records=facts,
        domain=domain,
        mine_code=req.mine_code,
        year=req.year,
        expected_years=expected_years,
    )

    # Persist audit entry
    AuditLogger.log_query(
        db=db,
        user_id=user.user_id,
        question=f"Intelligence query domain={domain} mine={req.mine_code} year={req.year}",
        route_selected="SQL",
        scope=scope,
        evidence_count=len(evidence_items),
        evidence_status=val_result.evidence_status,
        response_summary=f"Retrieved {len(facts)} facts with status {val_result.evidence_status}",
    )

    return QueryResultPackage(
        domain=domain,
        query_description=f"Operational query on {domain} for mine {req.mine_code or 'ALL'} (records={len(facts)})",
        authorized_scope_applied=scope.to_dict(),
        facts=facts,
        analytics=None,
        evidence=evidence_items,
        validation=val_result,
    )


@router.post("/analytics", response_model=QueryResultPackage)
def execute_intelligence_analytics(
    req: IntelligenceAnalyticsRequest,
    user: UserContext = Depends(require_permission(Permission.QUERY_AGGREGATE)),
    scope: AuthorizedScope = Depends(get_authorized_scope),
    db: Session = Depends(get_db),
) -> QueryResultPackage:
    """
    Executes deterministic calculations (totals, averages, trends, achievements)
    strictly within user's authorized scope. Python calculates, LLM explains.
    """
    if req.mine_code and not scope.is_mine_permitted(req.mine_code):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Access Denied: User '{user.user_id}' is not authorized to access mine '{req.mine_code}'.",
        )

    domain = req.domain.lower()
    if domain != "production_annual" and domain != "production_monthly" and domain != "dispatch_summary":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Analytics currently supports numerical operational domains: production_annual, production_monthly, dispatch_summary.",
        )

    # Fetch scoped source records
    if domain == "production_annual":
        records = DeterministicQueryService.get_annual_production(
            db, scope, mine_code=req.mine_code, year=req.year, start_year=req.start_year, end_year=req.end_year
        )
    elif domain == "production_monthly":
        records = DeterministicQueryService.get_monthly_production(
            db, scope, mine_code=req.mine_code, year=req.year
        )
    else:
        records = DeterministicQueryService.get_dispatch_summary(
            db, scope, mine_code=req.mine_code, year=req.year
        )

    facts = [{c.name: getattr(r, c.name) for c in r.__table__.columns} for r in records]
    evidence_items = EvidenceEngine.from_structured_records(records, domain)

    # Perform deterministic calculations
    op = req.operation.lower()
    analytics_out = AnalyticsResult(operation=op, metric=req.metric)

    if op in ["summary", "total", "average"]:
        analytics_out.total = AnalyticsEngine.compute_total(facts, req.metric)
        analytics_out.average = AnalyticsEngine.compute_average(facts, req.metric)
        min_max = AnalyticsEngine.compute_min_max(facts, req.metric)
        analytics_out.min_value = min_max["min"]
        analytics_out.max_value = min_max["max"]

    elif op in ["trend", "yoy"]:
        time_key = "month" if domain == "production_monthly" else "year"
        target_key = "monthly_target_mt" if domain == "production_monthly" else "target_mt"
        trend_summary = AnalyticsEngine.compute_trend_summary(
            facts, time_key=time_key, metric_key=req.metric, target_key=target_key
        )
        analytics_out.trend = trend_summary
        analytics_out.total = AnalyticsEngine.compute_total(facts, req.metric)
        analytics_out.average = AnalyticsEngine.compute_average(facts, req.metric)

    elif op in ["target_vs_actual", "achievement"]:
        tot_actual = AnalyticsEngine.compute_total(facts, "actual_production_mt")
        tot_target = AnalyticsEngine.compute_total(facts, "target_mt")
        achieve = AnalyticsEngine.compute_target_achievement(tot_target, tot_actual)
        analytics_out.total = tot_actual
        analytics_out.target_achievement_pct = achieve["achievement_pct"]
        analytics_out.variance_mt = achieve["variance"]

    # Validate output
    val_result = ValidationEngine.validate_query(
        db=db,
        scope=scope,
        records=facts,
        domain=domain,
        mine_code=req.mine_code,
        year=req.year,
    )

    AuditLogger.log_query(
        db=db,
        user_id=user.user_id,
        question=f"Analytics {op} on {domain}.{req.metric} mine={req.mine_code}",
        route_selected="ANALYTICS",
        scope=scope,
        evidence_count=len(evidence_items),
        evidence_status=val_result.evidence_status,
        response_summary=f"Analytics operation '{op}' completed with status {val_result.evidence_status}",
    )

    return QueryResultPackage(
        domain=domain,
        query_description=f"Analytics operation '{op}' on {domain}.{req.metric} (records={len(facts)})",
        authorized_scope_applied=scope.to_dict(),
        facts=facts,
        analytics=analytics_out,
        evidence=evidence_items,
        validation=val_result,
    )


@router.post("/compare", response_model=QueryResultPackage)
def execute_mine_comparison(
    req: MineCompareRequest,
    user: UserContext = Depends(require_permission(Permission.QUERY_AGGREGATE)),
    scope: AuthorizedScope = Depends(get_authorized_scope),
    db: Session = Depends(get_db),
) -> QueryResultPackage:
    """
    Compares production and performance across multiple mines.
    Strictly verifies that every requested mine is authorized for the user.
    """
    # Verify all requested mines are permitted
    if req.mine_codes:
        for m in req.mine_codes:
            if not scope.is_mine_permitted(m):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Access Denied: User '{user.user_id}' is not authorized to access mine '{m}'.",
                )

    # Fetch production records for the period
    records = DeterministicQueryService.get_annual_production(
        db, scope, start_year=req.start_year, end_year=req.end_year
    )

    # Filter by requested mines if provided
    if req.mine_codes:
        records = [r for r in records if r.mine_code in req.mine_codes]

    # Map mine names
    all_mines = DeterministicQueryService.get_authorized_mines(db, scope)
    names_map = {m.mine_code: m.mine_name for m in all_mines}

    facts = [{c.name: getattr(r, c.name) for c in r.__table__.columns} for r in records]
    comparison_items = AnalyticsEngine.compare_mines(facts, mine_names_map=names_map)
    evidence_items = EvidenceEngine.from_structured_records(records, "production_annual")

    val_result = ValidationEngine.validate_query(
        db=db,
        scope=scope,
        records=facts,
        domain="production_annual",
    )

    analytics_out = AnalyticsResult(
        operation="compare",
        metric="actual_production_mt",
        total=AnalyticsEngine.compute_total(facts, "actual_production_mt"),
        average=AnalyticsEngine.compute_average(facts, "actual_production_mt"),
        comparisons=comparison_items,
    )

    AuditLogger.log_query(
        db=db,
        user_id=user.user_id,
        question=f"Mine comparison {req.mine_codes or 'ALL'} years={req.start_year}-{req.end_year}",
        route_selected="ANALYTICS",
        scope=scope,
        evidence_count=len(evidence_items),
        evidence_status=val_result.evidence_status,
        response_summary=f"Compared {len(comparison_items)} mines",
    )

    return QueryResultPackage(
        domain="production_annual",
        query_description=f"Multi-mine comparison across {len(comparison_items)} mines ({req.start_year}–{req.end_year})",
        authorized_scope_applied=scope.to_dict(),
        facts=facts,
        analytics=analytics_out,
        evidence=evidence_items,
        validation=val_result,
    )


@router.post("/natural-query", response_model=GroundedQueryResponse)
def execute_natural_language_query(
    req: NaturalQueryRequest,
    user: UserContext = Depends(get_current_user),
    scope: AuthorizedScope = Depends(get_authorized_scope),
    db: Session = Depends(get_db),
) -> GroundedQueryResponse:
    """
    Executes a natural language query end-to-end.
    Performs deterministic query routing, pre-retrieval authorization scoping,
    structured/vector retrieval, validation, and grounded local Qwen3-8B reasoning.
    """
    if not (has_permission(user.role, Permission.QUERY_STRUCTURED) or has_permission(user.role, Permission.QUERY_VECTOR)):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Access Denied: Role '{user.role}' lacks query permissions.",
        )

    orchestrator = UnifiedAIOrchestrator(db=db, user=user, scope=scope)
    return orchestrator.orchestrate(
        query=req.query,
        target_mine_hint=req.target_mine,
        target_year_hint=req.target_year,
        top_k=req.top_k,
    )


@router.get("/logs")
def get_operational_audit_logs(
    limit: int = 50,
    user: UserContext = Depends(get_current_user),
    scope: AuthorizedScope = Depends(get_authorized_scope),
    db: Session = Depends(get_db),
):
    """
    Returns operational query and governance audit logs.
    Preserved for backward compatibility, delegated to AuditLogService.
    """
    from app.services.audit_service import AuditLogService

    paginated = AuditLogService.get_audit_logs(
        db=db,
        user=user,
        scope=scope,
        page=1,
        page_size=limit,
    )
    return [
        {
            "log_id": item.log_id,
            "user_id": item.user_id,
            "time": item.timestamp,
            "action": item.action,
            "module": item.module,
            "route": item.route,
            "details": item.sanitized_details,
            "status": item.status,
            "evidence_status": item.evidence_status,
            "evidence_count": item.evidence_count,
            "execution_time_ms": item.execution_time_ms,
        }
        for item in paginated.items
    ]
