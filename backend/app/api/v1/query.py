"""
GeoVault AI - Scoped Query Execution Endpoints
Enforces 'Authorization Before Retrieval' on structured, vector, and aggregate queries.
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.models.operational import (
    ProductionAnnual,
    ProductionMonthly,
    DispatchSummary,
    CoalQuality,
    GeologicalUnit,
    MiningIssueLog,
    InspectionRegister,
)
from app.ingestion.unstructured import get_embedding_model
from app.security.context import UserContext, AuthorizedScope
from app.security.dependencies import (
    get_current_user,
    get_authorized_scope,
    require_permission,
    get_db,
)
from app.security.roles import Permission
from app.security.service import AuthorizationService
from app.security.audit import AuditLogger

router = APIRouter(prefix="/query", tags=["Authorized Query & Retrieval"])

DOMAIN_MODELS = {
    "production_annual": ProductionAnnual,
    "production_monthly": ProductionMonthly,
    "dispatch_summary": DispatchSummary,
    "coal_quality": CoalQuality,
    "geological_units": GeologicalUnit,
    "mining_issue_log": MiningIssueLog,
    "inspection_register": InspectionRegister,
}


class StructuredQueryRequest(BaseModel):
    domain: str = Field(..., description="Operational domain (e.g. production_annual, mining_issue_log)")
    mine_code: Optional[str] = Field(None, description="Optional target mine code (e.g. DEOM-01)")
    year: Optional[int] = Field(None, description="Optional reporting year (e.g. 2024)")
    limit: int = Field(50, ge=1, le=500)


class VectorSearchRequest(BaseModel):
    query: str = Field(..., min_length=2, description="Natural language search query")
    target_mine: Optional[str] = Field(None, description="Optional target mine filter")
    top_k: int = Field(5, ge=1, le=20)


class AggregateQueryRequest(BaseModel):
    domain: str = Field("production_annual", description="Operational domain")
    metric: str = Field("actual_production_mt", description="Numeric column to aggregate")
    group_by: Optional[str] = Field(None, description="Optional column to group by (e.g. mine_code)")
    agg_func: str = Field("SUM", description="Aggregation function: SUM or AVG")


@router.post("/structured")
def query_structured_data(
    req: StructuredQueryRequest,
    user: UserContext = Depends(require_permission(Permission.QUERY_STRUCTURED)),
    scope: AuthorizedScope = Depends(get_authorized_scope),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """
    Executes a structured query strictly scoped to the user's permitted mines,
    departments, and classification levels.
    """
    if req.domain not in DOMAIN_MODELS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown domain '{req.domain}'. Valid domains: {list(DOMAIN_MODELS.keys())}",
        )

    # Pre-retrieval check on explicitly requested mine
    if req.mine_code and not scope.is_mine_permitted(req.mine_code):
        AuditLogger.log_query(
            db=db,
            user_id=user.user_id,
            question=f"Structured query domain={req.domain} mine={req.mine_code}",
            route_selected="SQL",
            scope=scope,
            evidence_count=0,
            evidence_status="INSUFFICIENT_AUTHORIZED_DATA",
            response_summary="Access Denied: Requested mine is outside authorized scope.",
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Access Denied: User '{user.user_id}' is not authorized to access data for mine '{req.mine_code}'.",
        )

    model = DOMAIN_MODELS[req.domain]
    base_query = select(model)

    if req.mine_code:
        base_query = base_query.where(model.mine_code == req.mine_code)
    if req.year and hasattr(model, "year"):
        base_query = base_query.where(model.year == req.year)

    # Apply strict RBAC+ABAC scoping BEFORE execution
    scoped_query = AuthorizationService.scope_structured_query(base_query, model, scope)
    scoped_query = scoped_query.limit(req.limit)

    records = db.scalars(scoped_query).all()

    # Convert records to dictionary for output
    results = []
    for r in records:
        d = {c.name: getattr(r, c.name) for c in r.__table__.columns}
        results.append(d)

    AuditLogger.log_query(
        db=db,
        user_id=user.user_id,
        question=f"Structured query domain={req.domain} mine={req.mine_code} year={req.year}",
        route_selected="SQL",
        scope=scope,
        evidence_count=len(results),
        evidence_status="VERIFIED" if len(results) > 0 else "INSUFFICIENT_AUTHORIZED_DATA",
        response_summary=f"Returned {len(results)} scoped records for {req.domain}",
    )

    return {
        "status": "success",
        "domain": req.domain,
        "count": len(results),
        "authorized_scope_applied": scope.to_dict(),
        "records": results,
    }


@router.post("/search")
def search_vector_knowledge(
    req: VectorSearchRequest,
    user: UserContext = Depends(require_permission(Permission.QUERY_VECTOR)),
    scope: AuthorizedScope = Depends(get_authorized_scope),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """
    Executes permission-aware semantic vector search.
    Only returns document chunks satisfying the user's permitted mines,
    departments, and clearance rank.
    """
    # Pre-retrieval check on explicitly requested target mine
    if req.target_mine and not scope.is_mine_permitted(req.target_mine):
        AuditLogger.log_query(
            db=db,
            user_id=user.user_id,
            question=req.query,
            route_selected="RAG",
            scope=scope,
            evidence_count=0,
            evidence_status="INSUFFICIENT_AUTHORIZED_DATA",
            response_summary="Access Denied: Target mine is outside authorized scope.",
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Access Denied: User '{user.user_id}' is not authorized to access document chunks for mine '{req.target_mine}'.",
        )

    # Generate 1024-dim BAAI/bge-m3 query vector
    emb_model = get_embedding_model()
    q_vec = emb_model.encode(req.query, normalize_embeddings=True).tolist()

    # Pre-filtered vector retrieval
    matches = AuthorizationService.scoped_vector_search(
        db=db,
        query_embedding=q_vec,
        scope=scope,
        top_k=req.top_k,
        target_mine=req.target_mine,
    )

    results = []
    for chunk, sim in matches:
        results.append({
            "chunk_id": chunk.chunk_id,
            "document_id": chunk.document_id,
            "page_number": chunk.page_number,
            "mine_code": chunk.mine_code,
            "department": chunk.department,
            "classification": chunk.classification,
            "similarity": round(sim, 4),
            "snippet": chunk.chunk_text[:250],
        })

    AuditLogger.log_query(
        db=db,
        user_id=user.user_id,
        question=req.query,
        route_selected="RAG",
        scope=scope,
        evidence_count=len(results),
        evidence_status="VERIFIED" if len(results) > 0 else "INSUFFICIENT_AUTHORIZED_DATA",
        response_summary=f"Retrieved {len(results)} authorized chunks for query '{req.query}'",
    )

    return {
        "status": "success",
        "query": req.query,
        "count": len(results),
        "authorized_scope_applied": scope.to_dict(),
        "chunks": results,
    }


@router.post("/aggregate")
def compute_scoped_aggregate(
    req: AggregateQueryRequest,
    user: UserContext = Depends(require_permission(Permission.QUERY_AGGREGATE)),
    scope: AuthorizedScope = Depends(get_authorized_scope),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """
    Computes numerical aggregations strictly over authorized mines.
    Prevents unauthorized mine data from leaking into totals or group-bys.
    """
    if req.domain not in DOMAIN_MODELS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown domain '{req.domain}'.",
        )

    model = DOMAIN_MODELS[req.domain]
    if not hasattr(model, req.metric):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Metric column '{req.metric}' does not exist on '{req.domain}'.",
        )

    metric_col = getattr(model, req.metric)
    group_col = getattr(model, req.group_by) if req.group_by and hasattr(model, req.group_by) else None

    results = AuthorizationService.scoped_aggregate(
        db=db,
        model=model,
        metric_column=metric_col,
        group_by_column=group_col,
        scope=scope,
        agg_func=req.agg_func,
    )

    AuditLogger.log_query(
        db=db,
        user_id=user.user_id,
        question=f"Aggregate {req.agg_func}({req.metric}) on {req.domain} group_by={req.group_by}",
        route_selected="ANALYTICS",
        scope=scope,
        evidence_count=len(results),
        evidence_status="VERIFIED",
        response_summary=f"Scoped aggregation returned {len(results)} groups",
    )

    return {
        "status": "success",
        "domain": req.domain,
        "metric": req.metric,
        "group_by": req.group_by,
        "agg_func": req.agg_func,
        "authorized_scope_applied": scope.to_dict(),
        "aggregations": results,
    }
