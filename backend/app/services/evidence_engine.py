"""
GeoVault AI - Dedicated Evidence Engine
Translates structured database rows and unstructured document chunks
into traceable, verifiable EvidenceItem models with standardized citations.
"""

from typing import List, Dict, Any, Optional
from app.schemas.query import EvidenceItem


class EvidenceEngine:
    """
    Enforces complete source traceability.
    Every factual claim is grounded in a specific table/record or document/page.
    """

    DEPARTMENT_MAP = {
        "production_annual": "Mining",
        "production_monthly": "Mining",
        "equipment_fleet": "Mining",
        "safety_records": "Safety",
        "environmental_records": "Environment",
        "coal_seams": "Geology",
        "boreholes_master": "Geology",
        "geotechnical_zones": "Geology",
        "survey_points": "Survey",
        "cross_section_points": "Survey",
        "qa_benchmarks": "Mining",
        "dispatch_summary": "Transportation",
        "coal_quality": "Mining",
        "geological_units": "Geology",
        "mining_issue_log": "Mining",
        "inspection_register": "Safety",
    }

    HUMAN_SOURCE_MAP = {
        "production_annual": "Annual Production Register",
        "production_monthly": "Monthly Production Register",
        "equipment_fleet": "HEMM Fleet Operational Register",
        "safety_records": "DGMS & Internal Safety Incident Register",
        "environmental_records": "Environmental Monitoring Compliance Register",
        "coal_seams": "Geological Coal Seam Master",
        "boreholes_master": "CMPDI Exploratory Drilling Master",
        "geotechnical_zones": "Geotechnical Risk & Slope Stability Database",
        "survey_points": "Mine Geodetic Survey Ground Stations",
        "cross_section_points": "Pit Cross-Section Survey Profile",
        "qa_benchmarks": "CMPDI Grounding Benchmarks",
        "dispatch_summary": "Dispatch & Logistics Summary",
        "coal_quality": "Coal Quality Analysis",
        "geological_units": "Geomechanical & Strata Database",
        "mining_issue_log": "Operational Issue Log",
        "inspection_register": "Statutory Inspection Register",
    }

    @classmethod
    def from_structured_record(cls, record: Any, domain: str) -> EvidenceItem:
        """Converts a single SQLAlchemy operational model instance into an EvidenceItem."""
        # Convert record to dictionary
        if isinstance(record, dict):
            data = record
        else:
            data = {c.name: getattr(record, c.name) for c in record.__table__.columns}

        record_id = str(data.get("id", data.get("equipment_id", data.get("borehole_id", data.get("seam_id", "0")))))
        mine_code = data.get("mine_code")
        year = data.get("year")
        fy = data.get("financial_year")
        month = data.get("month")

        dept = cls.DEPARTMENT_MAP.get(domain, "Mining")
        human_source = cls.HUMAN_SOURCE_MAP.get(domain, domain.replace("_", " ").title())

        # Generate deterministic globally unique evidence ID
        if year and month:
            ev_id = f"EV-{domain.upper()[:12]}-{mine_code}-{year}-M{month:02d}"
        elif fy:
            fy_clean = str(fy).replace(" ", "").replace("-", "")
            ev_id = f"EV-{domain.upper()[:12]}-{mine_code}-{fy_clean}-{record_id}"
        elif year:
            ev_id = f"EV-{domain.upper()[:12]}-{mine_code}-{year}"
        else:
            ev_id = f"EV-{domain.upper()[:12]}-{mine_code}-{record_id}"

        # Generate standard citation
        time_part = f"{fy}" if fy else (f"FY{year}" if year else "N/A")
        if month:
            time_part += f" M{month:02d}"
        citation = f"{human_source} ({domain}) | {mine_code or 'ALL'} | {time_part}"

        # Format human-readable snippet
        snippet_parts = []
        if "actual_production_mt" in data:
            snippet_parts.append(f"Actual: {data['actual_production_mt']} MT")
        if "production_mt" in data:
            snippet_parts.append(f"Production: {data['production_mt']} MT")
        if "target_mt" in data and data["target_mt"] is not None:
            snippet_parts.append(f"Target: {data['target_mt']} MT")
        if "variance_mt" in data and data["variance_mt"] is not None:
            snippet_parts.append(f"Variance: {data['variance_mt']:+} MT")
        if "dispatch_mt" in data:
            snippet_parts.append(f"Dispatch: {data['dispatch_mt']} MT")
        if "ash_pct" in data:
            snippet_parts.append(f"Ash: {data['ash_pct']}%")
        if "unit" in data:
            snippet_parts.append(f"Unit: {data['unit']}, Risk: {data.get('geological_risk')}")
        if "equipment_type" in data:
            snippet_parts.append(f"HEMM: {data.get('equipment_id', '')} ({data['equipment_type']}), Avail: {data.get('availability_pct')}%")
        if "incident_type" in data:
            snippet_parts.append(f"Incident: {data['incident_type']}, Severity: {data.get('severity')}, DGMS Reportable: {data.get('dgms_reportable')}")
        if "pm10_ug_m3" in data:
            snippet_parts.append(f"PM10: {data['pm10_ug_m3']} ug/m3, Water Discharge pH: {data.get('water_discharge_ph')}")
        if "seam_id" in data:
            snippet_parts.append(f"Seam: {data['seam_id']}, Avg Thickness: {data.get('avg_thickness_m')}m")
        if "total_depth_m" in data and "collar_rl_m" in data:
            snippet_parts.append(f"Borehole Depth: {data['total_depth_m']}m, RL: {data.get('collar_rl_m')}m")
        if "zone_type" in data:
            snippet_parts.append(f"Zone: {data.get('zone_id')}, Risk: {data.get('risk_class')}")
        if "observed_issue" in data:
            snippet_parts.append(f"Issue: {data['observed_issue']}")
        if "inspection_focus" in data:
            snippet_parts.append(f"Focus: {data['inspection_focus']}, Status: {data.get('status')}")

        snippet = f"[{mine_code} {time_part}] " + ", ".join(snippet_parts) if snippet_parts else str(data)

        return EvidenceItem(
            evidence_id=ev_id,
            source_type="STRUCTURED_RECORD",
            source_name=domain,
            record_id=record_id,
            document_id=None,
            page_number=None,
            mine_code=mine_code,
            department=dept,
            classification="INTERNAL",
            citation=citation,
            raw_data=data,
            snippet=snippet,
        )

    @classmethod
    def from_structured_records(cls, records: List[Any], domain: str) -> List[EvidenceItem]:
        """Converts a list of records into evidence items."""
        return [cls.from_structured_record(r, domain) for r in records]

    @classmethod
    def from_spatial_record(cls, record: Dict[str, Any], layer_name: str) -> EvidenceItem:
        """Converts a PostGIS spatial result into a traceable EvidenceItem."""
        mcode = record.get("mine_code", "UNKNOWN")
        feat_id = str(record.get("borehole_id") or record.get("zone_id") or record.get("event_id") or record.get("seam_id") or "FEATURE")
        ev_id = f"EV-SPATIAL-{mcode}-{feat_id}"
        citation = f"PostGIS Spatial Database ({layer_name}) | {mcode} | {feat_id}"

        snippet_parts = [f"{k}: {v}" for k, v in record.items() if k not in ["mine_code"] and v is not None]
        snippet = f"[Spatial Layer: {layer_name} | {mcode}] " + ", ".join(snippet_parts)

        return EvidenceItem(
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
            raw_data=record,
            snippet=snippet,
        )

    @classmethod
    def from_document_chunk(cls, chunk: Any) -> EvidenceItem:
        """Converts a DocumentChunk model into an EvidenceItem."""
        cid = getattr(chunk, "chunk_id", "0")
        doc_id = getattr(chunk, "document_id", "DOC")
        page_no = getattr(chunk, "page_number", 1)
        mine_code = getattr(chunk, "mine_code", None)
        dept = getattr(chunk, "department", "Mining")
        classification = getattr(chunk, "classification", "INTERNAL")
        chunk_text = getattr(chunk, "chunk_text", "")

        citation = f"{doc_id} — Page {page_no}"
        if mine_code:
            citation += f" | {mine_code}"

        return EvidenceItem(
            evidence_id=getattr(chunk, "chunk_id", f"{doc_id}-P{page_no}"),
            source_type="DOCUMENT_CHUNK",
            source_name=doc_id,
            record_id=None,
            document_id=doc_id,
            page_number=page_no,
            mine_code=mine_code,
            department=dept,
            classification=classification,
            citation=citation,
            raw_data=None,
            snippet=chunk_text[:300],
        )

    @classmethod
    def from_document_chunks(cls, chunks: List[Any]) -> List[EvidenceItem]:
        """Converts a list of document chunks into evidence items."""
        return [cls.from_document_chunk(c) for c in chunks]
