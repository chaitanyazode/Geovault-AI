"""
GeoVault AI - Centralized Authorization Service
Enforces 'Authorization Before Retrieval' (RBAC + ABAC) across all queries,
vector searches, aggregations, and evidence access.
"""

from typing import List, Optional, Set, Dict, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import select, func, text, and_, or_

from app.models.master import User, UserScope
from app.models.knowledge import DocumentChunk, Document
from app.models.governance import Evidence, Conflict
from app.security.clearance import (
    ClearanceLevel,
    CLEARANCE_RANKS,
    get_clearance_rank,
    is_clearance_sufficient,
)
from app.security.roles import Permission, has_permission
from app.security.context import UserContext, ScopeRule, AuthorizedScope


class AuthorizationService:
    """
    Central authority for identity resolution, scope derivation,
    and query scoping. The LLM is never the security boundary.
    """

    @staticmethod
    def resolve_user_context(db: Session, user_id: str) -> UserContext:
        """Retrieves user and active scopes from PostgreSQL and builds UserContext."""
        stmt = select(User).where(User.user_id == user_id, User.is_active == True)
        user = db.execute(stmt).scalar_one_or_none()
        if not user:
            raise ValueError(f"User '{user_id}' does not exist or is inactive.")

        scope_rules: List[ScopeRule] = []
        for s in user.scopes:
            scope_rules.append(
                ScopeRule(
                    mine_code=s.mine_code,
                    department=s.department,
                    max_classification=s.max_classification,
                )
            )

        return UserContext(
            user_id=user.user_id,
            username=user.username,
            email=user.email,
            role=user.role,
            department=user.department,
            clearance_level=user.clearance_level,
            assigned_mine_code=user.assigned_mine_code,
            is_active=user.is_active,
            scopes=scope_rules,
        )

    @staticmethod
    def get_authorized_scope(user: UserContext) -> AuthorizedScope:
        """
        Derives the definitive retrieval boundary (AuthorizedScope) from
        user role, clearance level, assigned mine, and configured scopes.
        """
        user_rank = get_clearance_rank(user.clearance_level)

        # Administrator has enterprise-wide scope bounded only by clearance
        if user.role == "Administrator":
            return AuthorizedScope(
                user_id=user.user_id,
                role=user.role,
                allowed_mines=None,  # Unrestricted
                allowed_departments=None,  # Unrestricted
                max_clearance=user.clearance_level,
                can_access_macro=True,
            )

        allowed_mines: Optional[Set[str]] = set()
        allowed_depts: Optional[Set[str]] = set()
        max_classification_rank = user_rank

        if user.scopes:
            for sc in user.scopes:
                # Mine resolution
                if sc.mine_code is None or sc.mine_code.upper() in ["ALL", "ENTERPRISE"]:
                    allowed_mines = None
                elif allowed_mines is not None and sc.mine_code:
                    allowed_mines.add(sc.mine_code)

                # Department resolution
                if sc.department is None or sc.department.upper() in ["ALL", "GENERAL"]:
                    allowed_depts = None
                elif allowed_depts is not None and sc.department:
                    allowed_depts.add(sc.department)

                # Clearance resolution
                sc_rank = get_clearance_rank(sc.max_classification)
                if sc_rank > max_classification_rank:
                    max_classification_rank = sc_rank
        else:
            # Fallback to direct assigned attributes
            if user.assigned_mine_code:
                allowed_mines = {user.assigned_mine_code}
            if user.department and user.department.upper() != "EXECUTIVE":
                allowed_depts = {user.department}
            else:
                allowed_depts = None

        # Determine highest permitted classification string
        rank_to_level = {v: k.value for k, v in CLEARANCE_RANKS.items()}
        max_clearance_str = rank_to_level.get(max_classification_rank, "INTERNAL")

        return AuthorizedScope(
            user_id=user.user_id,
            role=user.role,
            allowed_mines=allowed_mines,
            allowed_departments=allowed_depts,
            max_clearance=max_clearance_str,
            can_access_macro=True,
        )

    @classmethod
    def scope_structured_query(cls, query: Any, model: Any, scope: AuthorizedScope) -> Any:
        """
        Injects mandatory WHERE filters into SQLAlchemy select queries BEFORE execution.
        Prevents unauthorized records from ever leaving the database.
        """
        filters = []

        # Mine scoping
        if hasattr(model, "mine_code") and scope.allowed_mines is not None:
            if len(scope.allowed_mines) == 0:
                # User has no allowed mines, match nothing
                filters.append(text("1 = 0"))
            else:
                filters.append(model.mine_code.in_(list(scope.allowed_mines)))

        # Department scoping
        if hasattr(model, "department") and scope.allowed_departments is not None:
            if len(scope.allowed_departments) > 0:
                filters.append(
                    or_(
                        model.department.in_(list(scope.allowed_departments)),
                        model.department.is_(None),
                    )
                )

        # Clearance scoping
        if hasattr(model, "classification"):
            user_rank = get_clearance_rank(scope.max_clearance)
            allowed_classifications = [
                k.value for k, v in CLEARANCE_RANKS.items() if v <= user_rank
            ]
            filters.append(model.classification.in_(allowed_classifications))

        if filters:
            return query.where(and_(*filters))
        return query

    @classmethod
    def scoped_vector_search(
        cls,
        db: Session,
        query_embedding: List[float],
        scope: AuthorizedScope,
        top_k: int = 5,
        target_mine: Optional[str] = None,
    ) -> List[Tuple[DocumentChunk, float]]:
        """
        Executes pgvector cosine similarity search with mandatory SQL filters
        injected BEFORE returning chunks. Never retrieves unrestricted data.
        """
        # Build SQL filter conditions
        where_clauses = ["embedding IS NOT NULL"]

        # 1. Mine filter
        if target_mine:
            if not scope.is_mine_permitted(target_mine):
                # Requested mine is outside user scope -> return empty immediately
                return []
            where_clauses.append(f"(mine_code = '{target_mine}' OR mine_code IS NULL)")
        elif scope.allowed_mines is not None:
            if len(scope.allowed_mines) == 0:
                return []
            mine_list_str = ", ".join([f"'{m}'" for m in scope.allowed_mines])
            where_clauses.append(f"(mine_code IN ({mine_list_str}) OR mine_code IS NULL)")

        # 2. Department filter
        if scope.allowed_departments is not None and len(scope.allowed_departments) > 0:
            dept_list_str = ", ".join([f"'{d}'" for d in scope.allowed_departments])
            where_clauses.append(f"(department IN ({dept_list_str}) OR department IS NULL)")

        # 3. Clearance filter
        user_rank = get_clearance_rank(scope.max_clearance)
        allowed_classifications = [
            f"'{k.value}'" for k, v in CLEARANCE_RANKS.items() if v <= user_rank
        ]
        class_list_str = ", ".join(allowed_classifications)
        where_clauses.append(f"classification IN ({class_list_str})")

        filter_sql = " AND ".join(where_clauses)
        emb_str = str(query_embedding)

        query_sql = text(f"""
            SELECT 
                chunk_id,
                1 - (embedding <=> CAST(:q_emb AS vector(1024))) AS similarity
            FROM document_chunks
            WHERE {filter_sql}
            ORDER BY embedding <=> CAST(:q_emb AS vector(1024))
            LIMIT :top_k;
        """)

        rows = db.execute(query_sql, {"q_emb": emb_str, "top_k": top_k}).fetchall()
        if not rows:
            return []

        chunk_ids = [r.chunk_id for r in rows]
        score_map = {r.chunk_id: float(r.similarity) for r in rows}

        chunks = db.scalars(
            select(DocumentChunk).where(DocumentChunk.chunk_id.in_(chunk_ids))
        ).all()

        results = [(c, score_map.get(c.chunk_id, 0.0)) for c in chunks]
        results.sort(key=lambda x: x[1], reverse=True)
        return results

    @classmethod
    def scoped_aggregate(
        cls,
        db: Session,
        model: Any,
        metric_column: Any,
        group_by_column: Optional[Any],
        scope: AuthorizedScope,
        agg_func: str = "SUM",
    ) -> List[Dict[str, Any]]:
        """
        Executes aggregate queries strictly within user's permitted mines.
        Prevents unauthorized mine data from leaking into totals or group-bys.
        """
        fn = func.sum if agg_func.upper() == "SUM" else func.avg

        if group_by_column is not None:
            base_query = select(group_by_column, fn(metric_column).label("value"))
            scoped_query = cls.scope_structured_query(base_query, model, scope)
            scoped_query = scoped_query.group_by(group_by_column)
            rows = db.execute(scoped_query).fetchall()
            return [{"key": r[0], "value": float(r[1]) if r[1] is not None else 0.0} for r in rows]
        else:
            base_query = select(fn(metric_column).label("value"))
            scoped_query = cls.scope_structured_query(base_query, model, scope)
            val = db.execute(scoped_query).scalar()
            return [{"key": "total", "value": float(val) if val is not None else 0.0}]

    @classmethod
    def validate_evidence_access(
        cls, user: UserContext, scope: AuthorizedScope, evidence_obj: Any
    ) -> bool:
        """Verifies whether an evidence record, conflict, or chunk is readable by user."""
        mine_code = getattr(evidence_obj, "mine_code", None)
        department = getattr(evidence_obj, "department", None)
        classification = getattr(evidence_obj, "classification", "INTERNAL")

        return scope.is_resource_authorized(
            mine_code=mine_code,
            department=department,
            classification=classification,
        )
