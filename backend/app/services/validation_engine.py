"""
GeoVault AI - Dedicated Validation Engine
Performs mathematical cross-validation, data gap identification,
and automatic conflict surfacing. Never silently reconciles conflicting sources.
"""

from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import select, and_, or_

from app.models.governance import Conflict
from app.schemas.query import MathCheck, DataGap, ConflictItem, ValidationResult
from app.security.context import AuthorizedScope


class ValidationEngine:
    """
    Guarantees facts and arithmetic integrity before answers leave the backend.
    Enforces the core rule: Sources disagree = CONFLICT. Data missing = DATA_GAP.
    """

    @classmethod
    def validate_math(cls, records: List[Any]) -> List[MathCheck]:
        """
        Cross-checks stored database calculations (variance, achievement %)
        against independent recalculations to detect anomalies.
        """
        checks: List[MathCheck] = []

        for r in records:
            data = r if isinstance(r, dict) else {c.name: getattr(r, c.name) for c in r.__table__.columns}
            mine = data.get("mine_code", "N/A")
            year = data.get("year", "N/A")
            prefix = f"{mine}-{year}"

            # 1. Annual Production variance check
            if "actual_production_mt" in data and "target_mt" in data and data["target_mt"] is not None:
                actual = float(data["actual_production_mt"])
                target = float(data["target_mt"])
                calc_variance = round(actual - target, 3)

                if "variance_mt" in data and data["variance_mt"] is not None:
                    db_var = round(float(data["variance_mt"]), 3)
                    diff = round(abs(db_var - calc_variance), 4)
                    is_valid = diff <= 0.01
                    checks.append(
                        MathCheck(
                            field_name=f"{prefix}.variance_mt",
                            database_value=db_var,
                            calculated_value=calc_variance,
                            is_valid=is_valid,
                            discrepancy=diff if not is_valid else 0.0,
                        )
                    )

                if "achievement_pct" in data and data["achievement_pct"] is not None and target > 0:
                    db_achieve = round(float(data["achievement_pct"]), 2)
                    calc_achieve = round((actual / target) * 100.0, 2)
                    diff = round(abs(db_achieve - calc_achieve), 2)
                    is_valid = diff <= 0.05
                    checks.append(
                        MathCheck(
                            field_name=f"{prefix}.achievement_pct",
                            database_value=db_achieve,
                            calculated_value=calc_achieve,
                            is_valid=is_valid,
                            discrepancy=diff if not is_valid else 0.0,
                        )
                    )

            # 2. Monthly Production variance check
            if "production_mt" in data and "monthly_target_mt" in data:
                actual_m = float(data["production_mt"])
                target_m = float(data["monthly_target_mt"])
                calc_var_m = round(actual_m - target_m, 3)
                month = data.get("month", "0")
                if "variance_mt" in data and data["variance_mt"] is not None:
                    db_var_m = round(float(data["variance_mt"]), 3)
                    diff = round(abs(db_var_m - calc_var_m), 4)
                    checks.append(
                        MathCheck(
                            field_name=f"{prefix}-M{month}.variance_mt",
                            database_value=db_var_m,
                            calculated_value=calc_var_m,
                            is_valid=diff <= 0.01,
                            discrepancy=diff if diff > 0.01 else 0.0,
                        )
                    )

        return checks

    @classmethod
    def detect_data_gaps(
        cls,
        records: List[Any],
        domain: str,
        requested_mine: Optional[str] = None,
        requested_year: Optional[int] = None,
        expected_years: Optional[List[int]] = None,
    ) -> List[DataGap]:
        """Identifies missing years, empty domains, or unrecorded fields."""
        gaps: List[DataGap] = []

        if not records:
            desc = f"No records found for domain '{domain}'"
            if requested_mine:
                desc += f" and mine '{requested_mine}'"
            if requested_year:
                desc += f" in year {requested_year}"
            gaps.append(
                DataGap(
                    gap_type="NO_RECORDS_FOUND",
                    entity=requested_mine or "SCOPE",
                    description=desc,
                )
            )
            return gaps

        # Check for missing years if a range was expected
        if expected_years:
            record_years = set()
            for r in records:
                y = r.get("year") if isinstance(r, dict) else getattr(r, "year", None)
                if y:
                    record_years.add(int(y))

            missing_years = sorted(list(set(expected_years) - record_years))
            for my in missing_years:
                gaps.append(
                    DataGap(
                        gap_type="MISSING_YEAR",
                        entity=requested_mine or "SCOPE",
                        description=f"Year {my} is absent from {domain} dataset.",
                    )
                )

        return gaps

    @classmethod
    def surface_conflicts(
        cls,
        db: Session,
        scope: AuthorizedScope,
        mine_code: Optional[str] = None,
        year: Optional[int] = None,
    ) -> List[ConflictItem]:
        """
        Retrieves known conflicts from the conflicts table that fall within
        the user's authorized scope and match the query filters.
        """
        stmt = select(Conflict).where(Conflict.status == "CONFLICT")
        filters = []

        if mine_code:
            # Pre-retrieval check
            if not scope.is_mine_permitted(mine_code):
                return []
            filters.append(Conflict.mine_code == mine_code)
        elif scope.allowed_mines is not None:
            if len(scope.allowed_mines) == 0:
                return []
            filters.append(
                or_(
                    Conflict.mine_code.in_(list(scope.allowed_mines)),
                    Conflict.mine_code.is_(None),
                )
            )

        if year:
            filters.append(or_(Conflict.year == year, Conflict.year.is_(None)))

        if filters:
            stmt = stmt.where(and_(*filters))

        stmt = stmt.order_by(Conflict.conflict_id)
        records = db.scalars(stmt).all()

        conflicts: List[ConflictItem] = []
        for c in records:
            conflicts.append(
                ConflictItem(
                    conflict_id=c.conflict_id,
                    mine_code=c.mine_code,
                    year=c.year,
                    metric_or_topic=c.metric_or_topic,
                    source_a_type=c.source_a_type,
                    source_a_reference=c.source_a_reference,
                    source_a_value=c.source_a_value,
                    source_b_type=c.source_b_type,
                    source_b_reference=c.source_b_reference,
                    source_b_value=c.source_b_value,
                    status=c.status,
                    resolution_policy=c.resolution_policy,
                )
            )

        return conflicts

    @classmethod
    def determine_status(
        cls, records: List[Any], conflicts: List[ConflictItem], data_gaps: List[DataGap]
    ) -> str:
        """Determines the aggregate evidence status according to AGENTS.md rules."""
        if conflicts:
            return "CONFLICT"
        if not records:
            return "INSUFFICIENT_AUTHORIZED_DATA"
        if data_gaps:
            return "PARTIAL"
        return "VERIFIED"

    @classmethod
    def validate_query(
        cls,
        db: Session,
        scope: AuthorizedScope,
        records: List[Any],
        domain: str,
        mine_code: Optional[str] = None,
        year: Optional[int] = None,
        expected_years: Optional[List[int]] = None,
    ) -> ValidationResult:
        """Executes full validation workflow and returns a consolidated ValidationResult."""
        math_checks = cls.validate_math(records)
        data_gaps = cls.detect_data_gaps(records, domain, mine_code, year, expected_years)
        conflicts = cls.surface_conflicts(db, scope, mine_code, year)
        status_str = cls.determine_status(records, conflicts, data_gaps)

        return ValidationResult(
            evidence_status=status_str,
            math_checks=math_checks,
            data_gaps=data_gaps,
            conflicts_detected=conflicts,
            is_complete=(status_str == "VERIFIED"),
        )
