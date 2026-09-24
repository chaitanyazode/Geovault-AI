"""
GeoVault AI - Deterministic Query Service
Provides controlled, template-driven query functions across operational domains.
Strictly enforces 'Authorization Before Retrieval' via AuthorizedScope.
"""

from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import select, and_

from app.models.master import Mine
from app.models.operational import (
    ProductionAnnual,
    ProductionMonthly,
    DispatchSummary,
    CoalQuality,
    GeologicalUnit,
    MiningIssueLog,
    InspectionRegister,
)
from app.models.geological import (
    EquipmentFleet,
    SafetyRecord,
    EnvironmentalRecord,
    CoalSeam,
    BoreholeMaster,
    BoreholeInterval,
    GeologicalEvent,
    GeotechnicalZone,
    SurveyPoint,
    CrossSectionPoint,
    QABenchmark,
)
from app.security.context import AuthorizedScope
from app.security.service import AuthorizationService


class DeterministicQueryService:
    """
    Controlled query layer for structured organizational data.
    Never allows raw user SQL; strictly injects scope filters before execution.
    """

    @classmethod
    def _get_mine_aliases(cls, mine_code: Optional[str]) -> List[str]:
        """Resolves canonical mine codes to all known aliases for seamless relational querying."""
        if not mine_code:
            return []
        aliases = AuthorizedScope.MINE_ALIAS_SETS.get(mine_code.upper(), {mine_code})
        return list(aliases)

    @classmethod
    def get_annual_production(
        cls,
        db: Session,
        scope: AuthorizedScope,
        mine_code: Optional[str] = None,
        year: Optional[int] = None,
        start_year: Optional[int] = None,
        end_year: Optional[int] = None,
    ) -> List[ProductionAnnual]:
        """Queries annual production targets, actuals, variances, and face availability."""
        if mine_code and not scope.is_mine_permitted(mine_code):
            return []

        stmt = select(ProductionAnnual)
        filters = []

        if mine_code:
            norm_code = mine_code.upper()
            canonical_map = {
                "GV001": "GEVRA", "GEVRA": "GEVRA",
                "GV002": "KUSMUNDA", "KUSMUNDA": "KUSMUNDA",
                "GV003": "DIPKA", "DIPKA": "DIPKA",
                "GV004": "NIGAHI", "NIGAHI": "NIGAHI",
                "GV005": "DUDHICHUA", "DUDHICHUA": "DUDHICHUA",
            }
            canonical_code = canonical_map.get(norm_code, norm_code)
            # In ProductionAnnual, canonical mines have their own direct authoritative records (56.10 MT for GEVRA).
            # Never fall back to legacy aliases like DEOM-01 when querying a canonical mine.
            if canonical_code in ["GEVRA", "KUSMUNDA", "DIPKA", "NIGAHI", "DUDHICHUA"]:
                filters.append(ProductionAnnual.mine_code == canonical_code)
            elif norm_code in ["DEOM-01", "KNUG-02", "SSOP-03"]:
                filters.append(ProductionAnnual.mine_code == norm_code)
            else:
                filters.append(ProductionAnnual.mine_code.in_(cls._get_mine_aliases(mine_code)))
        else:
            # Multi-mine comparisons: query canonical mines to prevent legacy seed contamination
            canonical_five = ["GEVRA", "KUSMUNDA", "DIPKA", "NIGAHI", "DUDHICHUA"]
            filters.append(ProductionAnnual.mine_code.in_(canonical_five))

        if year:
            filters.append(ProductionAnnual.year == year)
        if start_year:
            filters.append(ProductionAnnual.year >= start_year)
        if end_year:
            filters.append(ProductionAnnual.year <= end_year)

        if filters:
            stmt = stmt.where(and_(*filters))

        scoped_stmt = AuthorizationService.scope_structured_query(stmt, ProductionAnnual, scope)
        scoped_stmt = scoped_stmt.order_by(ProductionAnnual.mine_code, ProductionAnnual.year)
        return list(db.scalars(scoped_stmt).all())

    @classmethod
    def get_monthly_production(
        cls,
        db: Session,
        scope: AuthorizedScope,
        mine_code: Optional[str] = None,
        year: Optional[int] = None,
        month: Optional[int] = None,
    ) -> List[ProductionMonthly]:
        """Queries monthly production breakdowns and variances."""
        if mine_code and not scope.is_mine_permitted(mine_code):
            return []

        stmt = select(ProductionMonthly)
        filters = []
        if mine_code:
            filters.append(ProductionMonthly.mine_code.in_(cls._get_mine_aliases(mine_code)))
        if year:
            filters.append(ProductionMonthly.year == year)
        if month:
            filters.append(ProductionMonthly.month == month)

        if filters:
            stmt = stmt.where(and_(*filters))

        scoped_stmt = AuthorizationService.scope_structured_query(stmt, ProductionMonthly, scope)
        scoped_stmt = scoped_stmt.order_by(
            ProductionMonthly.mine_code, ProductionMonthly.year, ProductionMonthly.month
        )
        return list(db.scalars(scoped_stmt).all())

    @classmethod
    def get_dispatch_summary(
        cls,
        db: Session,
        scope: AuthorizedScope,
        mine_code: Optional[str] = None,
        year: Optional[int] = None,
    ) -> List[DispatchSummary]:
        """Queries dispatch volumes, rail/road modes, and logistics bottleneck statuses."""
        if mine_code and not scope.is_mine_permitted(mine_code):
            return []

        stmt = select(DispatchSummary)
        filters = []
        if mine_code:
            filters.append(DispatchSummary.mine_code.in_(cls._get_mine_aliases(mine_code)))
        if year:
            filters.append(DispatchSummary.year == year)

        if filters:
            stmt = stmt.where(and_(*filters))

        scoped_stmt = AuthorizationService.scope_structured_query(stmt, DispatchSummary, scope)
        scoped_stmt = scoped_stmt.order_by(DispatchSummary.mine_code, DispatchSummary.year)
        return list(db.scalars(scoped_stmt).all())

    @classmethod
    def get_coal_quality(
        cls,
        db: Session,
        scope: AuthorizedScope,
        mine_code: Optional[str] = None,
        year: Optional[int] = None,
    ) -> List[CoalQuality]:
        """Queries coal quality parameters (ash %, moisture %, blending actions)."""
        if mine_code and not scope.is_mine_permitted(mine_code):
            return []

        stmt = select(CoalQuality)
        filters = []
        if mine_code:
            filters.append(CoalQuality.mine_code.in_(cls._get_mine_aliases(mine_code)))
        if year:
            filters.append(CoalQuality.year == year)

        if filters:
            stmt = stmt.where(and_(*filters))

        scoped_stmt = AuthorizationService.scope_structured_query(stmt, CoalQuality, scope)
        scoped_stmt = scoped_stmt.order_by(CoalQuality.mine_code, CoalQuality.year)
        return list(db.scalars(scoped_stmt).all())

    @classmethod
    def get_geological_units(
        cls,
        db: Session,
        scope: AuthorizedScope,
        mine_code: Optional[str] = None,
        unit: Optional[str] = None,
        risk: Optional[str] = None,
    ) -> List[GeologicalUnit]:
        """Queries geological strata, horizon depth, seam thickness, and risk classifications."""
        if mine_code and not scope.is_mine_permitted(mine_code):
            return []

        stmt = select(GeologicalUnit)
        filters = []
        if mine_code:
            filters.append(GeologicalUnit.mine_code.in_(cls._get_mine_aliases(mine_code)))
        if unit:
            filters.append(GeologicalUnit.unit.ilike(f"%{unit}%"))
        if risk:
            filters.append(GeologicalUnit.geological_risk.ilike(f"%{risk}%"))

        if filters:
            stmt = stmt.where(and_(*filters))

        scoped_stmt = AuthorizationService.scope_structured_query(stmt, GeologicalUnit, scope)
        scoped_stmt = scoped_stmt.order_by(GeologicalUnit.mine_code, GeologicalUnit.unit)
        return list(db.scalars(scoped_stmt).all())

    @classmethod
    def get_mining_issues(
        cls,
        db: Session,
        scope: AuthorizedScope,
        mine_code: Optional[str] = None,
        year: Optional[int] = None,
        category: Optional[str] = None,
    ) -> List[MiningIssueLog]:
        """Queries operational bottlenecks, monsoon hazards, equipment breakdowns, and corrective actions."""
        if mine_code and not scope.is_mine_permitted(mine_code):
            return []

        stmt = select(MiningIssueLog)
        filters = []
        if mine_code:
            filters.append(MiningIssueLog.mine_code.in_(cls._get_mine_aliases(mine_code)))
        if year:
            filters.append(MiningIssueLog.year == year)
        if category:
            filters.append(MiningIssueLog.issue_category.ilike(f"%{category}%"))

        if filters:
            stmt = stmt.where(and_(*filters))

        scoped_stmt = AuthorizationService.scope_structured_query(stmt, MiningIssueLog, scope)
        scoped_stmt = scoped_stmt.order_by(MiningIssueLog.mine_code, MiningIssueLog.year)
        return list(db.scalars(scoped_stmt).all())

    @classmethod
    def get_inspections(
        cls,
        db: Session,
        scope: AuthorizedScope,
        mine_code: Optional[str] = None,
        year: Optional[int] = None,
        focus: Optional[str] = None,
    ) -> List[InspectionRegister]:
        """Queries statutory DGMS and internal safety/mining inspections."""
        if mine_code and not scope.is_mine_permitted(mine_code):
            return []

        stmt = select(InspectionRegister)
        filters = []
        if mine_code:
            filters.append(InspectionRegister.mine_code.in_(cls._get_mine_aliases(mine_code)))
        if year:
            filters.append(InspectionRegister.year == year)
        if focus:
            filters.append(InspectionRegister.inspection_focus.ilike(f"%{focus}%"))

        if filters:
            stmt = stmt.where(and_(*filters))

        scoped_stmt = AuthorizationService.scope_structured_query(stmt, InspectionRegister, scope)
        scoped_stmt = scoped_stmt.order_by(InspectionRegister.mine_code, InspectionRegister.year)
        return list(db.scalars(scoped_stmt).all())

    @classmethod
    def get_equipment_metrics(
        cls,
        db: Session,
        scope: AuthorizedScope,
        mine_code: Optional[str] = None,
        year: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        Derives operational equipment metrics from annual records.
        Calculates equipment availability %, estimated downtime %, and production impact.
        """
        records = cls.get_annual_production(db, scope, mine_code=mine_code, year=year)
        metrics = []
        for r in records:
            avail = float(r.equipment_or_face_availability_pct) if r.equipment_or_face_availability_pct else None
            downtime = round(100.0 - avail, 2) if avail is not None else None
            metrics.append({
                "mine_code": r.mine_code,
                "year": r.year,
                "availability_pct": avail,
                "downtime_pct": downtime,
                "target_mt": float(r.target_mt) if r.target_mt else None,
                "actual_production_mt": float(r.actual_production_mt),
                "variance_mt": float(r.variance_mt) if r.variance_mt else None,
            })
        return metrics

    @classmethod
    def get_authorized_mines(
        cls,
        db: Session,
        scope: AuthorizedScope,
    ) -> List[Mine]:
        """Returns list of canonical Mine entities the user is permitted to see."""
        stmt = select(Mine)
        if scope.allowed_mines is not None:
            if len(scope.allowed_mines) == 0:
                return []
            stmt = stmt.where(Mine.mine_code.in_(list(scope.allowed_mines)))
        stmt = stmt.order_by(Mine.mine_code)
        return list(db.scalars(stmt).all())

    @classmethod
    def get_equipment_fleet(
        cls,
        db: Session,
        scope: AuthorizedScope,
        mine_code: Optional[str] = None,
        equipment_type: Optional[str] = None,
        financial_year: Optional[str] = None,
    ) -> List[EquipmentFleet]:
        """Queries HEMM equipment fleet units with availability %, downtime, and operating hours."""
        if mine_code and not scope.is_mine_permitted(mine_code):
            return []

        stmt = select(EquipmentFleet)
        filters = []
        if mine_code:
            filters.append(EquipmentFleet.mine_code == mine_code)
        if equipment_type:
            filters.append(EquipmentFleet.equipment_type.ilike(f"%{equipment_type}%"))
        if financial_year:
            filters.append(EquipmentFleet.financial_year == financial_year)

        if filters:
            stmt = stmt.where(and_(*filters))

        scoped_stmt = AuthorizationService.scope_structured_query(stmt, EquipmentFleet, scope)
        scoped_stmt = scoped_stmt.order_by(EquipmentFleet.mine_code, EquipmentFleet.equipment_id)
        return list(db.scalars(scoped_stmt).all())

    @classmethod
    def get_safety_records(
        cls,
        db: Session,
        scope: AuthorizedScope,
        mine_code: Optional[str] = None,
        financial_year: Optional[str] = None,
        incident_type: Optional[str] = None,
        dgms_reportable: Optional[bool] = None,
    ) -> List[SafetyRecord]:
        """Queries safety incidents, injury counts, and DGMS statutory reportable notices."""
        if mine_code and not scope.is_mine_permitted(mine_code):
            return []

        stmt = select(SafetyRecord)
        filters = []
        if mine_code:
            filters.append(SafetyRecord.mine_code == mine_code)
        if financial_year:
            filters.append(SafetyRecord.financial_year == financial_year)
        if incident_type:
            filters.append(SafetyRecord.incident_type.ilike(f"%{incident_type}%"))
        if dgms_reportable is not None:
            filters.append(SafetyRecord.dgms_reportable == dgms_reportable)

        if filters:
            stmt = stmt.where(and_(*filters))

        scoped_stmt = AuthorizationService.scope_structured_query(stmt, SafetyRecord, scope)
        scoped_stmt = scoped_stmt.order_by(SafetyRecord.mine_code, SafetyRecord.financial_year.desc())
        return list(db.scalars(scoped_stmt).all())

    @classmethod
    def get_environmental_records(
        cls,
        db: Session,
        scope: AuthorizedScope,
        mine_code: Optional[str] = None,
        financial_year: Optional[str] = None,
    ) -> List[EnvironmentalRecord]:
        """Queries environmental parameters: PM10, PM2.5, water treatment, and plantation."""
        if mine_code and not scope.is_mine_permitted(mine_code):
            return []

        stmt = select(EnvironmentalRecord)
        filters = []
        if mine_code:
            filters.append(EnvironmentalRecord.mine_code == mine_code)
        if financial_year:
            filters.append(EnvironmentalRecord.financial_year == financial_year)

        if filters:
            stmt = stmt.where(and_(*filters))

        scoped_stmt = AuthorizationService.scope_structured_query(stmt, EnvironmentalRecord, scope)
        scoped_stmt = scoped_stmt.order_by(EnvironmentalRecord.mine_code, EnvironmentalRecord.financial_year.desc())
        return list(db.scalars(scoped_stmt).all())

    @classmethod
    def get_coal_seams(
        cls,
        db: Session,
        scope: AuthorizedScope,
        mine_code: Optional[str] = None,
    ) -> List[CoalSeam]:
        """Queries canonical coal seams with thickness and depth parameters."""
        if mine_code and not scope.is_mine_permitted(mine_code):
            return []

        stmt = select(CoalSeam)
        if mine_code:
            stmt = stmt.where(CoalSeam.mine_code == mine_code)

        scoped_stmt = AuthorizationService.scope_structured_query(stmt, CoalSeam, scope)
        scoped_stmt = scoped_stmt.order_by(CoalSeam.mine_code, CoalSeam.seam_id)
        return list(db.scalars(scoped_stmt).all())

    @classmethod
    def get_boreholes_and_intervals(
        cls,
        db: Session,
        scope: AuthorizedScope,
        mine_code: Optional[str] = None,
        borehole_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Queries drill holes and stratigraphic intervals."""
        if mine_code and not scope.is_mine_permitted(mine_code):
            return []

        stmt = select(BoreholeMaster)
        filters = []
        if mine_code:
            filters.append(BoreholeMaster.mine_code == mine_code)
        if borehole_id:
            filters.append(BoreholeMaster.borehole_id == borehole_id)

        if filters:
            stmt = stmt.where(and_(*filters))

        scoped_stmt = AuthorizationService.scope_structured_query(stmt, BoreholeMaster, scope)
        scoped_stmt = scoped_stmt.order_by(BoreholeMaster.mine_code, BoreholeMaster.borehole_id)
        masters = list(db.scalars(scoped_stmt).all())

        results = []
        for bm in masters:
            intervals = db.scalars(
                select(BoreholeInterval)
                .where(BoreholeInterval.borehole_id == bm.borehole_id)
                .order_by(BoreholeInterval.interval_no)
            ).all()
            results.append({
                "borehole_id": bm.borehole_id,
                "mine_code": bm.mine_code,
                "total_depth_m": bm.total_depth_m,
                "rl_m": bm.rl_m,
                "status": bm.status,
                "intervals_count": len(intervals),
                "seams_intersected": list(set(iv.coal_seam for iv in intervals if iv.coal_seam)),
            })
        return results

    @classmethod
    def get_geotechnical_zones(
        cls,
        db: Session,
        scope: AuthorizedScope,
        mine_code: Optional[str] = None,
        risk_class: Optional[str] = None,
    ) -> List[GeotechnicalZone]:
        """Queries geotechnical risk zones with slope stability classifications."""
        if mine_code and not scope.is_mine_permitted(mine_code):
            return []

        stmt = select(GeotechnicalZone)
        filters = []
        if mine_code:
            filters.append(GeotechnicalZone.mine_code == mine_code)
        if risk_class:
            filters.append(GeotechnicalZone.risk_class == risk_class)

        if filters:
            stmt = stmt.where(and_(*filters))

        scoped_stmt = AuthorizationService.scope_structured_query(stmt, GeotechnicalZone, scope)
        scoped_stmt = scoped_stmt.order_by(GeotechnicalZone.mine_code, GeotechnicalZone.zone_id)
        return list(db.scalars(scoped_stmt).all())
