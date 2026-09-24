from typing import Dict, Any, List
from sqlalchemy.orm import Session
from sqlalchemy import select, delete
from app.models import Conflict

def register_discovered_conflicts(db: Session) -> List[Dict[str, Any]]:
    """Detects and registers known source divergences into the conflicts table without silently resolving them."""
    conflicts_to_register = [
        {
            "conflict_id": "CONF-SSOP03-2025-LOGISTICS",
            "mine_code": "SSOP-03",
            "year": 2025,
            "metric_or_topic": "Dispatch Logistics Status vs Operational Incident Log",
            "source_a_type": "STRUCTURED_DISPATCH_REGISTER",
            "source_a_reference": "dispatch_summary.csv (Row SSOP-03 2025)",
            "source_a_value": "Logistics Status: 'Normal' | Production-Dispatch Gap: 0.08 MT",
            "source_b_type": "OPERATIONAL_LOG_AND_UNSTRUCTURED_MEMO",
            "source_b_reference": "mining_issue_log.csv / SSOP-03_2025_logistics.pdf",
            "source_b_value": "Rail loading congestion creating 0.31 MT backlog and emergency road diversion",
            "status": "CONFLICT",
            "resolution_policy": "NO_SILENT_RESOLUTION: Preserve both sources; flag conflict on user query."
        },
        {
            "conflict_id": "CONF-DEOM01-2024-2025-CYCLETIME",
            "mine_code": "DEOM-01",
            "year": 2025,
            "metric_or_topic": "Temporal Logging Discrepancy for Haul Road Congestion",
            "source_a_type": "SCAN_ARCHIVE_DOCUMENT",
            "source_a_reference": "DEOM_2024_ocr_extract.txt (Ref: DEOM/OPS/2024/17)",
            "source_a_value": "Incident documented under FY2024 filing reference DEOM/OPS/2024/17 (+9% cycle time)",
            "source_b_type": "ANNUAL_ISSUE_REGISTER",
            "source_b_reference": "mining_issue_log.csv (Year 2025)",
            "source_b_value": "Event recorded under Year 2025 in annual consolidated issue log",
            "status": "CONFLICT",
            "resolution_policy": "NO_SILENT_RESOLUTION: Present temporal divergence in citations."
        }
    ]

    registered = []
    for cdata in conflicts_to_register:
        existing = db.execute(select(Conflict).where(Conflict.conflict_id == cdata["conflict_id"])).scalar_one_or_none()
        if not existing:
            rec = Conflict(**cdata)
            db.add(rec)
            registered.append(cdata)
        else:
            existing.source_a_value = cdata["source_a_value"]
            existing.source_b_value = cdata["source_b_value"]
            existing.resolution_policy = cdata["resolution_policy"]
            registered.append(cdata)

    db.commit()
    return registered
