"""
GeoVault AI - Phase 5B Natural Query, RAG & Grounded Qwen Verification Runner
Executes comprehensive automated tests for:
- Deterministic Query Routing (SQL, ANALYTICS, RAG, HYBRID, TOPIC, REPORT)
- LlamaIndex ScopedVectorRetriever authorization pre-filtering
- Grounded Qwen3-8B local reasoning & reasoning_content handling
- End-to-end natural language queries
- Strict security denials and anti-leakage boundaries
"""

import sys
import unittest

sys.path.insert(0, "/app")

from tests.test_natural_query_rag import TestNaturalQueryRAGSuite


def main():
    print("=" * 80)
    print("GeoVault AI — Phase 5B Natural Query, RAG & Grounded Qwen Verification")
    print("=" * 80)
    print("[*] Target Specification: AGENTS.md (Permission-Aware RAG + Query Router + Qwen)")
    print("[*] Security Principle: AUTHORIZATION BEFORE RETRIEVAL")
    print("[*] Grounding Rule: Python calculates. LLM explains.")
    print("-" * 80)

    suite = unittest.TestLoader().loadTestsFromTestCase(TestNaturalQueryRAGSuite)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    print("\n" + "=" * 80)
    print("SUMMARY OF PHASE 5B TEST EXECUTION")
    print("=" * 80)
    print(f"Total Tests Run : {result.testsRun}")
    print(f"Passed Tests   : {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"Failures       : {len(result.failures)}")
    print(f"Errors         : {len(result.errors)}")

    if result.wasSuccessful():
        print("\n>>> ALL PHASE 5B NATURAL QUERY, RAG & REASONING TESTS PASSED! <<<")
        print("=" * 80)
        sys.exit(0)
    else:
        print("\n[!] SOME TESTS FAILED! REVIEW OUTPUT ABOVE.")
        print("=" * 80)
        sys.exit(1)


if __name__ == "__main__":
    main()
