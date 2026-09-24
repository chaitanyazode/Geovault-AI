"""
GeoVault AI - Automated Security & Authorization Test Suite
Verifies RBAC + ABAC enforcement, scope boundaries, anti-leakage aggregations,
and pre-retrieval vector search constraints.
"""

import sys
import unittest
from typing import List
from sqlalchemy import select, func

from app.core.database import SessionLocal
from app.models.master import User
from app.models.operational import ProductionAnnual
from app.models.knowledge import DocumentChunk
from app.models.governance import Conflict
from app.security.clearance import is_clearance_sufficient, get_clearance_rank
from app.security.context import UserContext, AuthorizedScope
from app.security.service import AuthorizationService
from app.security.roles import Permission, has_permission
from app.ingestion.unstructured import get_embedding_model


class TestAuthorizationSuite(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.db = SessionLocal()
        # Resolve Demo Users
        cls.user1 = AuthorizationService.resolve_user_context(cls.db, "USR001")  # Mining Eng, DEOM-01, INTERNAL
        cls.user2 = AuthorizationService.resolve_user_context(cls.db, "USR002")  # Geology Eng, DEOM-01, RESTRICTED
        cls.user3 = AuthorizationService.resolve_user_context(cls.db, "USR003")  # Transport Eng, KNUG-02, INTERNAL
        cls.user4 = AuthorizationService.resolve_user_context(cls.db, "USR004")  # Mine Manager, DEOM-01 + KNUG-02, RESTRICTED
        cls.user5 = AuthorizationService.resolve_user_context(cls.db, "USR005")  # Administrator, ALL, CONFIDENTIAL

        # Resolve Scopes
        cls.scope1 = AuthorizationService.get_authorized_scope(cls.user1)
        cls.scope2 = AuthorizationService.get_authorized_scope(cls.user2)
        cls.scope3 = AuthorizationService.get_authorized_scope(cls.user3)
        cls.scope4 = AuthorizationService.get_authorized_scope(cls.user4)
        cls.scope5 = AuthorizationService.get_authorized_scope(cls.user5)

    @classmethod
    def tearDownClass(cls):
        cls.db.close()

    # --------------------------------------------------------------------------
    # Scenario 1: Mine A user -> Mine A allowed
    # --------------------------------------------------------------------------
    def test_01_mine_a_user_allowed_mine_a(self):
        """USR001 (assigned to DEOM-01) querying DEOM-01 structured records succeeds."""
        self.assertTrue(self.scope1.is_mine_permitted("DEOM-01"))
        
        base_query = select(ProductionAnnual).where(ProductionAnnual.mine_code == "DEOM-01")
        scoped_query = AuthorizationService.scope_structured_query(base_query, ProductionAnnual, self.scope1)
        records = self.db.scalars(scoped_query).all()

        self.assertGreater(len(records), 0, "USR001 should retrieve DEOM-01 production records.")
        for r in records:
            self.assertEqual(r.mine_code, "DEOM-01", "Returned record must strictly belong to DEOM-01.")

    # --------------------------------------------------------------------------
    # Scenario 2: Mine A user -> Mine B denied
    # --------------------------------------------------------------------------
    def test_02_mine_a_user_denied_mine_b(self):
        """USR001 (DEOM-01) querying KNUG-02 records is strictly denied and filtered out."""
        # 1. Attribute check
        self.assertFalse(self.scope1.is_mine_permitted("KNUG-02"), "USR001 must NOT be permitted to access KNUG-02.")

        # 2. Query Scoper check: If user attempts to query KNUG-02, the scoper adds mine_code IN ('DEOM-01')
        base_query = select(ProductionAnnual).where(ProductionAnnual.mine_code == "KNUG-02")
        scoped_query = AuthorizationService.scope_structured_query(base_query, ProductionAnnual, self.scope1)
        records = self.db.scalars(scoped_query).all()

        self.assertEqual(len(records), 0, "Query scoper must guarantee zero records returned when querying unauthorized mine.")

    # --------------------------------------------------------------------------
    # Scenario 3: Restricted geology access denied when clearance/dept insufficient
    # --------------------------------------------------------------------------
    def test_03_restricted_geology_access_denied(self):
        """USR001 (Mining/INTERNAL) cannot access RESTRICTED Geology resources. USR002 (Geology/RESTRICTED) can."""
        # Check clearance rank evaluation
        self.assertFalse(is_clearance_sufficient(self.user1.clearance_level, "RESTRICTED"))
        self.assertTrue(is_clearance_sufficient(self.user2.clearance_level, "RESTRICTED"))

        # Check resource authorization
        self.assertFalse(
            self.scope1.is_resource_authorized(mine_code="DEOM-01", department="Geology", classification="RESTRICTED"),
            "USR001 must be denied access to RESTRICTED Geology records."
        )
        self.assertTrue(
            self.scope2.is_resource_authorized(mine_code="DEOM-01", department="Geology", classification="RESTRICTED"),
            "USR002 must be permitted access to DEOM-01 RESTRICTED Geology records."
        )

    # --------------------------------------------------------------------------
    # Scenario 4: Authorized manager permitted across assigned mines only
    # --------------------------------------------------------------------------
    def test_04_manager_multi_mine_permitted_and_unassigned_denied(self):
        """USR004 (Mine Manager) can access DEOM-01 and KNUG-02, but is strictly denied on SSOP-03."""
        self.assertTrue(self.scope4.is_mine_permitted("DEOM-01"), "Manager must have access to DEOM-01.")
        self.assertTrue(self.scope4.is_mine_permitted("KNUG-02"), "Manager must have access to KNUG-02.")
        self.assertFalse(self.scope4.is_mine_permitted("SSOP-03"), "Manager must NOT have access to unassigned SSOP-03.")

        # Query all production annual records scoped to manager
        base_query = select(ProductionAnnual)
        scoped_query = AuthorizationService.scope_structured_query(base_query, ProductionAnnual, self.scope4)
        records = self.db.scalars(scoped_query).all()

        returned_mines = {r.mine_code for r in records}
        self.assertIn("DEOM-01", returned_mines)
        self.assertIn("KNUG-02", returned_mines)
        self.assertNotIn("SSOP-03", returned_mines, "SSOP-03 records must NEVER appear in manager's results.")

    # --------------------------------------------------------------------------
    # Scenario 5: Unauthorized data never enters vector retrieval
    # --------------------------------------------------------------------------
    def test_05_vector_search_pre_retrieval_filtering(self):
        """Vector search with USR001 scope NEVER returns chunks from KNUG-02 or SSOP-03."""
        emb_model = get_embedding_model()
        q_vec = emb_model.encode("water ingress Koyna panel fault line", normalize_embeddings=True).tolist()

        # Vector search scoped to USR001 (DEOM-01 only)
        results = AuthorizationService.scoped_vector_search(
            db=self.db,
            query_embedding=q_vec,
            scope=self.scope1,
            top_k=10
        )

        for chunk, score in results:
            self.assertIn(
                chunk.mine_code, ["DEOM-01", "GEVRA", None],
                f"Unauthorized chunk {chunk.chunk_id} from mine {chunk.mine_code} leaked into USR001 vector results!"
            )
            self.assertNotEqual(chunk.mine_code, "KNUG-02")
            self.assertNotEqual(chunk.mine_code, "SSOP-03")
            # Ensure classification rank is within USR001 clearance (INTERNAL)
            self.assertTrue(
                is_clearance_sufficient(self.user1.clearance_level, chunk.classification),
                f"Chunk {chunk.chunk_id} classification {chunk.classification} exceeds USR001 clearance!"
            )

    # --------------------------------------------------------------------------
    # --------------------------------------------------------------------------
    # Scenario 6: Unauthorized document/evidence access is denied
    # --------------------------------------------------------------------------
    def test_06_unauthorized_evidence_access_denied(self):
        """Direct inspection of evidence or chunk belonging to unpermitted mine/clearance is denied."""
        # Find a RESTRICTED Geology chunk belonging to KNUG-02
        knug_chunk = self.db.scalars(
            select(DocumentChunk).where(DocumentChunk.mine_code == "KNUG-02").limit(1)
        ).first()
        self.assertIsNotNone(knug_chunk, "Fixture requires at least one KNUG-02 chunk in DB.")

        # 1. Attempt validation for USR001 (DEOM-01 only) -> DENIED due to unassigned mine
        can_access_u1 = AuthorizationService.validate_evidence_access(self.user1, self.scope1, knug_chunk)
        self.assertFalse(can_access_u1, "USR001 must be denied access to KNUG-02 evidence chunk.")

        # 2. Attempt validation for USR003 (KNUG-02 Transportation / INTERNAL) -> DENIED due to department/clearance mismatch
        can_access_u3 = AuthorizationService.validate_evidence_access(self.user3, self.scope3, knug_chunk)
        self.assertFalse(can_access_u3, "USR003 (Transportation / INTERNAL) must be denied access to RESTRICTED Geology chunk.")

        # 3. Attempt validation for USR004 (Mine Manager assigned to DEOM-01 + KNUG-02, ALL depts, RESTRICTED) -> ALLOWED
        can_access_u4 = AuthorizationService.validate_evidence_access(self.user4, self.scope4, knug_chunk)
        self.assertTrue(can_access_u4, "USR004 (Manager for KNUG-02, RESTRICTED) must be granted access to KNUG-02 chunk.")

    # --------------------------------------------------------------------------
    # Scenario 7: Aggregations cannot leak unauthorized mine data
    # --------------------------------------------------------------------------
    def test_07_aggregations_prevent_unauthorized_cross_mine_leakage(self):
        """
        Total production SUM for USR001 reflects DEOM-01 + GEVRA (23.69 + 297.10 = 320.79 MT).
        Total for USR004 reflects DEOM-01 + KNUG-02 + GEVRA (23.69 + 7.88 + 297.10 = 328.67 MT).
        Total for USR005 reflects Enterprise ALL (23.69 + 7.88 + 33.44 + 297.10 = 362.11 MT).
        SSOP-03 (33.44 MT) remains strictly excluded from USR001 and USR004.
        """
        # 1. Aggregation for USR001 (DEOM-01 + GEVRA)
        agg_u1 = AuthorizationService.scoped_aggregate(
            db=self.db,
            model=ProductionAnnual,
            metric_column=ProductionAnnual.actual_production_mt,
            group_by_column=None,
            scope=self.scope1,
            agg_func="SUM"
        )
        total_u1 = agg_u1[0]["value"]
        self.assertAlmostEqual(total_u1, 320.79, places=2, msg="USR001 total must match DEOM-01 (23.69) + GEVRA (297.10) = 320.79 MT.")

        # 2. Aggregation for USR004 (Manager for DEOM-01 + KNUG-02 + GEVRA)
        agg_u4 = AuthorizationService.scoped_aggregate(
            db=self.db,
            model=ProductionAnnual,
            metric_column=ProductionAnnual.actual_production_mt,
            group_by_column=None,
            scope=self.scope4,
            agg_func="SUM"
        )
        total_u4 = agg_u4[0]["value"]
        self.assertAlmostEqual(total_u4, 328.67, places=2, msg="USR004 total must match DEOM-01 (23.69) + KNUG-02 (7.88) + GEVRA (297.10) = 328.67 MT.")

        # 3. Aggregation for USR005 (HQ Administrator, Enterprise ALL)
        agg_u5 = AuthorizationService.scoped_aggregate(
            db=self.db,
            model=ProductionAnnual,
            metric_column=ProductionAnnual.actual_production_mt,
            group_by_column=None,
            scope=self.scope5,
            agg_func="SUM"
        )
        total_u5 = agg_u5[0]["value"]
        all_sum = float(self.db.scalar(select(func.sum(ProductionAnnual.actual_production_mt))))
        self.assertAlmostEqual(total_u5, all_sum, places=2, msg=f"USR005 enterprise total ({total_u5}) must match full database sum ({all_sum} MT).")


if __name__ == "__main__":
    unittest.main()
