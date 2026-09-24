"""
GeoVault AI - Phase 5C Production AI Orchestrator Test Runner
Executes comprehensive automated tests for:
- Unified AI Orchestrator lifecycle across all routes
- Prompt-Injection Defense & XML-Fenced Data Boundaries
- Adversarial wording tricks and unauthorized mine access denials
- Output sanitation (<think> stripping) and latency metrics
- Scope-isolated conflict surfacing
"""

import sys
import unittest

sys.path.insert(0, "/app")

from tests.test_phase5c_orchestrator import TestPhase5COrchestratorSuite


def main():
    print("=" * 80)
    print("GeoVault AI — Phase 5C Production Grounded AI Orchestrator Verification")
    print("=" * 80)
    print("[*] Target Specification: AGENTS.md (Unified AI Orchestrator & Defense)")
    print("[*] Security Principle: AUTHORIZATION BEFORE RETRIEVAL")
    print("[*] Defense Boundary: XML-Fenced Data + Prompt-Injection Immunization")
    print("-" * 80)

    suite = unittest.TestLoader().loadTestsFromTestCase(TestPhase5COrchestratorSuite)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    print("\n" + "=" * 80)
    print("SUMMARY OF PHASE 5C TEST EXECUTION")
    print("=" * 80)
    print(f"Total Tests Run : {result.testsRun}")
    print(f"Passed Tests   : {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"Failures       : {len(result.failures)}")
    print(f"Errors         : {len(result.errors)}")

    if result.wasSuccessful():
        print("\n>>> ALL PHASE 5C PRODUCTION ORCHESTRATOR TESTS PASSED! <<<")
        print("=" * 80)
        sys.exit(0)
    else:
        print("\n[!] SOME TESTS FAILED! REVIEW OUTPUT ABOVE.")
        print("=" * 80)
        sys.exit(1)


if __name__ == "__main__":
    main()
