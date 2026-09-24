"""
GeoVault AI - Query Intelligence & Analytics Test Suite
Verifies deterministic queries, calculations, evidence generation,
validation engine, data gap detection, and conflict surfacing.
"""

import sys
import unittest
from typing import List

from app.core.database import SessionLocal
from app.models.operational import ProductionAnnual
from app.schemas.query import QueryResultPackage
from app.security.context import UserContext, AuthorizedScope
from app.security.service import AuthorizationService
from app.services.query_service import DeterministicQueryService
from app.analytics.engine import AnalyticsEngine
from app.services.evidence_engine import EvidenceEngine
from app.services.validation_engine import ValidationEngine


class TestQueryIntelligenceSuite(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.db = SessionLocal()
        # Demo Users
        cls.u1 = AuthorizationService.resolve_user_context(cls.db, "USR001")  # Mining Eng, DEOM-01, INTERNAL
        cls.u2 = AuthorizationService.resolve_user_context(cls.db, "USR002")  # Geology Eng, DEOM-01, RESTRICTED
        cls.u3 = AuthorizationService.resolve_user_context(cls.db, "USR003")  # Transport Eng, KNUG-02, INTERNAL
        cls.u4 = AuthorizationService.resolve_user_context(cls.db, "USR004")  # Mine Manager, DEOM-01 + KNUG-02, RESTRICTED
        cls.u5 = AuthorizationService.resolve_user_context(cls.db, "USR005")  # Administrator, ALL, CONFIDENTIAL

        # Scopes
        cls.scope1 = AuthorizationService.get_authorized_scope(cls.u1)
        cls.scope2 = AuthorizationService.get_authorized_scope(cls.u2)
        cls.scope3 = AuthorizationService.get_authorized_scope(cls.u3)
        cls.scope4 = AuthorizationService.get_authorized_scope(cls.u4)
        cls.scope5 = AuthorizationService.get_authorized_scope(cls.u5)

    @classmethod
    def tearDownClass(cls):
        cls.db.close()

    # --------------------------------------------------------------------------
    # 1. Deterministic Production Queries
    # --------------------------------------------------------------------------
    def test_01_deterministic_production_queries(self):
        """Verifies annual, monthly, and equipment metric queries under authorized scope."""
        # Annual query for DEOM-01
        annual_recs = DeterministicQueryService.get_annual_production(
            self.db, self.scope1, mine_code="DEOM-01", start_year=2021, end_year=2025
        )
        self.assertEqual(len(annual_recs), 5, "DEOM-01 should have exactly 5 annual production records (2021-2025).")
        for r in annual_recs:
            self.assertEqual(r.mine_code, "DEOM-01")
            self.assertGreater(float(r.actual_production_mt), 0.0)

        # Monthly query for DEOM-01 (FY2024)
        monthly_recs = DeterministicQueryService.get_monthly_production(
            self.db, self.scope1, mine_code="DEOM-01", year=2024
        )
        self.assertEqual(len(monthly_recs), 12, "DEOM-01 FY2024 should have 12 monthly records.")

        # Equipment availability and downtime derivation
        eq_metrics = DeterministicQueryService.get_equipment_metrics(
            self.db, self.scope1, mine_code="DEOM-01", year=2024
        )
        self.assertEqual(len(eq_metrics), 1)
        m = eq_metrics[0]
        self.assertIsNotNone(m["availability_pct"])
        self.assertIsNotNone(m["downtime_pct"])
        self.assertAlmostEqual(m["availability_pct"] + m["downtime_pct"], 100.0, places=2)

    # --------------------------------------------------------------------------
    # 2. Scoped Multi-Mine Comparison
    # --------------------------------------------------------------------------
    def test_02_scoped_multi_mine_comparison(self):
        """Manager (USR004) can compare DEOM-01 and KNUG-02; single-mine user cannot leak other mines."""
        records = DeterministicQueryService.get_annual_production(
            self.db, self.scope4, start_year=2021, end_year=2025
        )
        facts = [{c.name: getattr(r, c.name) for c in r.__table__.columns} for r in records]

        # Comparison via AnalyticsEngine
        comparisons = AnalyticsEngine.compare_mines(facts)
        comp_mines = {c.mine_code for c in comparisons}
        self.assertIn("DEOM-01", comp_mines)
        self.assertIn("KNUG-02", comp_mines)
        self.assertNotIn("SSOP-03", comp_mines, "Manager scope must not leak unassigned SSOP-03 data.")

        # Check total production per mine
        deom_item = next(c for c in comparisons if c.mine_code == "DEOM-01")
        knug_item = next(c for c in comparisons if c.mine_code == "KNUG-02")
        self.assertAlmostEqual(deom_item.total_production_mt, 23.69, places=2)
        self.assertAlmostEqual(knug_item.total_production_mt, 7.88, places=2)

    # --------------------------------------------------------------------------
    # 3. Trend Analysis & YoY Calculation
    # --------------------------------------------------------------------------
    def test_03_trend_analysis_and_yoy(self):
        """Computes multi-year trajectory, net growth, and year-over-year deltas."""
        records = DeterministicQueryService.get_annual_production(
            self.db, self.scope1, mine_code="DEOM-01", start_year=2021, end_year=2025
        )
        facts = [{c.name: getattr(r, c.name) for c in r.__table__.columns} for r in records]

        trend = AnalyticsEngine.compute_trend_summary(facts, time_key="year", metric_key="actual_production_mt")
        self.assertIsNotNone(trend)
        self.assertEqual(trend.direction, "UPWARD", "DEOM-01 production grew steadily from 4.18 to 5.31 MT.")
        self.assertAlmostEqual(trend.start_value, 4.18, places=2)
        self.assertAlmostEqual(trend.end_value, 5.31, places=2)
        self.assertAlmostEqual(trend.net_change, 1.13, places=2)
        self.assertAlmostEqual(trend.net_change_pct, 27.03, places=1)
        self.assertEqual(len(trend.series), 5)

    # --------------------------------------------------------------------------
    # 4. Target vs Actual Verification & Math Check
    # --------------------------------------------------------------------------
    def test_04_target_vs_actual_and_math_validation(self):
        """Cross-checks database variance and achievement % against live calculations."""
        records = DeterministicQueryService.get_annual_production(
            self.db, self.scope1, mine_code="DEOM-01", year=2024
        )
        facts = [{c.name: getattr(r, c.name) for c in r.__table__.columns} for r in records]

        # AnalyticsEngine calculation
        achieve = AnalyticsEngine.compute_target_achievement(target=facts[0]["target_mt"], actual=facts[0]["actual_production_mt"])
        self.assertEqual(achieve["status"], "ACHIEVED")
        self.assertAlmostEqual(achieve["variance"], 0.02, places=2)
        self.assertAlmostEqual(achieve["achievement_pct"], 100.40, places=1)

        # ValidationEngine cross-validation
        math_checks = ValidationEngine.validate_math(facts)
        self.assertGreater(len(math_checks), 0)
        for check in math_checks:
            self.assertTrue(check.is_valid, f"Math check failed for {check.field_name}: DB={check.database_value} vs Calc={check.calculated_value}")

    # --------------------------------------------------------------------------
    # 5. Evidence Engine Traceability
    # --------------------------------------------------------------------------
    def test_05_evidence_engine_attachment(self):
        """Verifies that every factual record produces a traceable, verifiable EvidenceItem."""
        records = DeterministicQueryService.get_annual_production(
            self.db, self.scope1, mine_code="DEOM-01", year=2024
        )
        evidence_items = EvidenceEngine.from_structured_records(records, "production_annual")

        self.assertEqual(len(evidence_items), 1)
        ev = evidence_items[0]
        self.assertTrue(ev.evidence_id.startswith("EV-PRODUCTION_A-DEOM-01-2024"))
        self.assertEqual(ev.source_type, "STRUCTURED_RECORD")
        self.assertEqual(ev.source_name, "production_annual")
        self.assertEqual(ev.mine_code, "DEOM-01")
        self.assertIn("Annual Production Register", ev.citation)
        self.assertIn("DEOM-01", ev.citation)
        self.assertIn("Actual: 5.02", ev.snippet)

    # --------------------------------------------------------------------------
    # 6. Missing Data & Data Gap Detection
    # --------------------------------------------------------------------------
    def test_06_missing_data_gap_detection(self):
        """Querying an unrecorded year or out-of-range period identifies a DATA_GAP."""
        # Querying year 2035 (non-existent)
        records = DeterministicQueryService.get_annual_production(
            self.db, self.scope1, mine_code="DEOM-01", year=2035
        )
        self.assertEqual(len(records), 0)

        val_result = ValidationEngine.validate_query(
            db=self.db,
            scope=self.scope1,
            records=[],
            domain="production_annual",
            mine_code="DEOM-01",
            year=2035,
        )
        self.assertEqual(val_result.evidence_status, "INSUFFICIENT_AUTHORIZED_DATA")
        self.assertGreater(len(val_result.data_gaps), 0)
        self.assertEqual(val_result.data_gaps[0].gap_type, "NO_RECORDS_FOUND")

    # --------------------------------------------------------------------------
    # 7. Conflict Surfacing (Never Silently Reconcile)
    # --------------------------------------------------------------------------
    def test_07_conflict_detection_and_surfacing(self):
        """Querying SSOP-03 FY2025 logistics surfaces CONF-SSOP03-2025-LOGISTICS with CONFLICT status."""
        # USR005 has access to SSOP-03
        records = DeterministicQueryService.get_dispatch_summary(
            self.db, self.scope5, mine_code="SSOP-03", year=2025
        )
        facts = [{c.name: getattr(r, c.name) for c in r.__table__.columns} for r in records]

        val_result = ValidationEngine.validate_query(
            db=self.db,
            scope=self.scope5,
            records=facts,
            domain="dispatch_summary",
            mine_code="SSOP-03",
            year=2025,
        )

        # Conflict MUST be detected and surfaced
        self.assertEqual(val_result.evidence_status, "CONFLICT", "Disagreements between sources must flag CONFLICT.")
        self.assertGreater(len(val_result.conflicts_detected), 0)
        conflict_ids = [c.conflict_id for c in val_result.conflicts_detected]
        self.assertIn("CONF-SSOP03-2025-LOGISTICS", conflict_ids)

        # Verify conflict payload
        c_item = next(c for c in val_result.conflicts_detected if c.conflict_id == "CONF-SSOP03-2025-LOGISTICS")
        self.assertEqual(c_item.mine_code, "SSOP-03")
        self.assertEqual(c_item.status, "CONFLICT")
        self.assertIn("0.08 MT", c_item.source_a_value)
        self.assertIn("0.31 MT", c_item.source_b_value)

    # --------------------------------------------------------------------------
    # 8. Operational Domains Coverage
    # --------------------------------------------------------------------------
    def test_08_operational_domains_coverage(self):
        """Verifies access to coal quality, geology, mining issues, and inspections."""
        # Coal quality
        cq = DeterministicQueryService.get_coal_quality(self.db, self.scope1, mine_code="DEOM-01")
        self.assertGreater(len(cq), 0)

        # Geological units (USR002 - Geology Engineer)
        geo = DeterministicQueryService.get_geological_units(self.db, self.scope2, mine_code="DEOM-01")
        self.assertGreater(len(geo), 0)

        # Mining issues
        issues = DeterministicQueryService.get_mining_issues(self.db, self.scope1, mine_code="DEOM-01")
        self.assertGreater(len(issues), 0)

        # Inspections
        inspections = DeterministicQueryService.get_inspections(self.db, self.scope1, mine_code="DEOM-01")
        self.assertGreater(len(inspections), 0)


if __name__ == "__main__":
    unittest.main()
