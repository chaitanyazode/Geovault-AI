"""
GeoVault AI - Phase 6A Automated Topic Identification & Word Cloud Test Suite
Tests:
1. Scoped chunk retrieval with pre-retrieval SQL filtering (AUTHORIZATION BEFORE RETRIEVAL)
2. Deterministic TF-IDF keyword extraction & ranking with domain stopword filtering
3. K-Means topic clustering & grounded title/description synthesis
4. WordCloud PNG generation & persistent file storage in data/generated/wordclouds/
5. Mine-specific filtering (e.g., DEOM-01, KNUG-02) within authorized scope
6. Security denial: USR001 attempting to access KNUG-02 or SSOP-03 raises 403 Forbidden
7. Scope isolation: USR001 never receives topics or chunks from unauthorized mines
8. Multi-mine manager analysis: USR004 receives aggregated topics across DEOM-01 and KNUG-02
9. UnifiedAIOrchestrator TOPIC route integration for natural-language topic queries
10. In-memory scope-aware caching performance and cache hit verification
"""

import os
import unittest
from sqlalchemy.orm import Session
from fastapi import HTTPException

from app.core.database import SessionLocal
from app.security.service import AuthorizationService
from app.security.context import UserContext, AuthorizedScope
from app.services.topic_service import TopicAnalysisService
from app.ai.orchestrator import UnifiedAIOrchestrator


class TestPhase6ATopicWordCloudSuite(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.db: Session = SessionLocal()

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
    # 1. Pre-Retrieval SQL Authorization Scoping
    # --------------------------------------------------------------------------
    def test_01_scoped_chunk_retrieval(self):
        """Verifies that chunks are filtered strictly at the SQL level before retrieval."""
        chunks = TopicAnalysisService.get_scoped_chunks(self.db, self.scope1)
        self.assertGreater(len(chunks), 0, "USR001 must have authorized document chunks")

        for c in chunks:
            # USR001 has DEOM-01, GEVRA or national (None)
            self.assertIn(
                c.mine_code,
                ["DEOM-01", "GEVRA", None],
                f"USR001 received chunk from unauthorized mine {c.mine_code}",
            )
            # USR001 clearance is INTERNAL, must not see RESTRICTED or CONFIDENTIAL
            self.assertIn(
                c.classification,
                ["PUBLIC", "INTERNAL"],
                f"USR001 received chunk with unauthorized classification {c.classification}",
            )

    # --------------------------------------------------------------------------
    # 2. Deterministic TF-IDF Keyword Extraction
    # --------------------------------------------------------------------------
    def test_02_tfidf_keyword_extraction(self):
        """Verifies deterministic TF-IDF extraction, ranking, and domain stopword removal."""
        chunks = TopicAnalysisService.get_scoped_chunks(self.db, self.scope1)
        keywords = TopicAnalysisService.extract_keywords_tfidf(chunks, top_n=15)

        self.assertGreater(len(keywords), 0, "Keywords must be extracted from authorized chunks")
        self.assertLessEqual(len(keywords), 15)

        # Check keyword structure
        top_kw = keywords[0]
        self.assertIsNotNone(top_kw.keyword)
        self.assertGreater(top_kw.frequency, 0)
        self.assertGreater(top_kw.tfidf_score, 0.0)
        self.assertGreater(top_kw.document_frequency, 0)

        # Ensure common stopwords are stripped
        extracted_words = {k.keyword.lower() for k in keywords}
        for sw in ["the", "and", "is", "in", "at", "which", "report", "page"]:
            self.assertNotIn(sw, extracted_words, f"Stopword '{sw}' was not filtered out")

    # --------------------------------------------------------------------------
    # 3. K-Means Topic Clustering
    # --------------------------------------------------------------------------
    def test_03_topic_clustering(self):
        """Verifies K-Means clustering creates grounded topics with titles and key quotes."""
        chunks = TopicAnalysisService.get_scoped_chunks(self.db, self.scope1)
        clusters = TopicAnalysisService.cluster_topics(chunks, num_clusters=3)

        self.assertGreater(len(clusters), 0, "Clusters must be generated")
        self.assertLessEqual(len(clusters), 3)

        for cl in clusters:
            self.assertIsNotNone(cl.title)
            self.assertGreater(len(cl.keywords), 0)
            self.assertGreater(cl.chunk_count, 0)
            self.assertGreater(len(cl.representative_quotes), 0)
            self.assertIn("cluster", cl.description.lower())


    # --------------------------------------------------------------------------
    # 4. WordCloud Image Generation & Storage
    # --------------------------------------------------------------------------
    def test_04_wordcloud_image_generation(self):
        """Verifies WordCloud PNG image is generated and saved in data/generated/wordclouds/."""
        chunks = TopicAnalysisService.get_scoped_chunks(self.db, self.scope1)
        keywords = TopicAnalysisService.extract_keywords_tfidf(chunks, top_n=20)
        wc_res = TopicAnalysisService.generate_wordcloud_image(keywords, "USR001_DEOM-01")

        self.assertIsNotNone(wc_res.image_url)
        self.assertTrue(wc_res.image_url.startswith("/api/v1/topics/wordcloud/image/"))
        self.assertTrue(os.path.exists(wc_res.image_path), f"File {wc_res.image_path} must exist on disk")
        self.assertTrue(wc_res.image_path.endswith(".png"))
        self.assertGreater(os.path.getsize(wc_res.image_path), 1000, "PNG image size must be non-trivial")

    # --------------------------------------------------------------------------
    # 5. Mine-Specific Filtering Within Scope
    # --------------------------------------------------------------------------
    def test_05_mine_filtering_within_scope(self):
        """Verifies that scoping down to DEOM-01 succeeds for USR001."""
        response = TopicAnalysisService.analyze_topics(
            self.db, self.user1, mine_code="DEOM-01", num_topics=3, top_keywords=15
        )
        self.assertEqual(response.scope_applied["mine_filter"], "DEOM-01")
        self.assertGreater(response.total_chunks_analyzed, 0)
        self.assertGreater(len(response.keywords), 0)
        self.assertGreater(len(response.topics), 0)
        self.assertIsNotNone(response.wordcloud.image_url)

    # --------------------------------------------------------------------------
    # 6. Security Denial: Access Denied for Unauthorized Mine
    # --------------------------------------------------------------------------
    def test_06_unauthorized_mine_denial(self):
        """Verifies USR001 attempting to request KNUG-02 or SSOP-03 raises 403 Forbidden."""
        with self.assertRaises(HTTPException) as ctx_knug:
            TopicAnalysisService.analyze_topics(self.db, self.user1, mine_code="KNUG-02")
        self.assertEqual(ctx_knug.exception.status_code, 403)
        self.assertIn("Access Denied", ctx_knug.exception.detail)

        with self.assertRaises(HTTPException) as ctx_ssop:
            TopicAnalysisService.analyze_topics(self.db, self.user1, mine_code="SSOP-03")
        self.assertEqual(ctx_ssop.exception.status_code, 403)
        self.assertIn("Access Denied", ctx_ssop.exception.detail)

    # --------------------------------------------------------------------------
    # 7. Scope Isolation: Zero Data Leakage
    # --------------------------------------------------------------------------
    def test_07_scope_isolation_data_leakage(self):
        """Verifies USR001 corpus contains zero chunks/documents from KNUG-02 or SSOP-03."""
        chunks = TopicAnalysisService.get_scoped_chunks(self.db, self.scope1)
        unauthorized_mines = {c.mine_code for c in chunks if c.mine_code in ["KNUG-02", "SSOP-03"]}
        self.assertEqual(
            len(unauthorized_mines),
            0,
            f"Data leakage detected! USR001 chunks include unauthorized mines: {unauthorized_mines}",
        )

    # --------------------------------------------------------------------------
    # 8. Mine Manager Multi-Mine Scoping
    # --------------------------------------------------------------------------
    def test_08_mine_manager_multi_mine(self):
        """Verifies USR004 (Mine Manager) can analyze topics across both DEOM-01 and KNUG-02."""
        # 1. Unfiltered request (aggregates both permitted mines)
        response_all = TopicAnalysisService.analyze_topics(
            self.db, self.user4, num_topics=3, top_keywords=15
        )
        self.assertIn("DEOM-01", response_all.scope_applied["user_mines"])
        self.assertIn("KNUG-02", response_all.scope_applied["user_mines"])
        self.assertGreater(response_all.total_chunks_analyzed, 0)

        # 2. Specific filter to KNUG-02 (permitted for USR004)
        response_knug = TopicAnalysisService.analyze_topics(
            self.db, self.user4, mine_code="KNUG-02", num_topics=3, top_keywords=15
        )
        self.assertEqual(response_knug.scope_applied["mine_filter"], "KNUG-02")
        self.assertGreater(response_knug.total_chunks_analyzed, 0)

        # 3. But USR004 CANNOT access SSOP-03
        with self.assertRaises(HTTPException) as ctx_ssop:
            TopicAnalysisService.analyze_topics(self.db, self.user4, mine_code="SSOP-03")
        self.assertEqual(ctx_ssop.exception.status_code, 403)

    # --------------------------------------------------------------------------
    # 9. UnifiedAIOrchestrator TOPIC Route Execution
    # --------------------------------------------------------------------------
    def test_09_orchestrator_topic_route(self):
        """Verifies natural-language topic query routes to TOPIC and produces grounded response."""
        res = UnifiedAIOrchestrator.execute_query(
            self.db,
            "USR001",
            "What are the major topics and recurring terminology in mine reports?",
        )
        self.assertEqual(res.route_used, "TOPIC")
        self.assertGreater(len(res.grounded_explanation), 0)
        self.assertGreater(len(res.evidence), 0)
        self.assertIsNotNone(res.metadata.get("wordcloud_url"))



    # --------------------------------------------------------------------------
    # 10. Scope-Aware In-Memory Caching
    # --------------------------------------------------------------------------
    def test_10_caching_hit(self):
        """Verifies that consecutive calls within TTL return cached analysis."""
        TopicAnalysisService.clear_cache()

        # First call (populates cache)
        res1 = TopicAnalysisService.analyze_topics(
            self.db, self.user1, mine_code="DEOM-01", num_topics=3, top_keywords=15
        )

        # Second call (must be hit from cache)
        res2 = TopicAnalysisService.analyze_topics(
            self.db, self.user1, mine_code="DEOM-01", num_topics=3, top_keywords=15
        )

        self.assertEqual(res1.wordcloud.image_url, res2.wordcloud.image_url)
        self.assertEqual(len(res1.topics), len(res2.topics))
        self.assertEqual(len(res1.keywords), len(res2.keywords))


if __name__ == "__main__":
    unittest.main()
