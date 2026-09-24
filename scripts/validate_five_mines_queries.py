import sys
import json
import logging
from decimal import Decimal
from sqlalchemy import text
from app.core.database import SessionLocal
from app.models import (
    Mine,
    User,
    UserScope,
    ProductionAnnual,
    CoalSeam,
    BoreholeMaster,
    BoreholeInterval,
    GeotechnicalZone,
    Document,
    DocumentChunk,
)

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

EXPECTED_MINES = ["GEVRA", "KUSMUNDA", "DIPKA", "NIGAHI", "DUDHICHUA"]

def run_all_tests():
    db = SessionLocal()
    results = {}
    passed_tests = 0
    total_tests = 0
    
    try:
        # -------------------------------------------------------------
        # Test 1: FY2024-25 Production for all 5 mines
        # -------------------------------------------------------------
        total_tests += 1
        logger.info("--- Test 1: FY2024-25 Production Across All 5 Mines ---")
        q1_rows = db.query(ProductionAnnual).filter(
            ProductionAnnual.financial_year == "2024-25"
        ).order_by(ProductionAnnual.actual_production_mt.desc()).all()
        
        assert len(q1_rows) == 5, f"Test 1 failed: Expected 5 production rows for 2024-25, got {len(q1_rows)}"
        m_codes = [r.mine_code for r in q1_rows]
        assert set(m_codes) == set(EXPECTED_MINES), f"Test 1 failed: Missing mines {set(EXPECTED_MINES) - set(m_codes)}"
        
        results["test_1_production_fy24_25"] = {
            "status": "PASS",
            "mines": [
                {
                    "mine_code": r.mine_code,
                    "target_mt": float(r.target_mt),
                    "actual_mt": float(r.actual_production_mt),
                    "achievement_pct": float(r.achievement_pct),
                    "variance_mt": float(r.variance_mt) if r.variance_mt is not None else round(float(r.actual_production_mt) - float(r.target_mt), 2)
                }
                for r in q1_rows
            ]
        }
        passed_tests += 1
        logger.info("Test 1 Passed: %d mines verified for FY2024-25", len(q1_rows))

        # -------------------------------------------------------------
        # Test 2: Cross-Mine Comparison Analytics
        # -------------------------------------------------------------
        total_tests += 1
        logger.info("--- Test 2: Cross-Mine Comparison Analytics ---")
        analytics = db.execute(text("""
            SELECT 
                COUNT(mine_code) as total_mines,
                SUM(actual_production_mt) as total_actual_mt,
                SUM(target_mt) as total_target_mt,
                AVG(achievement_pct) as avg_achievement_pct,
                MAX(actual_production_mt) as max_actual_mt,
                MIN(actual_production_mt) as min_actual_mt
            FROM production_annual
            WHERE financial_year = '2024-25'
        """)).mappings().first()
        
        total_actual = float(analytics["total_actual_mt"])
        total_target = float(analytics["total_target_mt"])
        avg_achieve = float(analytics["avg_achievement_pct"])
        assert analytics["total_mines"] == 5, "Test 2 failed: total mines != 5"
        assert total_actual > 0, "Test 2 failed: total production is 0"
        
        results["test_2_cross_mine_analytics"] = {
            "status": "PASS",
            "total_mines": analytics["total_mines"],
            "total_target_mt": round(total_target, 2),
            "total_actual_mt": round(total_actual, 2),
            "overall_achievement_pct": round((total_actual / total_target) * 100, 2),
            "average_achievement_pct": round(avg_achieve, 2),
            "highest_producer_mt": float(analytics["max_actual_mt"]),
            "lowest_producer_mt": float(analytics["min_actual_mt"])
        }
        passed_tests += 1
        logger.info("Test 2 Passed: Total FY24-25 Production = %.2f MT (Target: %.2f MT)", total_actual, total_target)

        # -------------------------------------------------------------
        # Test 3: Geological Summary Across All 5 Mines
        # -------------------------------------------------------------
        total_tests += 1
        logger.info("--- Test 3: Geological Summary Across All 5 Mines ---")
        seam_summary = db.execute(text("""
            SELECT mine_code, COUNT(seam_id) as seam_count, AVG(avg_thickness_m) as avg_th, MIN(avg_thickness_m) as min_th, MAX(avg_thickness_m) as max_th
            FROM coal_seams
            GROUP BY mine_code
            ORDER BY mine_code
        """)).mappings().all()
        
        assert len(seam_summary) == 5, f"Test 3 failed: Coal seams missing for some mines ({len(seam_summary)}/5)"
        
        bh_counts = db.execute(text("SELECT mine_code, COUNT(*) as cnt FROM boreholes_master GROUP BY mine_code")).mappings().all()
        bh_dict = {r["mine_code"]: r["cnt"] for r in bh_counts}
        for m in EXPECTED_MINES:
            assert bh_dict.get(m, 0) == 12, f"Test 3 failed: Expected 12 boreholes for {m}, got {bh_dict.get(m, 0)}"
            
        total_intervals = db.execute(text("SELECT COUNT(*) as cnt FROM borehole_intervals")).scalar()
        assert total_intervals == 600, f"Test 3 failed: Expected 600 borehole intervals, got {total_intervals}"
        
        results["test_3_geological_summary"] = {
            "status": "PASS",
            "seam_distribution": [
                {
                    "mine_code": r["mine_code"],
                    "seam_count": r["seam_count"],
                    "avg_thickness_m": round(float(r["avg_th"]), 2) if r["avg_th"] else None,
                    "thickness_range": f"{r['min_th']}-{r['max_th']}m"
                }
                for r in seam_summary
            ],
            "total_boreholes": sum(bh_dict.values()),
            "total_borehole_intervals": total_intervals
        }
        passed_tests += 1
        logger.info("Test 3 Passed: 60 Boreholes, 600 Intervals, Seams confirmed across all 5 mines")

        # -------------------------------------------------------------
        # Test 4: PostGIS Spatial Geometry and Queries
        # -------------------------------------------------------------
        total_tests += 1
        logger.info("--- Test 4: PostGIS Spatial Layers & Queries ---")
        spatial_tables = [
            "spatial_boreholes",
            "spatial_borehole_intervals",
            "spatial_borehole_traces",
            "spatial_coal_seam_belts",
            "spatial_geological_contacts",
            "spatial_geological_units",
            "spatial_geotechnical_zones",
            "spatial_landuse",
            "spatial_survey_points",
            "spatial_geological_events"
        ]
        
        counts = {}
        for tbl in spatial_tables:
            c = db.execute(text(f"SELECT COUNT(*) FROM {tbl}")).scalar()
            srid = db.execute(text(f"SELECT Find_SRID('public', '{tbl}', 'geom')")).scalar()
            counts[tbl] = {"count": c, "srid": srid}
            assert c > 0, f"Test 4 failed: Table {tbl} is empty"
            assert srid == 4326, f"Test 4 failed: Table {tbl} SRID is {srid}, expected 4326"

        # Check geometry validity
        invalid_count = db.execute(text("""
            SELECT 
                (SELECT COUNT(*) FROM spatial_coal_seam_belts WHERE ST_IsValid(geom) = false) +
                (SELECT COUNT(*) FROM spatial_geotechnical_zones WHERE ST_IsValid(geom) = false) +
                (SELECT COUNT(*) FROM spatial_geological_units WHERE ST_IsValid(geom) = false) as invalid_features
        """)).scalar()
        assert invalid_count == 0, f"Test 4 failed: Found {invalid_count} invalid geometries"

        # Check spatial distance query across mines
        dist_res = db.execute(text("""
            SELECT 
                b.mine_code,
                b.borehole_id,
                z.zone_id,
                ROUND(ST_Distance(b.geom::geography, z.geom::geography)::numeric, 2) as distance_meters
            FROM spatial_boreholes b
            JOIN spatial_geotechnical_zones z ON b.mine_code = z.mine_code
            WHERE b.mine_code = 'KUSMUNDA'
            ORDER BY distance_meters ASC
            LIMIT 1
        """)).mappings().first()
        
        results["test_4_postgis_spatial"] = {
            "status": "PASS",
            "tables": counts,
            "sample_spatial_query": {
                "mine": dist_res["mine_code"],
                "borehole": dist_res["borehole_id"],
                "geotechnical_zone": dist_res["zone_id"],
                "distance_meters": float(dist_res["distance_meters"])
            }
        }
        passed_tests += 1
        logger.info("Test 4 Passed: All 10 spatial tables valid SRID 4326, distance query operational")

        # -------------------------------------------------------------
        # Test 5: Hybrid Query (Production Metrics + Geological RAG)
        # -------------------------------------------------------------
        total_tests += 1
        logger.info("--- Test 5: Hybrid Query (Production + PDF RAG Evidence) ---")
        hybrid_results = {}
        for m in ["DIPKA", "NIGAHI"]:
            prod = db.query(ProductionAnnual).filter(
                ProductionAnnual.mine_code == m,
                ProductionAnnual.financial_year == "2024-25"
            ).first()
            
            rag_chunks = db.execute(text("""
                SELECT dc.chunk_id, dc.page_number, dc.chunk_text, d.file_name
                FROM document_chunks dc
                JOIN documents d ON dc.document_id = d.document_id
                WHERE dc.mine_code = :mcode
                  AND (dc.chunk_text ILIKE '%production%' OR dc.chunk_text ILIKE '%target%' OR dc.chunk_text ILIKE '%geolog%')
                LIMIT 2
            """), {"mcode": m}).mappings().all()
            
            hybrid_results[m] = {
                "actual_production_mt": float(prod.actual_production_mt),
                "target_mt": float(prod.target_mt),
                "achievement_pct": float(prod.achievement_pct),
                "evidence_chunks": [
                    {"chunk_id": c["chunk_id"], "page": c["page_number"], "file": c["file_name"], "snippet": c["chunk_text"][:120] + "..."}
                    for c in rag_chunks
                ]
            }
            assert len(rag_chunks) > 0, f"Test 5 failed: No RAG chunks found for {m}"

        results["test_5_hybrid_query"] = {
            "status": "PASS",
            "mines_tested": hybrid_results
        }
        passed_tests += 1
        logger.info("Test 5 Passed: Hybrid query successfully combined SQL metrics with RAG text chunks")

        # -------------------------------------------------------------
        # Test 6: Strict RBAC / ABAC Authorization Scopes
        # -------------------------------------------------------------
        total_tests += 1
        logger.info("--- Test 6: Strict RBAC/ABAC Security Access Verification ---")
        from app.security.service import AuthorizationService

        # User USR001: Mining Engineer (GEVRA authorized, others forbidden)
        u1_ctx = AuthorizationService.resolve_user_context(db, "USR001")
        u1_scope = AuthorizationService.get_authorized_scope(u1_ctx)
        assert "GEVRA" in u1_scope.allowed_mines, f"USR001 missing GEVRA scope: {u1_scope.allowed_mines}"
        assert not any(m in u1_scope.allowed_mines for m in ["KUSMUNDA", "DIPKA", "NIGAHI", "DUDHICHUA"]), f"USR001 has unauthorized mines: {u1_scope.allowed_mines}"
        q_u1 = AuthorizationService.scope_structured_query(db.query(ProductionAnnual), ProductionAnnual, u1_scope).all()
        u1_allowed_mines = set(r.mine_code for r in q_u1)
        assert "GEVRA" in u1_allowed_mines, "USR001 missing GEVRA production"
        assert not any(m in u1_allowed_mines for m in ["KUSMUNDA", "DIPKA", "NIGAHI", "DUDHICHUA"]), f"USR001 accessed forbidden mines: {u1_allowed_mines}"

        # User USR003: Transportation Engineer (KNUG-02 / Mine B, GEVRA/DIPKA/NIGAHI/DUDHICHUA forbidden)
        u3_ctx = AuthorizationService.resolve_user_context(db, "USR003")
        u3_scope = AuthorizationService.get_authorized_scope(u3_ctx)
        assert not any(m in u3_scope.allowed_mines for m in ["GEVRA", "DIPKA", "NIGAHI", "DUDHICHUA"]), f"USR003 has unauthorized mines: {u3_scope.allowed_mines}"
        q_u3 = AuthorizationService.scope_structured_query(db.query(ProductionAnnual), ProductionAnnual, u3_scope).all()
        u3_allowed_mines = set(r.mine_code for r in q_u3)
        assert "GEVRA" not in u3_allowed_mines and "NIGAHI" not in u3_allowed_mines, f"USR003 accessed forbidden mines: {u3_allowed_mines}"

        # User USR005: Administrator (Enterprise / Unrestricted)
        u5_ctx = AuthorizationService.resolve_user_context(db, "USR005")
        u5_scope = AuthorizationService.get_authorized_scope(u5_ctx)
        assert u5_scope.allowed_mines is None, "USR005 missing unrestricted scope"
        q_u5 = AuthorizationService.scope_structured_query(db.query(ProductionAnnual), ProductionAnnual, u5_scope).all()
        u5_allowed_mines = set(r.mine_code for r in q_u5)
        assert set(EXPECTED_MINES).issubset(u5_allowed_mines), f"USR005 expected all 5 mines, got: {u5_allowed_mines}"

        results["test_6_rbac_security"] = {
            "status": "PASS",
            "USR001_authorized_mines": list(u1_allowed_mines),
            "USR003_allowed_mines": list(u3_scope.allowed_mines),
            "USR003_forbidden_checked": ["GEVRA", "DIPKA", "NIGAHI", "DUDHICHUA"],
            "USR005_enterprise_unrestricted": u5_scope.allowed_mines is None,
            "USR005_all_mines_accessible": list(u5_allowed_mines)
        }
        passed_tests += 1
        logger.info("Test 6 Passed: Multi-tenant RBAC / ABAC scoping rigorously verified")

        results["summary"] = {
            "total_tests": total_tests,
            "passed_tests": passed_tests,
            "status": "ALL_TESTS_PASSED"
        }
        print(json.dumps(results, indent=2))

    except Exception as e:
        logger.error("Validation failed: %s", str(e), exc_info=True)
        sys.exit(1)
    finally:
        db.close()

if __name__ == "__main__":
    run_all_tests()
