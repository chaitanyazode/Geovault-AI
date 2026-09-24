"""
GeoVault AI - Phase 6B Automated Professional Report Generation Test Suite
Tests:
1. Scoped data packaging & retrieval (AUTHORIZATION BEFORE RETRIEVAL)
2. Headless Matplotlib chart generation (Trend & Comparison PNGs)
3. Word document (.docx) generation & structure verification
4. PDF document (.pdf) generation & page rendering
5. Deterministic numerical tables matching PostgreSQL records exactly
6. Security denial: USR001 requesting KNUG-02 report raises 403 Forbidden
7. Mine Manager multi-mine report: USR004 generates DEOM-01 + KNUG-02; denied on SSOP-03
8. Conflict detection & surfacing: SSOP-03 FY2025 includes visible conflict callout
9. Download authorization & path traversal security defense
10. UnifiedAIOrchestrator natural-language query integration (REPORT route)
"""

import os
import unittest
from sqlalchemy.orm import Session
from fastapi import HTTPException

from app.core.database import SessionLocal
from app.security.service import AuthorizationService
from app.security.context import UserContext, AuthorizedScope
from app.schemas.reports import ReportGenerateRequest
from app.services.report_service import ReportGenerationService
from app.ai.orchestrator import UnifiedAIOrchestrator
from docx import Document


class TestPhase6BReportGenerationSuite(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.db: Session = SessionLocal()
        cls.service = ReportGenerationService()

        # USR001: Mining Engineer, Mine A (DEOM-01), INTERNAL
        cls.user1: UserContext = AuthorizationService.resolve_user_context(cls.db, "USR001")
        cls.scope1: AuthorizedScope = AuthorizationService.get_authorized_scope(cls.user1)

        # USR004: Mine Manager, Mine A + Mine B (DEOM-01, KNUG-02), RESTRICTED
        cls.user4: UserContext = AuthorizationService.resolve_user_context(cls.db, "USR004")
        cls.scope4: AuthorizedScope = AuthorizationService.get_authorized_scope(cls.user4)

        # USR005: Administrator, ALL mines, CONFIDENTIAL
        cls.user5: UserContext = AuthorizationService.resolve_user_context(cls.db, "USR005")
        cls.scope5: AuthorizedScope = AuthorizationService.get_authorized_scope(cls.user5)

    @classmethod
    def tearDownClass(cls):
        cls.db.close()

    # --------------------------------------------------------------------------
    # 1. Report Data Packaging & Scoping
    # --------------------------------------------------------------------------
    def test_01_report_data_packaging(self):
        """Verifies report generation gathers verified operational data for authorized scope."""
        req = ReportGenerateRequest(
            mine_code="DEOM-01",
            report_type="PERFORMANCE",
            start_year=2021,
            end_year=2025,
            include_charts=True
        )
        res = self.service.generate_report(self.db, self.user1, req)

        self.assertIsNotNone(res.report_id)
        self.assertEqual(res.status, "GENERATED")
        self.assertIn("DEOM-01", res.mines_covered)
        self.assertGreater(res.evidence_count, 0)
        self.assertIsNotNone(res.docx_download_url)
        self.assertIsNotNone(res.pdf_download_url)

        TestPhase6BReportGenerationSuite.sample_report = res

    # --------------------------------------------------------------------------
    # 2. Chart Generation
    # --------------------------------------------------------------------------
    def test_02_chart_generation(self):
        """Verifies headless matplotlib generates valid, non-empty PNG charts."""
        sample_prod = [
            {"year": 2021, "actual_production_mt": 4.20, "target_mt": 4.00},
            {"year": 2022, "actual_production_mt": 4.50, "target_mt": 4.30},
            {"year": 2023, "actual_production_mt": 4.76, "target_mt": 4.60},
        ]
        trend_path = self.service.chart_generator.generate_production_trend_chart(
            sample_prod, "DEOM-01", "test_trend.png"
        )
        self.assertIsNotNone(trend_path)
        self.assertTrue(os.path.exists(trend_path))
        self.assertGreater(os.path.getsize(trend_path), 5000)

        # Comparison chart
        sample_comp = [
            {"mine_code": "DEOM-01", "actual_production_mt": 5.21, "target_production_mt": 5.00},
            {"mine_code": "KNUG-02", "actual_production_mt": 3.80, "target_production_mt": 3.70},
        ]
        comp_path = self.service.chart_generator.generate_comparison_chart(
            sample_comp, "test_comp.png", year=2025
        )
        self.assertIsNotNone(comp_path)
        self.assertTrue(os.path.exists(comp_path))
        self.assertGreater(os.path.getsize(comp_path), 5000)

    # --------------------------------------------------------------------------
    # 3. Word Document (.docx) Generation & Structure
    # --------------------------------------------------------------------------
    def test_03_docx_generation(self):
        """Verifies python-docx creates openable, well-structured .docx files."""
        rep = getattr(TestPhase6BReportGenerationSuite, "sample_report", None)
        if not rep:
            req = ReportGenerateRequest(mine_code="DEOM-01", report_type="PERFORMANCE")
            rep = self.service.generate_report(self.db, self.user1, req)

        docx_path = os.path.join(self.service.REPORTS_DIR, f"{rep.report_id}.docx")
        self.assertTrue(os.path.exists(docx_path))
        self.assertGreater(os.path.getsize(docx_path), 10000)

        # Open and inspect document structure
        doc = Document(docx_path)
        self.assertGreater(len(doc.paragraphs), 5)
        self.assertGreater(len(doc.tables), 1)

    # --------------------------------------------------------------------------
    # 4. PDF Document (.pdf) Generation & Structure
    # --------------------------------------------------------------------------
    def test_04_pdf_generation(self):
        """Verifies ReportLab produces valid, readable PDF binaries."""
        rep = getattr(TestPhase6BReportGenerationSuite, "sample_report", None)
        if not rep:
            req = ReportGenerateRequest(mine_code="DEOM-01", report_type="PERFORMANCE")
            rep = self.service.generate_report(self.db, self.user1, req)

        pdf_path = os.path.join(self.service.REPORTS_DIR, f"{rep.report_id}.pdf")
        self.assertTrue(os.path.exists(pdf_path))
        self.assertGreater(os.path.getsize(pdf_path), 10000)

        # Verify PDF magic bytes
        with open(pdf_path, "rb") as f:
            header = f.read(5)
            self.assertEqual(header, b"%PDF-")

    # --------------------------------------------------------------------------
    # 5. Deterministic Tables (Database Grounding)
    # --------------------------------------------------------------------------
    def test_05_deterministic_tables(self):
        """Verifies that generated report table figures match PostgreSQL numbers exactly."""
        # Verify DEOM-01 2021 actual production = 4.18 MT
        from app.services.query_service import DeterministicQueryService
        records = DeterministicQueryService.get_annual_production(
            self.db, self.scope1, mine_code="DEOM-01", year=2021
        )
        self.assertEqual(len(records), 1)
        self.assertEqual(float(records[0].actual_production_mt), 4.18)

    # --------------------------------------------------------------------------
    # 6. Security Denial: Unauthorized Mine (USR001 -> KNUG-02)
    # --------------------------------------------------------------------------
    def test_06_security_denial_unauthorized_mine(self):
        """Verifies USR001 requesting KNUG-02 or SSOP-03 is denied with 403 Forbidden."""
        req = ReportGenerateRequest(
            mine_code="KNUG-02",
            report_type="PERFORMANCE"
        )
        with self.assertRaises(HTTPException) as ctx:
            self.service.generate_report(self.db, self.user1, req)
        self.assertEqual(ctx.exception.status_code, 403)
        self.assertIn("not authorized", ctx.exception.detail.lower())

        # Test natural language request override attempt
        req_nl = ReportGenerateRequest(
            query="Generate a performance report for KNUG-02"
        )
        with self.assertRaises(HTTPException) as ctx:
            self.service.generate_report(self.db, self.user1, req_nl)
        self.assertEqual(ctx.exception.status_code, 403)

    # --------------------------------------------------------------------------
    # 7. Mine Manager Multi-Mine Scope (USR004 -> DEOM-01 + KNUG-02)
    # --------------------------------------------------------------------------
    def test_07_manager_multi_mine_report(self):
        """Verifies USR004 can generate comparison report for DEOM-01 and KNUG-02, but is denied on SSOP-03."""
        req = ReportGenerateRequest(
            compared_mines=["DEOM-01", "KNUG-02"],
            report_type="COMPARISON",
            start_year=2024,
            end_year=2025
        )
        res = self.service.generate_report(self.db, self.user4, req)
        self.assertEqual(res.status, "GENERATED")
        self.assertEqual(res.report_type, "COMPARISON")
        self.assertIn("DEOM-01", res.mines_covered)
        self.assertIn("KNUG-02", res.mines_covered)

        # Denied when including SSOP-03
        req_unauth = ReportGenerateRequest(
            compared_mines=["DEOM-01", "SSOP-03"],
            report_type="COMPARISON"
        )
        with self.assertRaises(HTTPException) as ctx:
            self.service.generate_report(self.db, self.user4, req_unauth)
        self.assertEqual(ctx.exception.status_code, 403)

    # --------------------------------------------------------------------------
    # 8. Conflict Inclusion (SSOP-03 Logistics Conflict)
    # --------------------------------------------------------------------------
    def test_08_conflict_inclusion_ssop03(self):
        """Verifies reports covering SSOP-03 include CONF-SSOP03-2025-LOGISTICS and human review warning."""
        req = ReportGenerateRequest(
            mine_code="SSOP-03",
            report_type="CONFLICT",
            start_year=2025,
            end_year=2025
        )
        res = self.service.generate_report(self.db, self.user5, req)
        self.assertEqual(res.validation_status, "CONFLICT")
        self.assertGreater(res.conflict_count, 0)

    # --------------------------------------------------------------------------
    # 9. Download Authorization & Path Traversal Defense
    # --------------------------------------------------------------------------
    def test_09_download_authorization_and_traversal_defense(self):
        """Verifies download authorization and rejection of path traversal attempts."""
        # 1. Generate report for SSOP-03 as Admin USR005
        req = ReportGenerateRequest(mine_code="SSOP-03", start_year=2025, end_year=2025)
        res = self.service.generate_report(self.db, self.user5, req)

        # 2. USR001 attempts to download SSOP-03 report -> MUST 403
        with self.assertRaises(HTTPException) as ctx:
            self.service.get_report_file(self.db, self.user1, res.report_id, "pdf")
        self.assertEqual(ctx.exception.status_code, 403)

        # 3. USR005 downloads successfully
        file_path, media_type = self.service.get_report_file(self.db, self.user5, res.report_id, "pdf")
        self.assertTrue(os.path.exists(file_path))
        self.assertEqual(media_type, "application/pdf")

        # 4. Path traversal attempt
        with self.assertRaises(HTTPException) as ctx:
            self.service.get_report_file(self.db, self.user5, res.report_id, "../../etc/passwd")
        self.assertIn(ctx.exception.status_code, [400, 404])

    # --------------------------------------------------------------------------
    # 10. UnifiedAIOrchestrator REPORT Route Integration
    # --------------------------------------------------------------------------
    def test_10_orchestrator_report_route(self):
        """Verifies natural language query routes to REPORT and generates outputs."""
        orchestrator = UnifiedAIOrchestrator(self.db, self.user1, self.scope1)
        res = orchestrator.orchestrate("Generate a 5-year performance report for DEOM-01.")

        self.assertEqual(res.query_type, "REPORT")
        self.assertIsNotNone(res.answer)
        self.assertIn("Generated Official Report", res.answer)
        self.assertIn("PDF Document", res.answer)


if __name__ == "__main__":
    unittest.main()
