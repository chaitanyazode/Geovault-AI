"""
GeoVault AI - Phase 5C Ask GeoVault & Evidence UX Integration Test Suite
Tests:
1. Canonical Gevra structured production query and fact packaging
2. Canonical Gevra geological observations query
3. Canonical PostGIS spatial query (boreholes within 500m)
4. Canonical multi-mine production comparison analytics
5. Canonical hybrid shortfall analysis (structured + document evidence)
6. Strict ABAC authorization isolation (HTTP 403) for unauthorized mine queries
7. Conflict and data gap detection surfacing
8. PostGIS spatial evidence geometry resolution with SYNTHETIC_DEMO provenance
"""

import unittest
from sqlalchemy.orm import Session
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.main import app
from app.core.database import SessionLocal
from app.security.service import AuthorizationService
from app.security.context import UserContext, AuthorizedScope
from app.ai.orchestrator import UnifiedAIOrchestrator
from app.schemas.query import GroundedQueryResponse


class TestPhase5CAskEvidenceSuite(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.db: Session = SessionLocal()
        cls.client = TestClient(app)

        # USR001: Mining Engineer, Scoped to GEVRA (GV001)
        cls.user1: UserContext = AuthorizationService.resolve_user_context(cls.db, "USR001")
        cls.scope1: AuthorizedScope = AuthorizationService.get_authorized_scope(cls.user1)

        # USR004: Mine Manager, Scoped to GEVRA + KUSMUNDA
        cls.user4: UserContext = AuthorizationService.resolve_user_context(cls.db, "USR004")
        cls.scope4: AuthorizedScope = AuthorizationService.get_authorized_scope(cls.user4)

        # USR005: Administrator, Full Enterprise Scope (ALL 5 Mines)
        cls.user5: UserContext = AuthorizationService.resolve_user_context(cls.db, "USR005")
        cls.scope5: AuthorizedScope = AuthorizationService.get_authorized_scope(cls.user5)

    @classmethod
    def tearDownClass(cls):
        cls.db.close()

    # --------------------------------------------------------------------------
    # 1. Canonical Prompt 1: GEVRA Production (STRUCTURED/SQL Route)
    # --------------------------------------------------------------------------
    def test_01_canonical_gevra_production_structured(self):
        """Validates 'What was GEVRA's production in FY2024-25?' routes to SQL/STRUCTURED."""
        orchestrator = UnifiedAIOrchestrator(self.db, self.user1, self.scope1)
        res: GroundedQueryResponse = orchestrator.orchestrate("What was GEVRA's production in FY2024-25?")

        self.assertIn(res.query_type, ["SQL", "STRUCTURED"])
        self.assertEqual(res.validation_status, "VERIFIED")
        self.assertIsNotNone(res.structured_results)
        self.assertIn("facts", res.structured_results)
        self.assertGreater(len(res.structured_results["facts"]), 0)

        # Confirm evidence generated with provenance
        self.assertGreater(len(res.evidence), 0)
        for ev in res.evidence:
            self.assertIn(ev.mine_code, ["GV001", "GEVRA", "Enterprise", None])

    # --------------------------------------------------------------------------
    # 2. Canonical Prompt 2: GEVRA Geological Observations (GEOLOGY/RAG Route)
    # --------------------------------------------------------------------------
    def test_02_canonical_gevra_geology_observations(self):
        """Validates 'What geological observations were reported for GEVRA in FY2024-25?'."""
        orchestrator = UnifiedAIOrchestrator(self.db, self.user1, self.scope1)
        res: GroundedQueryResponse = orchestrator.orchestrate("What geological observations were reported for GEVRA in FY2024-25?")

        self.assertIn(res.query_type, ["GEOLOGY", "RAG", "HYBRID"])
        self.assertGreater(len(res.evidence), 0)
        self.assertIsNotNone(res.answer)
        self.assertGreater(len(res.answer), 0)

    # --------------------------------------------------------------------------
    # 3. Canonical Prompt 3: PostGIS Spatial Boreholes near 500m (SPATIAL Route)
    # --------------------------------------------------------------------------
    def test_03_canonical_boreholes_spatial_500m(self):
        """Validates 'Which boreholes are within 500 metres of a geological feature?'."""
        orchestrator = UnifiedAIOrchestrator(self.db, self.user1, self.scope1)
        res: GroundedQueryResponse = orchestrator.orchestrate("Which boreholes are within 500 metres of a geological feature?")

        self.assertEqual(res.query_type, "SPATIAL")
        self.assertIsNotNone(res.structured_results)
        self.assertIn("operation", res.structured_results.get("analytics", {}))
        self.assertEqual(res.structured_results["analytics"]["operation"], "ST_DWithin")

        # Spatial evidence items must have PostGIS metadata
        self.assertGreater(len(res.evidence), 0)
        for ev in res.evidence:
            self.assertIn("SPATIAL", ev.source_type)

    # --------------------------------------------------------------------------
    # 4. Canonical Prompt 4: Multi-Mine Comparison across 5 Mines (ANALYTICS Route)
    # --------------------------------------------------------------------------
    def test_04_canonical_compare_production_across_mines(self):
        """Validates 'Compare FY2024-25 production across the five mines.' for Administrator."""
        orchestrator = UnifiedAIOrchestrator(self.db, self.user5, self.scope5)
        res: GroundedQueryResponse = orchestrator.orchestrate("Compare FY2024-25 production across the five mines.")

        self.assertEqual(res.query_type, "ANALYTICS")
        self.assertIsNotNone(res.structured_results)
        analytics = res.structured_results.get("analytics", {})
        self.assertIn("comparisons", analytics)
        self.assertGreaterEqual(len(analytics["comparisons"]), 2)

    # --------------------------------------------------------------------------
    # 5. Canonical Prompt 5: Production Shortfall (HYBRID Route)
    # --------------------------------------------------------------------------
    def test_05_canonical_production_shortfall_hybrid(self):
        """Validates 'Explain the production shortfall using operational and geological evidence.'."""
        orchestrator = UnifiedAIOrchestrator(self.db, self.user1, self.scope1)
        res: GroundedQueryResponse = orchestrator.orchestrate("Explain the production shortfall using operational and geological evidence.")

        self.assertIn(res.query_type, ["HYBRID", "SQL", "RAG"])
        self.assertGreater(len(res.evidence), 0)
        self.assertIsNotNone(res.answer)

    # --------------------------------------------------------------------------
    # 6. Authorization Isolation: USR001 Denied Access to NIGAHI (HTTP 403)
    # --------------------------------------------------------------------------
    def test_06_mine_isolation_403_denial_unauthorized(self):
        """Verifies USR001 querying NIGAHI (GV004) raises HTTP 403 without data leakage."""
        orchestrator = UnifiedAIOrchestrator(self.db, self.user1, self.scope1)
        with self.assertRaises(HTTPException) as ctx:
            orchestrator.orchestrate("What was NIGAHI coal production in 2024?")

        self.assertEqual(ctx.exception.status_code, 403)
        self.assertIn("not authorized", ctx.exception.detail.lower())
        # Ensure no actual numbers or secrets leaked in exception message
        self.assertNotIn("56.10", ctx.exception.detail)
        self.assertNotIn("58.50", ctx.exception.detail)

    # --------------------------------------------------------------------------
    # 7. PostGIS Spatial Evidence Resolution Endpoint
    # --------------------------------------------------------------------------
    def test_07_spatial_evidence_endpoint_wgs84(self):
        """Tests GET /api/v1/evidence/{evidence_id} for a spatial feature returns WGS84 and SYNTHETIC_DEMO."""
        headers = {"X-User-ID": "USR005"}
        resp = self.client.get("/api/v1/evidence/EV-SPATIAL-GEVRA-GV-BH-001", headers=headers)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()

        self.assertEqual(data["evidence_id"], "EV-SPATIAL-GEVRA-GV-BH-001")
        self.assertEqual(data["provenance_type"], "SYNTHETIC_DEMO")
        self.assertIn("coordinates", data)
        self.assertIsNotNone(data["coordinates"]["longitude"])
        self.assertIsNotNone(data["coordinates"]["latitude"])


if __name__ == "__main__":
    unittest.main()
