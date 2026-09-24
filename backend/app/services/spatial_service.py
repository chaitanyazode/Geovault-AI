"""
GeoVault AI - PostGIS Spatial Intelligence Service
Executes deterministic geospatial operations:
- ST_DWithin (proximity filtering in meters)
- ST_Distance (geodesic distance calculations)
- ST_Intersects (spatial intersections between drill holes, seams, faults)
- ST_Contains (containment queries)
- High-risk geotechnical zone identification

Strictly enforces 'Authorization Before Retrieval' via AuthorizedScope.
Never allows LLM to invent coordinates or calculate spatial distances.
"""

from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import text, select, func
from geoalchemy2.functions import ST_Distance, ST_DWithin, ST_Intersects, ST_Contains

from app.security.context import AuthorizedScope
from app.models.spatial import (
    SpatialBorehole,
    SpatialBoreholeInterval,
    SpatialBoreholeTrace,
    SpatialCoalSeamBelt,
    SpatialGeologicalContact,
    SpatialGeologicalUnit,
    SpatialGeotechnicalZone,
    SpatialLanduse,
    SpatialSurveyPoint,
    SpatialGeologicalEvent,
)
from app.schemas.query import EvidenceItem


class SpatialIntelligenceService:
    """
    Dedicated PostGIS spatial analysis service.
    Enforces authorization prior to executing any spatial query.
    """

    @classmethod
    def _verify_mine_auth(cls, scope: AuthorizedScope, mine_code: Optional[str]) -> bool:
        """Verifies if the target mine is permitted under user's scope."""
        if mine_code is None:
            return True
        return scope.is_mine_permitted(mine_code)

    @classmethod
    def query_boreholes_near_events(
        cls,
        db: Session,
        scope: AuthorizedScope,
        mine_code: Optional[str] = None,
        distance_meters: float = 500.0,
        event_severity: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        PostGIS ST_DWithin query:
        Finds boreholes within distance_meters of recorded geological events.
        """
        if mine_code and not cls._verify_mine_auth(scope, mine_code):
            return []

        # Scope filters
        params: Dict[str, Any] = {"dist": distance_meters}
        where_clauses = ["ST_DWithin(b.geom::geography, e.geom::geography, :dist)"]

        if mine_code:
            where_clauses.append("b.mine_code = :mine_code")
            where_clauses.append("e.mine_code = :mine_code")
            params["mine_code"] = mine_code
        elif scope.allowed_mines is not None:
            where_clauses.append("b.mine_code = ANY(:allowed_mines)")
            where_clauses.append("e.mine_code = ANY(:allowed_mines)")
            params["allowed_mines"] = list(scope.allowed_mines)

        if event_severity:
            where_clauses.append("e.severity ILIKE :severity")
            params["severity"] = event_severity

        sql = f"""
            SELECT 
                b.mine_code,
                b.borehole_id,
                b.depth_m,
                b.lithology,
                e.event_id,
                e.event_type,
                e.severity,
                e.area,
                ROUND(ST_Distance(b.geom::geography, e.geom::geography)::numeric, 2) as distance_meters,
                ST_X(b.geom) as longitude,
                ST_Y(b.geom) as latitude
            FROM spatial_boreholes b
            JOIN spatial_geological_events e ON b.mine_code = e.mine_code
            WHERE {" AND ".join(where_clauses)}
            ORDER BY distance_meters ASC
        """

        results = db.execute(text(sql), params).mappings().all()
        return [dict(r) for r in results]

    @classmethod
    def query_boreholes_intersecting_seams(
        cls,
        db: Session,
        scope: AuthorizedScope,
        mine_code: Optional[str] = None,
        seam_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        PostGIS ST_Intersects query:
        Finds boreholes that spatially intersect coal seam polygon belts.
        """
        if mine_code and not cls._verify_mine_auth(scope, mine_code):
            return []

        params: Dict[str, Any] = {}
        where_clauses = ["ST_Intersects(b.geom, s.geom)"]

        if mine_code:
            where_clauses.append("b.mine_code = :mine_code")
            where_clauses.append("s.mine_code = :mine_code")
            params["mine_code"] = mine_code
        elif scope.allowed_mines is not None:
            where_clauses.append("b.mine_code = ANY(:allowed_mines)")
            where_clauses.append("s.mine_code = ANY(:allowed_mines)")
            params["allowed_mines"] = list(scope.allowed_mines)

        if seam_id:
            where_clauses.append("s.seam_id ILIKE :seam_id")
            params["seam_id"] = f"%{seam_id}%"

        sql = f"""
            SELECT 
                b.mine_code,
                b.borehole_id,
                s.seam_id,
                s.width_m as seam_belt_width_m,
                b.depth_m as borehole_depth_m,
                b.lithology,
                ST_X(b.geom) as longitude,
                ST_Y(b.geom) as latitude
            FROM spatial_boreholes b
            JOIN spatial_coal_seam_belts s ON b.mine_code = s.mine_code
            WHERE {" AND ".join(where_clauses)}
            ORDER BY b.mine_code, s.seam_id, b.borehole_id
        """

        results = db.execute(text(sql), params).mappings().all()
        return [dict(r) for r in results]

    @classmethod
    def query_high_risk_geotechnical_zones(
        cls,
        db: Session,
        scope: AuthorizedScope,
        mine_code: Optional[str] = None,
        min_risk_level: str = "HIGH",
    ) -> List[Dict[str, Any]]:
        """
        Queries geotechnical zones with high risk, calculating contained/intersecting
        survey stations and boreholes.
        """
        if mine_code and not cls._verify_mine_auth(scope, mine_code):
            return []

        params: Dict[str, Any] = {"risk": min_risk_level}
        where_clauses = ["z.risk_class ILIKE :risk"]

        if mine_code:
            where_clauses.append("z.mine_code = :mine_code")
            params["mine_code"] = mine_code
        elif scope.allowed_mines is not None:
            where_clauses.append("z.mine_code = ANY(:allowed_mines)")
            params["allowed_mines"] = list(scope.allowed_mines)

        sql = f"""
            SELECT 
                z.mine_code,
                z.zone_id,
                z.zone_type,
                z.risk_class,
                ROUND(ST_Area(z.geom::geography)::numeric, 2) as area_sq_meters,
                (
                    SELECT COUNT(*)
                    FROM spatial_boreholes b
                    WHERE b.mine_code = z.mine_code AND ST_Intersects(b.geom, z.geom)
                ) as intersecting_boreholes_count,
                (
                    SELECT COUNT(*)
                    FROM spatial_survey_points p
                    WHERE p.mine_code = z.mine_code AND ST_Intersects(p.geom, z.geom)
                ) as contained_survey_points_count
            FROM spatial_geotechnical_zones z
            WHERE {" AND ".join(where_clauses)}
            ORDER BY z.mine_code, z.zone_id
        """

        results = db.execute(text(sql), params).mappings().all()
        return [dict(r) for r in results]

    @classmethod
    def query_nearest_features(
        cls,
        db: Session,
        scope: AuthorizedScope,
        mine_code: str,
        source_type: str = "borehole",
        target_type: str = "geotechnical_zone",
        limit: int = 5,
    ) -> List[Dict[str, Any]]:
        """
        PostGIS ST_Distance nearest-neighbor query between spatial layers.
        """
        if not cls._verify_mine_auth(scope, mine_code):
            return []

        sql = """
            SELECT 
                b.mine_code,
                b.borehole_id as origin_feature_id,
                z.zone_id as target_feature_id,
                z.zone_type as target_type,
                z.risk_class as target_risk,
                ROUND(ST_Distance(b.geom::geography, z.geom::geography)::numeric, 2) as distance_meters
            FROM spatial_boreholes b
            CROSS JOIN spatial_geotechnical_zones z
            WHERE b.mine_code = :mine_code AND z.mine_code = :mine_code
            ORDER BY distance_meters ASC
            LIMIT :limit
        """
        results = db.execute(text(sql), {"mine_code": mine_code, "limit": limit}).mappings().all()
        return [dict(r) for r in results]

    @classmethod
    def build_spatial_evidence(cls, spatial_records: List[Dict[str, Any]], layer_name: str) -> List[EvidenceItem]:
        """Translates PostGIS query outputs into traceable, standard EvidenceItem objects."""
        items: List[EvidenceItem] = []
        for idx, rec in enumerate(spatial_records):
            mcode = rec.get("mine_code", "UNKNOWN")
            feat_id = rec.get("borehole_id") or rec.get("zone_id") or rec.get("event_id") or f"FEAT-{idx+1}"
            ev_id = f"EV-SPATIAL-{mcode}-{feat_id}"

            # Format descriptive snippet
            parts = []
            for k, v in rec.items():
                if k not in ["mine_code"] and v is not None:
                    parts.append(f"{k}: {v}")
            snippet = f"[Spatial Layer: {layer_name} | {mcode}] " + ", ".join(parts)

            citation = f"PostGIS Spatial Database ({layer_name}) | {mcode} | {feat_id}"

            items.append(
                EvidenceItem(
                    evidence_id=ev_id,
                    source_type="POSTGIS_SPATIAL",
                    source_name=layer_name,
                    record_id=feat_id,
                    document_id=None,
                    page_number=None,
                    mine_code=mcode,
                    department="Geology",
                    classification="INTERNAL",
                    citation=citation,
                    raw_data=rec,
                    snippet=snippet,
                )
            )
        return items
