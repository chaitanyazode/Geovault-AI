"""
GeoVault AI - Phase 5B Natural Language Query, RAG & Grounded Qwen Test Suite
Tests:
1. Deterministic Query Router classification
2. LlamaIndex ScopedVectorRetriever authorization pre-filtering
3. Qwen3-8B local reasoner context prompt & reasoning_content resolution
4. End-to-end natural language queries (SQL, ANALYTICS, RAG, HYBRID, CONFLICT)
5. Strict security denials (unauthorized mine access, restricted clearance)
"""

import unittest
from sqlalchemy.orm import Session
from fastapi import HTTPException

from app.core.database import SessionLocal
from app.security.service import AuthorizationService
from app.security.context import UserContext, AuthorizedScope
from app.ai.query_router import DeterministicQueryRouter, RoutedQuery
from app.ai.qwen_reasoner import QwenReasonerClient
from app.ai.hybrid_pipeline import HybridIntelligencePipeline
from app.rag.retriever import ScopedVectorRetriever
from app.schemas.query import GroundedQueryResponse


class TestNaturalQueryRAGSuite(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.db: Session = SessionLocal()
        cls.user1: UserContext = AuthorizationService.resolve_user_context(cls.db, "USR001")
        cls.scope1: AuthorizedScope = AuthorizationService.get_authorized_scope(cls.user1)

        cls.user2: UserContext = AuthorizationService.resolve_user_context(cls.db, "USR002")
        cls.scope2: AuthorizedScope = AuthorizationService.get_authorized_scope(cls.user2)

        cls.user4: UserContext = AuthorizationService.resolve_user_context(cls.db, "USR004")
        cls.scope4: AuthorizedScope = AuthorizationService.get_authorized_scope(cls.user4)

        cls.user5: UserContext = AuthorizationService.resolve_user_context(cls.db, "USR005")
        cls.scope5: AuthorizedScope = AuthorizationService.get_authorized_scope(cls.user5)

    @classmethod
    def tearDownClass(cls):
        cls.db.close()

    # --------------------------------------------------------------------------
    # 1. Deterministic Query Router Tests
    # --------------------------------------------------------------------------
    def test_01_query_router_classification(self):
        """Validates deterministic routing into SQL, ANALYTICS, RAG, HYBRID, REPORT, TOPIC."""
        # SQL Route
        r1 = DeterministicQueryRouter.route_query("What was DEOM-01 production in FY2024?")
        self.assertEqual(r1.route, "SQL")
        self.assertEqual(r1.target_mine, "DEOM-01")
        self.assertEqual(r1.target_year, 2024)

        # ANALYTICS Route (Comparison)
        r2 = DeterministicQueryRouter.route_query("Compare DEOM-01 and KNUG-02 production.")
        self.assertEqual(r2.route, "ANALYTICS")
        self.assertIn("DEOM-01", r2.compared_mines)
        self.assertIn("KNUG-02", r2.compared_mines)

        # RAG Route (Qualitative Geology inquiry)
        r3 = DeterministicQueryRouter.route_query("What geological issues were reported for DEOM-01?")
        self.assertEqual(r3.route, "RAG")
        self.assertEqual(r3.target_mine, "DEOM-01")

        # HYBRID Route (Causality / Why did production change)
        r4 = DeterministicQueryRouter.route_query("Why did production change between 2023 and 2024?")
        self.assertEqual(r4.route, "HYBRID")

        # REPORT Route
        r5 = DeterministicQueryRouter.route_query("Generate a mining performance report for Dharani East.")
        self.assertEqual(r5.route, "REPORT")
        self.assertEqual(r5.target_mine, "DEOM-01")

        # TOPIC Route
        r6 = DeterministicQueryRouter.route_query("What are the major topics and recurring terminology?")
        self.assertEqual(r6.route, "TOPIC")

        # CONFLICT Check Route
        r7 = DeterministicQueryRouter.route_query("What conflicts exist in the data for SSOP-03?")
        self.assertEqual(r7.route, "SQL")
        self.assertEqual(r7.target_mine, "SSOP-03")

    # --------------------------------------------------------------------------
    # 2. LlamaIndex ScopedVectorRetriever Pre-Retrieval Authorization
    # --------------------------------------------------------------------------
    def test_02_llamaindex_scoped_vector_retriever(self):
        """Verifies that ScopedVectorRetriever enforces authorization scope inside pgvector."""
        retriever = ScopedVectorRetriever(
            db=self.db,
            scope=self.scope1,  # USR001: DEOM-01 only
            top_k=5,
        )
        nodes, evidence_items = retriever.retrieve_with_evidence("overburden bench stability water ingress")

        self.assertGreater(len(nodes), 0)
        for node in nodes:
            mine = node.node.metadata.get("mine_code")
            # Must strictly be authorized for USR001 (DEOM-01, GEVRA, or national ALL)
            self.assertIn(mine, ["DEOM-01", "GEVRA", None, "ALL"])
            self.assertNotEqual(mine, "KNUG-02")
            self.assertNotEqual(mine, "SSOP-03")

        for ev in evidence_items:
            self.assertIn(ev.mine_code, ["DEOM-01", "GEVRA", None, "ALL"])
            self.assertNotEqual(ev.mine_code, "KNUG-02")
            self.assertNotEqual(ev.mine_code, "SSOP-03")

    # --------------------------------------------------------------------------
    # 3. Local Qwen Context Prompt & Reasoning Content Resolution
    # --------------------------------------------------------------------------
    def test_03_qwen_context_and_reasoning_handling(self):
        """Tests that user prompt contains GeoVault governance rules and reasoning content is parsed."""
        client = QwenReasonerClient()
        prompt = client.build_user_context_prompt(
            query="What was DEOM-01 production in 2024?",
            route="SQL",
            facts=[{"mine_code": "DEOM-01", "year": 2024, "actual_production_mt": 5.02}],
            analytics={"total": 5.02},
            evidence_items=[],
            validation_status="VERIFIED",
            conflicts=[],
            data_gaps=[],
        )
        self.assertTrue("USER QUERY: What was DEOM-01 production in 2024?" in prompt or "<user_query>What was DEOM-01 production in 2024?</user_query>" in prompt)
        self.assertTrue("EXECUTION ROUTE: SQL" in prompt or "<execution_route>SQL</execution_route>" in prompt)
        self.assertTrue("VALIDATION STATUS: VERIFIED" in prompt or "<validation_status>VERIFIED</validation_status>" in prompt)
        self.assertIn("DEOM-01", prompt)
        self.assertIn("5.02", prompt)


        # Verify fallback deterministic generator
        summary = client._generate_fallback_deterministic_summary(
            query="What was DEOM-01 production?",
            route="SQL",
            facts=[{"mine_code": "DEOM-01", "year": 2024, "actual_production_mt": 5.02, "target_mt": 5.00}],
            analytics=None,
            conflicts=[],
        )
        self.assertIn("DEOM-01 in FY2024 recorded actual production of 5.02 MT", summary)

    # --------------------------------------------------------------------------
    # 4. End-to-End Query: SQL Route (DEOM-01 FY2024)
    # --------------------------------------------------------------------------
    def test_04_e2e_sql_production_query(self):
        """End-to-End: 'What was DEOM-01 production in FY2024?' -> SQL route with verified facts."""
        pipeline = HybridIntelligencePipeline(self.db, self.user1, self.scope1)
        res: GroundedQueryResponse = pipeline.process_query("What was DEOM-01 production in FY2024?")

        self.assertEqual(res.query_type, "SQL")
        self.assertEqual(res.validation_status, "VERIFIED")
        self.assertIsNotNone(res.structured_results)
        facts = res.structured_results["facts"]
        self.assertEqual(len(facts), 1)
        self.assertEqual(float(facts[0]["actual_production_mt"]), 5.02)
        self.assertGreater(len(res.evidence), 0)
        self.assertTrue(res.evidence[0].evidence_id.startswith("EV-PRODUCTION_A-DEOM-01-2024"))
        self.assertIn("5.02", res.answer)

    # --------------------------------------------------------------------------
    # 5. End-to-End Query: ANALYTICS Route (Comparison)
    # --------------------------------------------------------------------------
    def test_05_e2e_analytics_comparison_query(self):
        """End-to-End: Manager USR004 comparing DEOM-01 and KNUG-02 production."""
        pipeline = HybridIntelligencePipeline(self.db, self.user4, self.scope4)
        res: GroundedQueryResponse = pipeline.process_query("Compare DEOM-01 and KNUG-02 production.")

        self.assertEqual(res.query_type, "ANALYTICS")
        self.assertIn(res.validation_status, ["VERIFIED", "CONFLICT"])
        self.assertIsNotNone(res.structured_results)
        analytics = res.structured_results["analytics"]
        self.assertIn("comparisons", analytics)
        mine_codes = [c["mine_code"] for c in analytics["comparisons"]]
        self.assertIn("DEOM-01", mine_codes)
        self.assertIn("KNUG-02", mine_codes)
        self.assertNotIn("SSOP-03", mine_codes)  # Not assigned to manager

    # --------------------------------------------------------------------------
    # 6. End-to-End Query: RAG Route (Geological Issues)
    # --------------------------------------------------------------------------
    def test_06_e2e_rag_geological_query(self):
        """End-to-End: 'What geological issues were reported for DEOM-01?' -> RAG route with document evidence."""
        pipeline = HybridIntelligencePipeline(self.db, self.user1, self.scope1)
        res: GroundedQueryResponse = pipeline.process_query("What geological issues were reported for DEOM-01?")

        self.assertEqual(res.query_type, "RAG")
        self.assertGreater(len(res.evidence), 0)
        for ev in res.evidence:
            self.assertIn(ev.mine_code, ["DEOM-01", None, "ALL"])
            self.assertNotEqual(ev.mine_code, "KNUG-02")
        self.assertGreater(len(res.source_references), 0)

    # --------------------------------------------------------------------------
    # 7. End-to-End Query: HYBRID Route (Why did production change)
    # --------------------------------------------------------------------------
    def test_07_e2e_hybrid_production_change_query(self):
        """End-to-End: 'Why did production change?' -> HYBRID route with facts + document chunks."""
        pipeline = HybridIntelligencePipeline(self.db, self.user1, self.scope1)
        res: GroundedQueryResponse = pipeline.process_query("Why did production change between 2023 and 2024 for DEOM-01?")

        self.assertEqual(res.query_type, "HYBRID")
        self.assertIsNotNone(res.structured_results)
        # Has both structured facts and document evidence
        self.assertGreater(len(res.structured_results["facts"]), 0)
        self.assertGreater(len(res.evidence), 0)

    # --------------------------------------------------------------------------
    # 8. End-to-End Query: Conflict Surfacing (SSOP-03)
    # --------------------------------------------------------------------------
    def test_08_e2e_conflict_surfacing_query(self):
        """End-to-End: SSOP-03 conflict query explicitly surfaces CONF-SSOP03-2025-LOGISTICS."""
        pipeline = HybridIntelligencePipeline(self.db, self.user5, self.scope5)
        res: GroundedQueryResponse = pipeline.process_query("What conflicts exist in the data for SSOP-03 in 2025?")

        self.assertEqual(res.validation_status, "CONFLICT")
        self.assertEqual(res.confidence_status, "CONFLICT_DETECTED")
        self.assertGreater(len(res.conflicts), 0)
        conf_ids = [c.conflict_id for c in res.conflicts]
        self.assertIn("CONF-SSOP03-2025-LOGISTICS", conf_ids)

    # --------------------------------------------------------------------------
    # 9. Security Denials: USR001 Denied Access to KNUG-02
    # --------------------------------------------------------------------------
    def test_09_security_denial_unauthorized_mine(self):
        """USR001 cannot query or compare KNUG-02 via natural language; strictly returns 403 Forbidden."""
        pipeline = HybridIntelligencePipeline(self.db, self.user1, self.scope1)

        # Direct query for unauthorized mine
        with self.assertRaises(HTTPException) as ctx:
            pipeline.process_query("What was KNUG-02 production in FY2024?")
        self.assertEqual(ctx.exception.status_code, 403)
        self.assertIn("Access Denied", ctx.exception.detail)

        # Comparison including unauthorized mine
        with self.assertRaises(HTTPException) as ctx:
            pipeline.process_query("Compare DEOM-01 and KNUG-02 production.")
        self.assertEqual(ctx.exception.status_code, 403)
        self.assertIn("Access Denied", ctx.exception.detail)

    # --------------------------------------------------------------------------
    # 10. Security Denials: Restricted Geology Access
    # --------------------------------------------------------------------------
    def test_10_security_denial_restricted_geology(self):
        """USR001 (INTERNAL clearance) cannot retrieve RESTRICTED geology chunks through RAG."""
        retriever = ScopedVectorRetriever(
            db=self.db,
            scope=self.scope1,  # Max clearance INTERNAL
            top_k=10,
        )
        nodes, _ = retriever.retrieve_with_evidence("geotechnical core strata fault zone")
        for node in nodes:
            classification = node.node.metadata.get("classification")
            self.assertIn(classification, ["PUBLIC", "INTERNAL"])
            self.assertNotEqual(classification, "RESTRICTED")
            self.assertNotEqual(classification, "CONFIDENTIAL")


if __name__ == "__main__":
    unittest.main()
