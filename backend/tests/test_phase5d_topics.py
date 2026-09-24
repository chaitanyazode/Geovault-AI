"""
GeoVault AI - Phase 5D Topics & Word Cloud UX + Authorization Test Suite
Tests:
1. Canonical 5-mine scoped chunk retrieval (GV001-GV005)
2. TF-IDF keyword extraction & frequency ranking
3. K-Means clustering and canonical mine naming in topics
4. WordCloud image generation
5. Authorized mine filtering for single-mine scoped user (USR001)
6. Strict HTTP 403 pre-retrieval denial for unauthorized mine (USR001 querying GV004)
7. Scope isolation: zero unauthorized mine data leakage
8. Multi-mine analysis for Mine Manager (USR004)
9. Reporting year filtering (FY2024)
10. Empty state handling and graceful zero-chunk response
"""

import unittest
from sqlalchemy.orm import Session
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.main import app
from app.core.database import SessionLocal
from app.security.service import AuthorizationService
from app.security.context import UserContext, AuthorizedScope
from app.services.topic_service import TopicAnalysisService
from app.schemas.topics import TopicAnalysisRequest, TopicAnalysisResponse


class TestPhase5DTopicsSuite(unittest.TestCase):
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
    # 1. Scoped Chunk Retrieval with Canonical Alias Resolution
    # --------------------------------------------------------------------------
    def test_01_canonical_mines_scoped_chunk_retrieval(self):
        """Verifies chunks are retrieved using canonical codes and alias expansion."""
        chunks_gv = TopicAnalysisService.get_scoped_chunks(self.db, self.scope1, mine_code="GV001")
        self.assertGreater(len(chunks_gv), 0)

        chunks_name = TopicAnalysisService.get_scoped_chunks(self.db, self.scope1, mine_code="GEVRA")
        self.assertEqual(len(chunks_gv), len(chunks_name))

    # --------------------------------------------------------------------------
    # 2. TF-IDF Keyword Extraction & Ranking
    # --------------------------------------------------------------------------
    def test_02_tfidf_keyword_extraction_canonical(self):
        """Validates TF-IDF keyword extraction returns ranked domain keywords."""
        chunks = TopicAnalysisService.get_scoped_chunks(self.db, self.scope1, mine_code="GV001")
        keywords = TopicAnalysisService.extract_keywords_tfidf(chunks, max_keywords=20)

        self.assertGreater(len(keywords), 0)
        self.assertLessEqual(len(keywords), 20)

        # Verify attributes exist and are non-negative
        for k in keywords:
            self.assertIsNotNone(k.keyword)
            self.assertGreaterEqual(k.frequency, 1)
            self.assertGreaterEqual(k.tfidf_score, 0.0)
            self.assertGreaterEqual(k.document_count, 1)

    # --------------------------------------------------------------------------
    # 3. K-Means Topic Clustering & Canonical Mine Naming
    # --------------------------------------------------------------------------
    def test_03_topic_clustering_canonical_names(self):
        """Verifies topic clusters are formed and contain canonical mine names."""
        chunks = TopicAnalysisService.get_scoped_chunks(self.db, self.scope5)
        clusters = TopicAnalysisService.cluster_topics(chunks, num_clusters=4)

        self.assertGreater(len(clusters), 0)
        for cluster in clusters:
            self.assertIsNotNone(cluster.title)
            self.assertGreater(len(cluster.top_keywords), 0)
            self.assertGreaterEqual(cluster.document_chunk_count, 1)

            # Ensure zero legacy mine names in mines_covered
            for m in cluster.mines_covered:
                self.assertNotIn("DEOM-01", m)
                self.assertNotIn("KNUG-02", m)
                self.assertNotIn("SSOP-03", m)

    # --------------------------------------------------------------------------
    # 4. WordCloud Generation
    # --------------------------------------------------------------------------
    def test_04_wordcloud_image_generation_provenance(self):
        """Tests word cloud image generation produces valid file and URL."""
        chunks = TopicAnalysisService.get_scoped_chunks(self.db, self.scope1, mine_code="GV001")
        keywords = TopicAnalysisService.extract_keywords_tfidf(chunks, max_keywords=15)
        wc_res = TopicAnalysisService.generate_wordcloud_image(keywords, "test_phase5d")

        self.assertIsNotNone(wc_res.image_url)
        self.assertIsNotNone(wc_res.image_path)
        self.assertIn("/api/v1/topics/wordcloud/image/", wc_res.image_url)

    # --------------------------------------------------------------------------
    # 5. Authorized Mine Filtering for Single-Mine User (USR001)
    # --------------------------------------------------------------------------
    def test_05_authorized_mine_filtering_usr001(self):
        """Verifies USR001 can analyze topics for permitted mine GV001."""
        req = TopicAnalysisRequest(mine_code="GV001", generate_wordcloud=False)
        res = TopicAnalysisService.analyze_topics(self.db, self.scope1, req=req)

        self.assertIsInstance(res, TopicAnalysisResponse)
        self.assertGreater(res.total_chunks_analyzed, 0)
        self.assertGreater(len(res.topics), 0)

    # --------------------------------------------------------------------------
    # 6. Strict HTTP 403 Denial for Unauthorized Mine
    # --------------------------------------------------------------------------
    def test_06_unauthorized_mine_denial_403(self):
        """Verifies USR001 querying NIGAHI (GV004) is denied via HTTP 403 before retrieval."""
        req = TopicAnalysisRequest(mine_code="GV004", generate_wordcloud=False)
        with self.assertRaises(HTTPException) as ctx:
            TopicAnalysisService.analyze_topics(self.db, self.scope1, req=req)

        self.assertEqual(ctx.exception.status_code, 403)
        self.assertIn("not authorized", ctx.exception.detail.lower())

    # --------------------------------------------------------------------------
    # 7. Scope Isolation: Zero Data Leakage Across Mine Scopes
    # --------------------------------------------------------------------------
    def test_07_scope_isolation_data_leakage(self):
        """Ensures USR001 topic analysis contains zero chunks or excerpts from other mines."""
        res = TopicAnalysisService.analyze_topics(self.db, self.scope1, generate_wordcloud=False)

        # Chunks analyzed must belong strictly to GEVRA
        for t in res.topics:
            for m in t.mines_covered:
                self.assertIn(m, ["GEVRA", "GV001", "Enterprise"])

    # --------------------------------------------------------------------------
    # 8. Multi-Mine Analysis for Mine Manager (USR004)
    # --------------------------------------------------------------------------
    def test_08_mine_manager_multi_mine_analysis(self):
        """Validates USR004 can access GEVRA and KUSMUNDA, but is denied for DUDHICHUA (GV005)."""
        # Permitted: GEVRA
        res_gevra = TopicAnalysisService.analyze_topics(
            self.db, self.scope4, req=TopicAnalysisRequest(mine_code="GV001", generate_wordcloud=False)
        )
        self.assertGreater(res_gevra.total_chunks_analyzed, 0)

        # Denied: GV005 (DUDHICHUA)
        with self.assertRaises(HTTPException) as ctx:
            TopicAnalysisService.analyze_topics(
                self.db, self.scope4, req=TopicAnalysisRequest(mine_code="GV005", generate_wordcloud=False)
            )
        self.assertEqual(ctx.exception.status_code, 403)

    # --------------------------------------------------------------------------
    # 9. Reporting Year Filtering
    # --------------------------------------------------------------------------
    def test_09_year_filtering(self):
        """Tests that passing year filter constrains chunk retrieval."""
        chunks_all = TopicAnalysisService.get_scoped_chunks(self.db, self.scope5)
        chunks_2024 = TopicAnalysisService.get_scoped_chunks(self.db, self.scope5, year=2024)

        # Year-filtered count must be non-zero and less than or equal to total chunks
        self.assertGreater(len(chunks_2024), 0)
        self.assertLessEqual(len(chunks_2024), len(chunks_all))

    # --------------------------------------------------------------------------
    # 10. Empty State Handling
    # --------------------------------------------------------------------------
    def test_10_empty_state_handling(self):
        """Verifies that non-existent year query returns clean empty topic response without crashing."""
        chunks = TopicAnalysisService.get_scoped_chunks(self.db, self.scope5, year=1950)
        self.assertEqual(len(chunks), 0)

        res = TopicAnalysisService.analyze_topics(
            self.db, self.scope5, req=TopicAnalysisRequest(year=1950, generate_wordcloud=False)
        )
        self.assertEqual(res.total_chunks_analyzed, 0)
        self.assertEqual(len(res.keywords), 0)
        self.assertEqual(len(res.topics), 0)


if __name__ == "__main__":
    unittest.main()
