"""
GeoVault AI - Query Intelligence & Deterministic Analytics Test Runner
Executes comprehensive tests for Phase 5A:
- Deterministic operational queries (production, target vs actual, dispatch, quality, geology, issues)
- Analytics engine calculations (YoY growth, target achievement, trend detection, multi-mine comparisons)
- Evidence engine tracebacks (document/table/chunk, record IDs, formatted citations)
- Validation engine integrity (math checks, data gaps, conflict surfacing)
- Strict compliance with AUTHORIZATION BEFORE RETRIEVAL
"""

import os
import sys
import unittest

sys.path.insert(0, "/app")

from tests.test_query_intelligence import TestQueryIntelligenceSuite


def main():
    print("=" * 80)
    print("GeoVault AI — Phase 5A Query Intelligence & Analytics Verification")
    print("=" * 80)
    print("[*] Target Specification: AGENTS.md (Deterministic SQL, Analytics, Evidence, Validation)")
    print("[*] Core Rule: Python calculates. LLM explains.")
    print("[*] Security Principle: AUTHORIZATION BEFORE RETRIEVAL")
    print("-" * 80)

    suite = unittest.TestLoader().loadTestsFromTestCase(TestQueryIntelligenceSuite)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    print("\n" + "=" * 80)
    print("SUMMARY OF QUERY INTELLIGENCE TEST EXECUTION")
    print("=" * 80)
    print(f"Total Tests Run : {result.testsRun}")
    print(f"Passed Tests   : {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"Failures       : {len(result.failures)}")
    print(f"Errors         : {len(result.errors)}")

    if result.wasSuccessful():
        print("\n>>> ALL PHASE 5A QUERY INTELLIGENCE & ANALYTICS TESTS PASSED! <<<")
        print("=" * 80)
        sys.exit(0)
    else:
        print("\n[!] SOME TESTS FAILED! REVIEW OUTPUT ABOVE.")
        print("=" * 80)
        sys.exit(1)


if __name__ == "__main__":
    main()
