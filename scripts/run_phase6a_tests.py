"""
GeoVault AI - Phase 6A Automated Topic Identification & Word Cloud Test Runner
Executes comprehensive automated tests for:
- Pre-retrieval SQL authorization scoping (AUTHORIZATION BEFORE RETRIEVAL)
- Deterministic TF-IDF keyword extraction with domain stopword filtering
- K-Means topic clustering & grounded description synthesis
- WordCloud PNG generation & persistent file storage in data/generated/wordclouds/
- Mine-specific filtering (DEOM-01, KNUG-02) within authorized scope
- Security denial: USR001 attempting to query KNUG-02/SSOP-03 raises 403 Forbidden
- Scope isolation: USR001 corpus never leaks unauthorized mine data
- Multi-mine manager analysis: USR004 receives aggregated topics across permitted mines
- UnifiedAIOrchestrator TOPIC route integration for natural-language topic queries
- Scope-aware in-memory caching performance and cache hit verification
"""

import sys
import unittest

sys.path.insert(0, "/app")

from tests.test_topics_wordcloud import TestPhase6ATopicWordCloudSuite


def main():
    print("=" * 80)
    print("GeoVault AI — Phase 6A Automated Topic Identification & Word Cloud Verification")
    print("=" * 80)
    print("[*] Target Specification: AGENTS.md (Section 4.2 & Section 50)")
    print("[*] Core Rule: Deterministic NLP (TF-IDF + K-Means) + Grounded Explanations")
    print("[*] Security Boundary: AUTHORIZATION BEFORE RETRIEVAL (Pre-retrieval SQL Scoping)")
    print("[*] Storage Rule: Derived outputs only in data/generated/wordclouds/ (Coal Data/ READ-ONLY)")
    print("-" * 80)

    suite = unittest.TestLoader().loadTestsFromTestCase(TestPhase6ATopicWordCloudSuite)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    print("\n" + "=" * 80)
    print("SUMMARY OF PHASE 6A TEST EXECUTION")
    print("=" * 80)
    print(f"Total Tests Run : {result.testsRun}")
    print(f"Passed Tests   : {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"Failures       : {len(result.failures)}")
    print(f"Errors         : {len(result.errors)}")

    if result.wasSuccessful():
        print("\n>>> ALL PHASE 6A TOPIC IDENTIFICATION & WORD CLOUD TESTS PASSED! <<<")
        print("=" * 80)
        sys.exit(0)
    else:
        print("\n[!] SOME TESTS FAILED! REVIEW OUTPUT ABOVE.")
        print("=" * 80)
        sys.exit(1)


if __name__ == "__main__":
    main()
