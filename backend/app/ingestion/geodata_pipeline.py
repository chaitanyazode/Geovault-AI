"""
GeoVault AI - Controlled Ingestion & ETL Service for New Dataset
Supports full 5-mine ingestion (GEVRA, KUSMUNDA, DIPKA, NIGAHI, DUDHICHUA),
PostGIS spatial loading from GeoPackage (971 features across 50 layers),
deterministic relational extraction, page-aware PDF chunking, OCR scanning,
and BGE-M3 embeddings.
"""

import os
import re
import sys
import time
import glob
import logging
from typing import Dict, Any, List, Optional
import pandas as pd
import geopandas as gpd
from shapely.geometry import mapping
from geoalchemy2.shape import from_shape
from sqlalchemy.orm import Session
from sqlalchemy import select, func, delete

from app.core.database import SessionLocal
from app.models import (
    Subsidiary,
    Mine,
    ProductionAnnual,
    EquipmentFleet,
    SafetyRecord,
    EnvironmentalRecord,
    BoreholeMaster,
    BoreholeInterval,
    CoalSeam,
    GeologicalEvent,
    GeotechnicalZone,
    SurveyPoint,
    CrossSectionPoint,
    QABenchmark,
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
    Document,
    DocumentChunk,
    Evidence,
    UserScope,
)
from app.ingestion.hasher import compute_file_sha256
from app.ingestion.unstructured import get_embedding_model, chunk_text_page

logger = logging.getLogger("geovault.ingestion.geodata")
logging.basicConfig(level=logging.INFO)

CANONICAL_MINES = [
    {
        "mine_id": "GV001",
        "mine_code": "GEVRA",
        "mine_name": "Gevra OCP",
        "subsidiary_id": "SECL",
        "district": "Korba",
        "state": "Chhattisgarh",
        "coalfield": "Korba Coalfield",
        "mine_type": "Opencast",
        "lat": 22.3333,
        "lon": 82.5833,
    },
    {
        "mine_id": "GV002",
        "mine_code": "KUSMUNDA",
        "mine_name": "Kusmunda OCP",
        "subsidiary_id": "SECL",
        "district": "Korba",
        "state": "Chhattisgarh",
        "coalfield": "Korba Coalfield",
        "mine_type": "Opencast",
        "lat": 22.3167,
        "lon": 82.6833,
    },
    {
        "mine_id": "GV003",
        "mine_code": "DIPKA",
        "mine_name": "Dipka OCP",
        "subsidiary_id": "SECL",
        "district": "Korba",
        "state": "Chhattisgarh",
        "coalfield": "Korba Coalfield",
        "mine_type": "Opencast",
        "lat": 22.3167,
        "lon": 82.5667,
    },
    {
        "mine_id": "GV004",
        "mine_code": "NIGAHI",
        "mine_name": "Nigahi OCP",
        "subsidiary_id": "NCL",
        "district": "Singrauli",
        "state": "Madhya Pradesh",
        "coalfield": "Singrauli Coalfield",
        "mine_type": "Opencast",
        "lat": 24.1167,
        "lon": 82.6167,
    },
    {
        "mine_id": "GV005",
        "mine_code": "DUDHICHUA",
        "mine_name": "Dudhichua OCP",
        "subsidiary_id": "NCL",
        "district": "Singrauli",
        "state": "Uttar Pradesh",
        "coalfield": "Singrauli Coalfield",
        "mine_type": "Opencast",
        "lat": 24.1333,
        "lon": 82.6833,
    },
]


class GeoDataIngestionService:
    @staticmethod
    def load_all_operational(session: Session, geo_data_dir: str = "/data/geo_data") -> Dict[str, int]:
        """Loads master profiles, annual facts, equipment, safety, environment, and QA benchmarks for all 5 mines."""
        counts = {
            "mines": 0,
            "production_annual": 0,
            "equipment_fleet": 0,
            "safety_records": 0,
            "environmental_records": 0,
            "qa_benchmarks": 0,
        }
        master_file = os.path.join(geo_data_dir, "Excel/GeoVault_Synthetic_Master_Dataset.xlsx")

        # 1. Ensure SECL and NCL exist in subsidiaries
        for sub_id, sub_name in [("SECL", "South Eastern Coalfields Limited"), ("NCL", "Northern Coalfields Limited")]:
            sub = session.scalar(select(Subsidiary).where(Subsidiary.subsidiary_id == sub_id))
            if not sub:
                session.add(Subsidiary(subsidiary_id=sub_id, subsidiary_name=sub_name))
        session.flush()

        # 2. Mine Profiles for all 5 canonical mines
        df_mine = pd.read_excel(master_file, sheet_name="Mine_Profile")
        for m_meta in CANONICAL_MINES:
            mid = m_meta["mine_id"]
            mcode = m_meta["mine_code"]
            matched_row = df_mine[df_mine["Mine_ID"] == mid]
            row_dict = matched_row.iloc[0].to_dict() if len(matched_row) > 0 else {}

            mine = session.scalar(select(Mine).where(Mine.mine_code == mcode))
            if not mine:
                mine = Mine(
                    mine_code=mcode,
                    mine_id=mid,
                    mine_name=m_meta["mine_name"],
                    subsidiary_id=m_meta["subsidiary_id"],
                    state=str(row_dict.get("State", m_meta["state"])),
                    district=str(row_dict.get("District", m_meta["district"])),
                    coalfield=str(row_dict.get("Coalfield", m_meta["coalfield"])),
                    latitude=m_meta["lat"],
                    longitude=m_meta["lon"],
                    mine_type=str(row_dict.get("Mine_Type", m_meta["mine_type"])),
                    provenance_type="SYNTHETIC_DEMO"
                )
                session.add(mine)
                counts["mines"] += 1
            else:
                mine.mine_id = mid
                mine.state = str(row_dict.get("State", m_meta["state"]))
                mine.district = str(row_dict.get("District", m_meta["district"]))
                mine.coalfield = str(row_dict.get("Coalfield", m_meta["coalfield"]))
                mine.latitude = m_meta["lat"]
                mine.longitude = m_meta["lon"]
                mine.provenance_type = "SYNTHETIC_DEMO"
        session.flush()

        # 3. Production Annual (30 rows total, 6 per mine)
        df_facts = pd.read_excel(master_file, sheet_name="Mine_Year_Facts")
        mine_id_to_code = {m["mine_id"]: m["mine_code"] for m in CANONICAL_MINES}

        for _, r in df_facts.iterrows():
            mid = str(r["Mine_ID"]).strip()
            if mid not in mine_id_to_code:
                continue
            mcode = mine_id_to_code[mid]
            fy = str(r["Financial_Year"]).strip()
            year_match = re.search(r"20(\d\d)", fy)
            cal_year = int(f"20{year_match.group(1)}") if year_match else 2024

            existing = session.scalar(
                select(ProductionAnnual).where(
                    ProductionAnnual.mine_code == mcode,
                    ProductionAnnual.financial_year == fy
                )
            )
            if not existing:
                prod = ProductionAnnual(
                    mine_code=mcode,
                    year=cal_year,
                    financial_year=fy,
                    target_mt=float(r["Production_Target_MT"]),
                    actual_production_mt=float(r["Actual_Production_MT"]),
                    variance_mt=float(r["Production_Variance_MT"]) if pd.notna(r.get("Production_Variance_MT")) else None,
                    dispatch_mt=float(r["Actual_Offtake_MT"]) if pd.notna(r.get("Actual_Offtake_MT")) else float(r["Actual_Production_MT"]),
                    achievement_pct=float(r["Achievement_%"]) if pd.notna(r.get("Achievement_%")) else None,
                    yoy_growth_pct=float(r["YoY_Growth_%"]) if pd.notna(r.get("YoY_Growth_%")) else None,
                    target_ob_mcu_m=float(r["Target_OB_Removal_McuM"]) if pd.notna(r.get("Target_OB_Removal_McuM")) else None,
                    actual_ob_mcu_m=float(r["Actual_OB_Removal_McuM"]) if pd.notna(r.get("Actual_OB_Removal_McuM")) else None,
                    stripping_ratio_target=float(r["Stripping_Ratio_Target"]) if pd.notna(r.get("Stripping_Ratio_Target")) else None,
                    stripping_ratio_actual=float(r["Stripping_Ratio_Actual"]) if pd.notna(r.get("Stripping_Ratio_Actual")) else None,
                    manpower_available=int(r["Manpower_Available"]) if pd.notna(r.get("Manpower_Available")) else None,
                    hemm_availability_pct=float(r["HEMM_Availability_%"]) if pd.notna(r.get("HEMM_Availability_%")) else None,
                    downtime_hours=float(r["Downtime_Hours"]) if pd.notna(r.get("Downtime_Hours")) else None,
                    rainfall_impact_days=int(r["Rainfall_Impact_Days"]) if pd.notna(r.get("Rainfall_Impact_Days")) else None,
                    safety_incident_count=int(r["Safety_Incident_Count"]) if pd.notna(r.get("Safety_Incident_Count")) else None,
                    ltifr=float(r["LTIFR"]) if pd.notna(r.get("LTIFR")) else None,
                    fatalities=int(r["Fatalities"]) if pd.notna(r.get("Fatalities")) else 0,
                    reclamation_ha=float(r["Reclamation_Ha"]) if pd.notna(r.get("Reclamation_Ha")) else None,
                    mine_water_treated_ml=float(r["Mine_Water_Treated_ML"]) if pd.notna(r.get("Mine_Water_Treated_ML")) else None,
                    dust_compliance_pct=float(r["Dust_Compliance_%"]) if pd.notna(r.get("Dust_Compliance_%")) else None,
                    primary_cause_of_shortfall=str(r.get("Primary_Cause_of_Shortfall", "")) if pd.notna(r.get("Primary_Cause_of_Shortfall")) else None,
                    geological_observation=str(r.get("Geological_Observation", "")) if pd.notna(r.get("Geological_Observation")) else None,
                    provenance_type="SYNTHETIC_DEMO"
                )
                session.add(prod)
                counts["production_annual"] += 1
        session.flush()

        # 4. Equipment Fleet (150 rows total, 30 per mine)
        df_eq = pd.read_excel(master_file, sheet_name="Equipment")
        for idx, r in df_eq.iterrows():
            mid = str(r["Mine_ID"]).strip()
            if mid not in mine_id_to_code:
                continue
            mcode = mine_id_to_code[mid]
            eq_type = str(r["Equipment_Type"]).strip()
            fy = str(r["Financial_Year"]).strip()
            eq_id = f"EQ-{mcode}-{eq_type.upper()[:4]}-{fy}"

            existing_eq = session.scalar(
                select(EquipmentFleet).where(
                    EquipmentFleet.mine_code == mcode,
                    EquipmentFleet.equipment_id == eq_id,
                    EquipmentFleet.financial_year == fy
                )
            )
            if not existing_eq:
                eq_record = EquipmentFleet(
                    equipment_id=eq_id,
                    mine_code=mcode,
                    financial_year=fy,
                    equipment_type=eq_type,
                    availability_pct=float(r["Availability_%"]) if pd.notna(r.get("Availability_%")) else None,
                    downtime_hours=float(r["Downtime_%"]) if pd.notna(r.get("Downtime_%")) else None,
                    status="OPERATIONAL",
                    provenance_type="SYNTHETIC_DEMO"
                )
                session.add(eq_record)
                counts["equipment_fleet"] += 1
        session.flush()

        # 5. Safety Records (30 rows total, 6 per mine)
        df_safe = pd.read_excel(master_file, sheet_name="Safety")
        for _, r in df_safe.iterrows():
            mid = str(r["Mine_ID"]).strip()
            if mid not in mine_id_to_code:
                continue
            mcode = mine_id_to_code[mid]
            fy = str(r["Financial_Year"]).strip()
            inc_id = f"SAFE-{mcode}-{fy}"

            existing_safe = session.scalar(
                select(SafetyRecord).where(
                    SafetyRecord.mine_code == mcode,
                    SafetyRecord.incident_id == inc_id,
                    SafetyRecord.financial_year == fy
                )
            )
            if not existing_safe:
                safe_rec = SafetyRecord(
                    incident_id=inc_id,
                    mine_code=mcode,
                    financial_year=fy,
                    incident_type="Annual Operational Safety Summary",
                    severity="FATALITY" if int(r.get("Fatalities", 0)) > 0 else "NON_FATAL",
                    description=f"Incidents: {r.get('Safety_Incident_Count', 0)}, LTIFR: {r.get('LTIFR', 0)}, PPE: {r.get('PPE_Compliance_%', 0)}%",
                    corrective_action=str(r.get("Safety_Action", "Monthly safety review and compliance checks")),
                    dgms_reportable=bool(int(r.get("Fatalities", 0)) > 0),
                    provenance_type="SYNTHETIC_DEMO"
                )
                session.add(safe_rec)
                counts["safety_records"] += 1
        session.flush()

        # 6. Environmental Records (30 rows total, 6 per mine)
        df_env = pd.read_excel(master_file, sheet_name="Environment")
        for _, r in df_env.iterrows():
            mid = str(r["Mine_ID"]).strip()
            if mid not in mine_id_to_code:
                continue
            mcode = mine_id_to_code[mid]
            fy = str(r["Financial_Year"]).strip()
            rec_id = f"ENV-{mcode}-{fy}"

            existing_env = session.scalar(
                select(EnvironmentalRecord).where(
                    EnvironmentalRecord.mine_code == mcode,
                    EnvironmentalRecord.record_id == rec_id,
                    EnvironmentalRecord.financial_year == fy
                )
            )
            if not existing_env:
                env_rec = EnvironmentalRecord(
                    record_id=rec_id,
                    mine_code=mcode,
                    financial_year=fy,
                    water_treated_ml=float(r["Water_Treated_ML"]) if pd.notna(r.get("Water_Treated_ML")) else None,
                    reclamation_ha=float(r["Reclamation_Ha"]) if pd.notna(r.get("Reclamation_Ha")) else None,
                    compliance_status="COMPLIANT" if float(r.get("Dust_Compliance_%", 100)) >= 90 else "ACTION_REQUIRED",
                    provenance_type="SYNTHETIC_DEMO"
                )
                session.add(env_rec)
                counts["environmental_records"] += 1
        session.flush()

        # 7. QA Benchmarks (150 rows total, 30 per mine)
        for m_meta in CANONICAL_MINES:
            mcode = m_meta["mine_code"]
            m_geo_file = os.path.join(geo_data_dir, f"Geological/mines/{mcode}/{mcode}_Geological_Dataset_FINAL.xlsx")
            if not os.path.exists(m_geo_file):
                logger.warning(f"Geological excel not found for {mcode}: {m_geo_file}")
                continue

            df_qa = pd.read_excel(m_geo_file, sheet_name="QA_Test_Cases")
            for _, r in df_qa.iterrows():
                qa_id = str(r["QA_ID"]).strip()
                existing_qa = session.scalar(select(QABenchmark).where(QABenchmark.qa_id == qa_id))
                if not existing_qa:
                    qa_rec = QABenchmark(
                        qa_id=qa_id,
                        mine_code=mcode,
                        question=str(r["Question"]).strip(),
                        expected_source=str(r.get("Expected_Source", "")).strip(),
                        expected_operation=str(r.get("Expected_Operation", "")).strip(),
                        expected_key=str(r["Expected_Key"]).strip() if pd.notna(r.get("Expected_Key")) else None,
                        expected_value=str(r["Expected_Value"]).strip(),
                        answer_type=str(r.get("Answer_Type", "text")).strip(),
                        data_type="SYNTHETIC_TEST_CASE"
                    )
                    session.add(qa_rec)
                    counts["qa_benchmarks"] += 1
        session.flush()

        return counts

    @staticmethod
    def load_all_geological(session: Session, geo_data_dir: str = "/data/geo_data") -> Dict[str, int]:
        """Loads boreholes, intervals, seams, events, geotechnical zones, survey points, and cross-sections for all 5 mines."""
        counts = {
            "boreholes_master": 0,
            "borehole_intervals": 0,
            "coal_seams": 0,
            "geological_events": 0,
            "geotechnical_zones": 0,
            "survey_points": 0,
            "cross_section_points": 0,
        }

        for m_meta in CANONICAL_MINES:
            mid = m_meta["mine_id"]
            mcode = m_meta["mine_code"]
            mname = m_meta["mine_name"]
            geo_file = os.path.join(geo_data_dir, f"Geological/mines/{mcode}/{mcode}_Geological_Dataset_FINAL.xlsx")
            if not os.path.exists(geo_file):
                logger.warning(f"Geological file not found: {geo_file}")
                continue

            # 1. Boreholes Master (12 per mine)
            df_bh = pd.read_excel(geo_file, sheet_name="Boreholes")
            for _, r in df_bh.iterrows():
                bhid = str(r["borehole_id"]).strip()
                existing_bh = session.scalar(select(BoreholeMaster).where(BoreholeMaster.borehole_id == bhid))
                if not existing_bh:
                    bh = BoreholeMaster(
                        borehole_id=bhid,
                        mine_id=mid,
                        mine_code=mcode,
                        mine_name=mname,
                        latitude=float(r["latitude"]),
                        longitude=float(r["longitude"]),
                        rl_m=float(r["rl_m"]),
                        total_depth_m=float(r["total_depth_m"]),
                        intersected_seam=str(r.get("intersected_seam", "")) if pd.notna(r.get("intersected_seam")) else None,
                        from_depth_m=float(r["from_depth_m"]) if pd.notna(r.get("from_depth_m")) else None,
                        to_depth_m=float(r["to_depth_m"]) if pd.notna(r.get("to_depth_m")) else None,
                        coal_thickness_m=float(r["coal_thickness_m"]) if pd.notna(r.get("coal_thickness_m")) else None,
                        quality_band=str(r.get("quality_band", "")) if pd.notna(r.get("quality_band")) else None,
                        lithology_summary=str(r.get("lithology_summary", "")) if pd.notna(r.get("lithology_summary")) else None,
                        status=str(r.get("status", "COMPLETED")),
                        data_type="SYNTHETIC_DEMO",
                        provenance_type="SYNTHETIC_DEMO"
                    )
                    session.add(bh)
                    counts["boreholes_master"] += 1
            session.flush()

            # 2. Borehole Intervals (120 per mine)
            df_int = pd.read_excel(geo_file, sheet_name="Borehole_Intervals")
            for _, r in df_int.iterrows():
                bhid = str(r["Borehole_ID"]).strip()
                int_no = int(r["Interval_No"])
                existing_int = session.scalar(
                    select(BoreholeInterval).where(
                        BoreholeInterval.borehole_id == bhid,
                        BoreholeInterval.interval_no == int_no
                    )
                )
                if not existing_int:
                    b_int = BoreholeInterval(
                        borehole_id=bhid,
                        mine_id=mid,
                        mine_code=mcode,
                        interval_no=int_no,
                        from_depth_m=float(r["From_Depth_m"]),
                        to_depth_m=float(r["To_Depth_m"]),
                        thickness_m=float(r["Thickness_m"]),
                        lithology=str(r["Lithology"]).strip(),
                        stratigraphic_unit=str(r.get("Stratigraphic_Unit", "")) if pd.notna(r.get("Stratigraphic_Unit")) else None,
                        coal_bearing=str(r.get("Coal_Bearing", "NO")) if pd.notna(r.get("Coal_Bearing")) else "NO",
                        coal_seam=str(r["Coal_Seam"]).strip() if pd.notna(r.get("Coal_Seam")) else None,
                        weathering_class=str(r.get("Weathering_Class", "")) if pd.notna(r.get("Weathering_Class")) else None,
                        sample_id=str(r.get("Sample_ID", "")) if pd.notna(r.get("Sample_ID")) else None,
                        data_type="SYNTHETIC_DEMO",
                        provenance_type="SYNTHETIC_DEMO"
                    )
                    session.add(b_int)
                    counts["borehole_intervals"] += 1
            session.flush()

            # 3. Coal Seams (5 for Gevra, 4 each for others)
            df_seams = pd.read_excel(geo_file, sheet_name="Coal_Seams")
            for _, r in df_seams.iterrows():
                sid = str(r["seam_id"]).strip()
                existing_seam = session.scalar(
                    select(CoalSeam).where(
                        CoalSeam.seam_id == sid,
                        CoalSeam.mine_code == mcode
                    )
                )
                if not existing_seam:
                    seam = CoalSeam(
                        seam_id=sid,
                        mine_id=mid,
                        mine_code=mcode,
                        mine_name=mname,
                        sequence_order=int(r["sequence_order"]),
                        avg_thickness_m=float(r["avg_thickness_m"]),
                        synthetic_dip_deg=float(r["synthetic_dip_deg"]) if pd.notna(r.get("synthetic_dip_deg")) else None,
                        synthetic_strike_deg=float(r["synthetic_strike_deg"]) if pd.notna(r.get("synthetic_strike_deg")) else None,
                        continuity=str(r.get("continuity", "")) if pd.notna(r.get("continuity")) else None,
                        quality_band=str(r.get("quality_band", "")) if pd.notna(r.get("quality_band")) else None,
                        data_type="SYNTHETIC_DEMO",
                        provenance_type="SYNTHETIC_DEMO"
                    )
                    session.add(seam)
                    counts["coal_seams"] += 1
            session.flush()

            # 4. Geological Events (2 per mine)
            df_events = pd.read_excel(geo_file, sheet_name="Geological_Events")
            for _, r in df_events.iterrows():
                eid = str(r["event_id"]).strip()
                existing_event = session.scalar(
                    select(GeologicalEvent).where(
                        GeologicalEvent.event_id == eid,
                        GeologicalEvent.mine_code == mcode
                    )
                )
                if not existing_event:
                    event = GeologicalEvent(
                        event_id=eid,
                        mine_id=mid,
                        mine_code=mcode,
                        financial_year=str(r.get("financial_year", "FY 2023-24")).strip(),
                        event_type=str(r["event_type"]).strip(),
                        severity=str(r["severity"]).strip().upper(),
                        area=str(r.get("area", "")) if pd.notna(r.get("area")) else None,
                        action=str(r.get("action", "")) if pd.notna(r.get("action")) else None,
                        data_type="SYNTHETIC_DEMO",
                        provenance_type="SYNTHETIC_DEMO"
                    )
                    session.add(event)
                    counts["geological_events"] += 1
            session.flush()

            # 5. Geotechnical Zones (4 per mine)
            df_gz = pd.read_excel(geo_file, sheet_name="Geotechnical_Zones")
            for _, r in df_gz.iterrows():
                zid = str(r["Zone_ID"] if "Zone_ID" in r else r["zone_id"]).strip()
                existing_zone = session.scalar(
                    select(GeotechnicalZone).where(
                        GeotechnicalZone.zone_id == zid,
                        GeotechnicalZone.mine_code == mcode
                    )
                )
                if not existing_zone:
                    gzone = GeotechnicalZone(
                        zone_id=zid,
                        mine_id=mid,
                        mine_code=mcode,
                        zone_type=str(r["Zone_Type"] if "Zone_Type" in r else r["zone_type"]).strip(),
                        risk_class=str(r["Risk_Class"] if "Risk_Class" in r else r["risk_class"]).strip().upper(),
                        basis=str(r.get("Basis", r.get("basis", "Synthetic demonstration interpretation"))),
                        data_type="SYNTHETIC_DEMO",
                        provenance_type="SYNTHETIC_DEMO"
                    )
                    session.add(gzone)
                    counts["geotechnical_zones"] += 1
            session.flush()

            # 6. Survey Points (25 per mine)
            df_sp = pd.read_excel(geo_file, sheet_name="Survey_Points")
            for _, r in df_sp.iterrows():
                spid = str(r["Survey_Point_ID"] if "Survey_Point_ID" in r else r["point_id"]).strip()
                existing_sp = session.scalar(
                    select(SurveyPoint).where(
                        SurveyPoint.survey_point_id == spid,
                        SurveyPoint.mine_code == mcode
                    )
                )
                if not existing_sp:
                    sp = SurveyPoint(
                        survey_point_id=spid,
                        mine_id=mid,
                        mine_code=mcode,
                        point_type=str(r["Point_Type"] if "Point_Type" in r else r["point_type"]).strip(),
                        latitude=float(r["Latitude"] if "Latitude" in r else r["latitude"]),
                        longitude=float(r["Longitude"] if "Longitude" in r else r["longitude"]),
                        rl_m=float(r["RL_m"] if "RL_m" in r else r["rl_m"]),
                        data_type="SYNTHETIC_DEMO",
                        provenance_type="SYNTHETIC_DEMO"
                    )
                    session.add(sp)
                    counts["survey_points"] += 1
            session.flush()

            # 7. Cross Section Points (42 per mine)
            df_cs = pd.read_excel(geo_file, sheet_name="Cross_Section_Points")
            for _, r in df_cs.iterrows():
                sec_id = str(r["Section_ID"] if "Section_ID" in r else r["section_id"]).strip()
                chainage = float(r["Chainage_m"] if "Chainage_m" in r else r["distance_m"])
                ground_rl = float(r["Ground_RL_m"] if "Ground_RL_m" in r else r["elevation_m"])
                existing_csp = session.scalar(
                    select(CrossSectionPoint).where(
                        CrossSectionPoint.mine_code == mcode,
                        CrossSectionPoint.section_id == sec_id,
                        CrossSectionPoint.chainage_m == chainage
                    )
                )
                if not existing_csp:
                    csp = CrossSectionPoint(
                        mine_code=mcode,
                        section_id=sec_id,
                        chainage_m=chainage,
                        ground_rl_m=ground_rl,
                        data_type="SYNTHETIC_DEMO",
                        provenance_type="SYNTHETIC_DEMO"
                    )
                    session.add(csp)
                    counts["cross_section_points"] += 1
            session.flush()

        return counts

    @staticmethod
    def load_all_spatial_gpkg(session: Session, geo_data_dir: str = "/data/geo_data") -> Dict[str, int]:
        """Loads PostGIS spatial layers from GeoVault_Geospatial_All_Mines_FINAL.gpkg for all 5 mines."""
        counts = {
            "spatial_boreholes": 0,
            "spatial_borehole_intervals": 0,
            "spatial_borehole_traces": 0,
            "spatial_coal_seam_belts": 0,
            "spatial_geological_contacts": 0,
            "spatial_geological_units": 0,
            "spatial_geotechnical_zones": 0,
            "spatial_landuse": 0,
            "spatial_survey_points": 0,
            "spatial_geological_events": 0,
        }
        gpkg_path = os.path.join(geo_data_dir, "Geological/GeoVault_Geospatial_All_Mines_FINAL.gpkg")
        if not os.path.exists(gpkg_path):
            raise FileNotFoundError(f"GeoPackage not found at {gpkg_path}")

        for m_meta in CANONICAL_MINES:
            mcode = m_meta["mine_code"]

            layers_config = [
                {
                    "layer": f"{mcode}_boreholes",
                    "model": SpatialBorehole,
                    "count_key": "spatial_boreholes",
                    "map_fn": lambda r: {
                        "borehole_id": str(r["borehole_i"] if "borehole_i" in r else r["borehole_id"]).strip(),
                        "mine_code": mcode,
                        "depth_m": float(r["depth_m"]) if "depth_m" in r and pd.notna(r["depth_m"]) else None,
                        "lithology": str(r.get("lithology", "")) if pd.notna(r.get("lithology")) else None,
                        "intersected_seam": str(r.get("seam", r.get("intersected_seam", ""))) if pd.notna(r.get("seam")) else None,
                        "provenance_type": "SYNTHETIC_DEMO",
                    },
                    "id_col": "borehole_id",
                },
                {
                    "layer": f"{mcode}_borehole_intervals",
                    "model": SpatialBoreholeInterval,
                    "count_key": "spatial_borehole_intervals",
                    "map_fn": lambda r: {
                        "borehole_id": str(r["Borehole_ID"]).strip(),
                        "interval_no": int(r["Interval_No"]),
                        "mine_code": mcode,
                        "from_depth_m": float(r["From_Depth_m"]),
                        "to_depth_m": float(r["To_Depth_m"]),
                        "thickness_m": float(r["Thickness_m"]),
                        "lithology": str(r["Lithology"]).strip(),
                        "coal_seam": str(r["Coal_Seam"]).strip() if pd.notna(r.get("Coal_Seam")) else None,
                        "provenance_type": "SYNTHETIC_DEMO",
                    },
                    "id_col": "borehole_id",
                    "extra_id_col": "interval_no",
                },
                {
                    "layer": f"{mcode}_borehole_traces",
                    "model": SpatialBoreholeTrace,
                    "count_key": "spatial_borehole_traces",
                    "map_fn": lambda r: {
                        "trace_id": str(r["Trace_ID"]).strip(),
                        "borehole_id": str(r["Borehole_ID"]).strip(),
                        "mine_code": mcode,
                        "azimuth_deg": float(r["Azimuth_deg"]) if pd.notna(r.get("Azimuth_deg")) else None,
                        "inclination_deg": float(r["Inclination_deg"]) if pd.notna(r.get("Inclination_deg")) else None,
                        "total_depth_m": float(r["Total_Depth_m"]) if pd.notna(r.get("Total_Depth_m")) else None,
                        "provenance_type": "SYNTHETIC_DEMO",
                    },
                    "id_col": "trace_id",
                },
                {
                    "layer": f"{mcode}_coal_seam_belts",
                    "model": SpatialCoalSeamBelt,
                    "count_key": "spatial_coal_seam_belts",
                    "map_fn": lambda r: {
                        "seam_id": str(r["Seam_ID"]).strip(),
                        "mine_code": mcode,
                        "width_m": float(r["Width_m"]) if pd.notna(r.get("Width_m")) else None,
                        "feature_type": str(r.get("Feature_Type", "")) if pd.notna(r.get("Feature_Type")) else None,
                        "provenance_type": "SYNTHETIC_DEMO",
                    },
                    "id_col": "seam_id",
                },
                {
                    "layer": f"{mcode}_geological_contacts",
                    "model": SpatialGeologicalContact,
                    "count_key": "spatial_geological_contacts",
                    "map_fn": lambda r: {
                        "contact_id": str(r["Contact_ID"]).strip(),
                        "mine_code": mcode,
                        "contact_type": str(r["Contact_Type"]).strip(),
                        "unit_a": str(r.get("Unit_A", "")) if pd.notna(r.get("Unit_A")) else None,
                        "unit_b": str(r.get("Unit_B", "")) if pd.notna(r.get("Unit_B")) else None,
                        "confidence": str(r.get("Confidence", "")) if pd.notna(r.get("Confidence")) else None,
                        "provenance_type": "SYNTHETIC_DEMO",
                    },
                    "id_col": "contact_id",
                },
                {
                    "layer": f"{mcode}_geological_units",
                    "model": SpatialGeologicalUnit,
                    "count_key": "spatial_geological_units",
                    "map_fn": lambda r: {
                        "geology_unit_id": str(r["Geology_Unit_ID"]).strip(),
                        "mine_code": mcode,
                        "unit_name": str(r["Unit_Name"]).strip(),
                        "unit_type": str(r.get("Unit_Type", "")) if pd.notna(r.get("Unit_Type")) else None,
                        "age": str(r.get("Age", "")) if pd.notna(r.get("Age")) else None,
                        "relative_order": int(r["Relative_Order"]) if pd.notna(r.get("Relative_Order")) else None,
                        "provenance_type": "SYNTHETIC_DEMO",
                    },
                    "id_col": "geology_unit_id",
                },
                {
                    "layer": f"{mcode}_geotechnical_zones",
                    "model": SpatialGeotechnicalZone,
                    "count_key": "spatial_geotechnical_zones",
                    "map_fn": lambda r: {
                        "zone_id": str(r["Zone_ID"]).strip(),
                        "mine_code": mcode,
                        "zone_type": str(r["Zone_Type"]).strip(),
                        "risk_class": str(r["Risk_Class"]).strip().upper(),
                        "provenance_type": "SYNTHETIC_DEMO",
                    },
                    "id_col": "zone_id",
                },
                {
                    "layer": f"{mcode}_landuse",
                    "model": SpatialLanduse,
                    "count_key": "spatial_landuse",
                    "map_fn": lambda r: {
                        "landuse_id": str(r["Landuse_ID"]).strip(),
                        "mine_code": mcode,
                        "landuse_class": str(r["Landuse_Class"]).strip(),
                        "status": str(r.get("Status", "")) if pd.notna(r.get("Status")) else None,
                        "provenance_type": "SYNTHETIC_DEMO",
                    },
                    "id_col": "landuse_id",
                },
                {
                    "layer": f"{mcode}_survey_points",
                    "model": SpatialSurveyPoint,
                    "count_key": "spatial_survey_points",
                    "map_fn": lambda r: {
                        "survey_point_id": str(r["Survey_Point_ID"]).strip(),
                        "mine_code": mcode,
                        "point_type": str(r["Point_Type"]).strip(),
                        "rl_m": float(r["RL_m"]) if pd.notna(r.get("RL_m")) else None,
                        "provenance_type": "SYNTHETIC_DEMO",
                    },
                    "id_col": "survey_point_id",
                },
                {
                    "layer": f"{mcode}_geological_events_spatial",
                    "model": SpatialGeologicalEvent,
                    "count_key": "spatial_geological_events",
                    "map_fn": lambda r: {
                        "event_id": str(r["Event_ID"]).strip(),
                        "mine_code": mcode,
                        "event_type": str(r["Event_Type"]).strip(),
                        "severity": str(r["Severity"]).strip(),
                        "area": str(r.get("Area", "")) if pd.notna(r.get("Area")) else None,
                        "action": str(r.get("Action", "")) if pd.notna(r.get("Action")) else None,
                        "provenance_type": "SYNTHETIC_DEMO",
                    },
                    "id_col": "event_id",
                },
            ]

            for cfg in layers_config:
                layer_name = cfg["layer"]
                model_cls = cfg["model"]
                key = cfg["count_key"]

                try:
                    gdf = gpd.read_file(gpkg_path, layer=layer_name)
                except Exception as e:
                    logger.warning(f"Could not read layer {layer_name} from GPKG: {e}")
                    continue

                if gdf.crs is not None and gdf.crs.to_epsg() != 4326:
                    gdf = gdf.to_crs(epsg=4326)

                for _, row in gdf.iterrows():
                    props = cfg["map_fn"](row)
                    geom = row.geometry
                    if geom is None or geom.is_empty:
                        continue

                    shape_geom = from_shape(geom, srid=4326)
                    filter_conds = [model_cls.mine_code == mcode]
                    id_col_name = cfg["id_col"]
                    filter_conds.append(getattr(model_cls, id_col_name) == props[id_col_name])
                    if "extra_id_col" in cfg:
                        extra_col = cfg["extra_id_col"]
                        filter_conds.append(getattr(model_cls, extra_col) == props[extra_col])

                    existing = session.scalar(select(model_cls).where(*filter_conds))
                    if not existing:
                        props["geom"] = shape_geom
                        instance = model_cls(**props)
                        session.add(instance)
                        counts[key] += 1
                session.flush()

        return counts

    @staticmethod
    def load_all_pdfs_and_embeddings(session: Session, geo_data_dir: str = "/data/geo_data") -> Dict[str, int]:
        """Loads all 30 annual report PDFs, extracts text page-by-page, chunks, and batches BGE-M3 embeddings."""
        counts = {"documents": 0, "chunks": 0, "embeddings": 0}
        pdf_pattern = os.path.join(geo_data_dir, "PDF/*.pdf")
        pdf_files = sorted(glob.glob(pdf_pattern))

        import pymupdf
        embed_model = None

        mine_subsidiaries = {m["mine_code"]: m["subsidiary_id"] for m in CANONICAL_MINES}

        for pdf_path in pdf_files:
            fname = os.path.basename(pdf_path)
            # Example filename: GV-KUSMUNDA-OCP-202425-ANNUAL.pdf
            parts = fname.replace(".pdf", "").split("-")
            mcode = parts[1] if len(parts) > 1 else "ENTERPRISE"
            fy_raw = parts[3] if len(parts) > 3 else "202425"
            fy_match = re.match(r"(\d{4})(\d{2})", fy_raw)
            if fy_match:
                formatted_fy = f"{fy_match.group(1)}-{fy_match.group(2)}"
            else:
                formatted_fy = fy_raw

            doc_id = fname.replace(".pdf", "")
            fhash = compute_file_sha256(pdf_path)

            doc = pymupdf.open(pdf_path)
            page_count = len(doc)

            existing_doc = session.scalar(select(Document).where(Document.document_id == doc_id))
            if not existing_doc:
                doc_record = Document(
                    document_id=doc_id,
                    file_name=fname,
                    file_hash=fhash,
                    file_path=pdf_path,
                    category="ANNUAL_REPORT",
                    mine_code=mcode,
                    subsidiary_id=mine_subsidiaries.get(mcode, "SECL"),
                    department="Mining",
                    financial_year=formatted_fy,
                    report_type="ANNUAL",
                    page_count=page_count,
                    classification="INTERNAL",
                    processing_status="COMPLETED",
                    provenance_type="SYNTHETIC_DEMO"
                )
                session.add(doc_record)
                counts["documents"] += 1
            session.flush()

            # Extract pages & collect chunks to embed
            chunks_to_embed = []
            for p_num in range(1, page_count + 1):
                p_text = doc[p_num - 1].get_text("text").strip()
                if not p_text:
                    continue

                page_chunks = chunk_text_page(p_text, max_chars=700, overlap_chars=100)
                for idx, c_text in enumerate(page_chunks):
                    cid = f"{doc_id}-P{p_num:02d}-C{idx+1:02d}"
                    existing_chunk = session.scalar(select(DocumentChunk).where(DocumentChunk.chunk_id == cid))
                    if not existing_chunk:
                        chunks_to_embed.append({
                            "chunk_id": cid,
                            "document_id": doc_id,
                            "page_number": p_num,
                            "chunk_index": idx + 1,
                            "chunk_text": c_text,
                            "mine_code": mcode,
                            "subsidiary_id": mine_subsidiaries.get(mcode, "SECL"),
                            "department": "Mining",
                            "financial_year": formatted_fy,
                            "classification": "INTERNAL",
                            "access_scope": f"{mcode}:Mining:INTERNAL",
                            "provenance_type": "SYNTHETIC_DEMO"
                        })
            doc.close()

            # Compute embeddings in batches if new chunks exist
            if chunks_to_embed:
                if embed_model is None:
                    embed_model = get_embedding_model()

                texts = [c["chunk_text"] for c in chunks_to_embed]
                logger.info(f"Computing BGE-M3 embeddings for {len(texts)} chunks of {fname}...")
                vectors = embed_model.encode(texts, batch_size=32, normalize_embeddings=True, show_progress_bar=False)

                for chunk_meta, vec in zip(chunks_to_embed, vectors):
                    chunk_meta["embedding"] = vec.tolist()
                    chunk_obj = DocumentChunk(**chunk_meta)
                    session.add(chunk_obj)
                    counts["chunks"] += 1
                    counts["embeddings"] += 1
                session.flush()

        return counts

    @staticmethod
    def load_all_ocr_scans(session: Session, geo_data_dir: str = "/data/geo_data") -> Dict[str, int]:
        """Loads and OCR processes the 15 scanned image documents in geo_data/OCR/."""
        counts = {"ocr_documents": 0, "ocr_chunks": 0, "ocr_embeddings": 0}
        ocr_dir = os.path.join(geo_data_dir, "OCR")
        if not os.path.exists(ocr_dir):
            return counts

        image_files = sorted(glob.glob(os.path.join(ocr_dir, "*.png")) + glob.glob(os.path.join(ocr_dir, "*.jpg")))
        if not image_files:
            return counts

        # Configure environment for PaddleOCR CPU execution
        os.environ["FLAGS_use_mkldnn"] = "0"
        os.environ["PADDLE_PDX_ENABLE_ONEDNN"] = "0"
        from paddleocr import PaddleOCR
        ocr_engine = PaddleOCR(use_angle_cls=False, lang="en", enable_mkldnn=False)
        embed_model = None

        for img_path in image_files:
            fname = os.path.basename(img_path)
            fhash = compute_file_sha256(img_path)
            doc_id = f"OCR-{os.path.splitext(fname)[0].upper().replace(' ', '_')}"

            # Detect mine hint if present
            detected_mine = None
            for m in CANONICAL_MINES:
                if m["mine_code"].lower() in fname.lower() or m["mine_name"].lower() in fname.lower() or "kusumudra" in fname.lower():
                    detected_mine = "KUSMUNDA" if "kusumudra" in fname.lower() else m["mine_code"]
                    break

            existing_doc = session.scalar(select(Document).where(Document.file_hash == fhash))
            if not existing_doc:
                doc_record = Document(
                    document_id=doc_id,
                    file_name=fname,
                    file_hash=fhash,
                    file_path=img_path,
                    category="OCR_SCAN",
                    mine_code=detected_mine,
                    subsidiary_id="SECL" if detected_mine in ["GEVRA", "KUSMUNDA", "DIPKA"] else ("NCL" if detected_mine else None),
                    department="Field Operations / Inspection",
                    financial_year="2024-25",
                    report_type="OCR_SCAN",
                    page_count=1,
                    classification="INTERNAL",
                    processing_status="COMPLETED",
                    provenance_type="SYNTHETIC_DEMO"
                )
                session.add(doc_record)
                counts["ocr_documents"] += 1
                session.flush()
            else:
                doc_id = existing_doc.document_id

            # Check if chunk already exists
            cid = f"{doc_id}-P01-C01"
            existing_chunk = session.scalar(select(DocumentChunk).where(DocumentChunk.chunk_id == cid))
            if not existing_chunk:
                try:
                    logger.info(f"Running OCR on {fname}...")
                    ocr_res = ocr_engine.ocr(img_path)
                    lines = [line[1][0] for res in ocr_res for line in res] if ocr_res else []
                    extracted_text = " ".join(lines).strip()
                    if not extracted_text:
                        extracted_text = f"Scanned image document: {fname}. Synthetic demonstration record."
                except Exception as e:
                    logger.warning(f"OCR extraction failed for {fname}: {e}")
                    extracted_text = f"Scanned image record: {fname}."

                if embed_model is None:
                    embed_model = get_embedding_model()

                vec = embed_model.encode([extracted_text], normalize_embeddings=True)[0].tolist()

                chunk_obj = DocumentChunk(
                    chunk_id=cid,
                    document_id=doc_id,
                    page_number=1,
                    chunk_index=1,
                    chunk_text=extracted_text,
                    mine_code=detected_mine,
                    subsidiary_id="SECL" if detected_mine in ["GEVRA", "KUSMUNDA", "DIPKA"] else ("NCL" if detected_mine else None),
                    department="Field Operations / Inspection",
                    financial_year="2024-25",
                    classification="INTERNAL",
                    access_scope=f"{detected_mine or 'ALL'}:Field:INTERNAL",
                    embedding=vec,
                    provenance_type="SYNTHETIC_DEMO"
                )
                session.add(chunk_obj)
                counts["ocr_chunks"] += 1
                counts["ocr_embeddings"] += 1
                session.flush()

        return counts

    @staticmethod
    def register_all_evidence(session: Session) -> int:
        """Registers verified evidence records across all five canonical mines."""
        added = 0
        for m in CANONICAL_MINES:
            mcode = m["mine_code"]
            ev_id = f"EV-FACTS-{mcode}-202425"
            existing = session.scalar(select(Evidence).where(Evidence.evidence_id == ev_id))
            if not existing:
                ev = Evidence(
                    evidence_id=ev_id,
                    source_type="STRUCTURED_RECORD",
                    table_name="production_annual",
                    record_id=f"PROD-{mcode}-202425",
                    source_text=f"{mcode} validated production annual operational facts for FY2024-25",
                    mine_code=mcode,
                    department="Mining",
                    classification="INTERNAL",
                    status="VERIFIED"
                )
                session.add(ev)
                added += 1
        session.flush()
        return added

    @classmethod
    def run_full_five_mines_pipeline(cls, geo_data_dir: str = "/data/geo_data") -> Dict[str, Any]:
        """Executes full ingestion across all five canonical mines idempotently."""
        session = SessionLocal()
        start_time = time.time()
        summary = {
            "status": "SUCCESS",
            "mines": [m["mine_code"] for m in CANONICAL_MINES],
            "provenance": "SYNTHETIC_DEMO",
            "start_time": time.ctime(start_time),
        }

        try:
            logger.info("=== STEP 1: Operational Ingestion (5 Mines) ===")
            summary["operational_counts"] = cls.load_all_operational(session, geo_data_dir)

            logger.info("=== STEP 2: Geological Ingestion (5 Mines) ===")
            summary["geological_counts"] = cls.load_all_geological(session, geo_data_dir)

            logger.info("=== STEP 3: PostGIS Spatial Ingestion (10 layers x 5 Mines) ===")
            summary["spatial_counts"] = cls.load_all_spatial_gpkg(session, geo_data_dir)

            logger.info("=== STEP 4: PDF Unstructured Extraction & Embeddings (30 PDFs) ===")
            summary["unstructured_counts"] = cls.load_all_pdfs_and_embeddings(session, geo_data_dir)

            logger.info("=== STEP 5: OCR Image Processing (15 Scans) ===")
            summary["ocr_counts"] = cls.load_all_ocr_scans(session, geo_data_dir)

            logger.info("=== STEP 6: Registering Multi-Mine Verified Evidence ===")
            summary["evidence_registered"] = cls.register_all_evidence(session)

            session.commit()

            logger.info("=== STEP 7: Reconciling Full Five-Mine Database Counts ===")
            recon: Dict[str, Any] = {"grand_totals": {}, "by_mine": {}}
            tables = [
                ("production_annual", ProductionAnnual),
                ("equipment_fleet", EquipmentFleet),
                ("safety_records", SafetyRecord),
                ("environmental_records", EnvironmentalRecord),
                ("qa_benchmarks", QABenchmark),
                ("boreholes_master", BoreholeMaster),
                ("borehole_intervals", BoreholeInterval),
                ("coal_seams", CoalSeam),
                ("geological_events", GeologicalEvent),
                ("geotechnical_zones", GeotechnicalZone),
                ("survey_points", SurveyPoint),
                ("cross_section_points", CrossSectionPoint),
                ("spatial_boreholes", SpatialBorehole),
                ("spatial_borehole_intervals", SpatialBoreholeInterval),
                ("spatial_borehole_traces", SpatialBoreholeTrace),
                ("spatial_coal_seam_belts", SpatialCoalSeamBelt),
                ("spatial_geological_contacts", SpatialGeologicalContact),
                ("spatial_geological_units", SpatialGeologicalUnit),
                ("spatial_geotechnical_zones", SpatialGeotechnicalZone),
                ("spatial_landuse", SpatialLanduse),
                ("spatial_survey_points", SpatialSurveyPoint),
                ("spatial_geological_events", SpatialGeologicalEvent),
                ("documents", Document),
                ("document_chunks", DocumentChunk),
            ]

            recon["grand_totals"]["mines"] = session.scalar(select(func.count(Mine.mine_code)).where(Mine.mine_code.in_([m["mine_code"] for m in CANONICAL_MINES])))
            for tname, model_cls in tables:
                total = session.scalar(select(func.count()).select_from(model_cls).where(model_cls.mine_code.in_([m["mine_code"] for m in CANONICAL_MINES])))
                recon["grand_totals"][tname] = total

            recon["grand_totals"]["embeddings"] = session.scalar(
                select(func.count(DocumentChunk.chunk_id)).where(
                    DocumentChunk.mine_code.in_([m["mine_code"] for m in CANONICAL_MINES]),
                    DocumentChunk.embedding.isnot(None)
                )
            )

            # Breakdown by mine
            for m in CANONICAL_MINES:
                mcode = m["mine_code"]
                m_counts = {}
                for tname, model_cls in tables:
                    m_counts[tname] = session.scalar(select(func.count()).select_from(model_cls).where(model_cls.mine_code == mcode))
                recon["by_mine"][mcode] = m_counts

            summary["database_reconciliation"] = recon
            summary["elapsed_sec"] = round(time.time() - start_time, 2)
            logger.info(f"Full 5-Mine Ingestion completed successfully in {summary['elapsed_sec']}s")

        except Exception as e:
            session.rollback()
            logger.exception("Error during full 5-mine ingestion")
            summary["status"] = "FAILED"
            summary["error"] = str(e)
        finally:
            session.close()

        return summary


if __name__ == "__main__":
    import json
    result = GeoDataIngestionService.run_full_five_mines_pipeline()
    print(json.dumps(result, indent=2))
