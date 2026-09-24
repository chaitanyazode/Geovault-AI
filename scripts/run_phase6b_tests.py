"""
GeoVault AI - Phase 6B Automated Professional Report Generation Test Runner
Executes comprehensive automated tests for:
- Pre-retrieval authorization enforcement (AUTHORIZATION BEFORE RETRIEVAL)
- Scoped operational data packaging (Production, Dispatch, Issues, Inspections)
- Headless matplotlib chart generation (Production Trend & Comparison PNGs)
- Word document (.docx) generation & structure verification
- PDF document (.pdf) generation & page formatting
- Exact deterministic numerical consistency with PostgreSQL
- Security denial: USR001 requesting KNUG-02/SSOP-03 raises 403 Forbidden
- Mine Manager multi-mine report: USR004 generates DEOM-01 + KNUG-02; denied on SSOP-03
- Conflict detection & human review notice on SSOP-03 FY2025
- Download authorization & path traversal security defense
- UnifiedAIOrchestrator REPORT route natural-language integration
"""

import sys
import unittest

sys.path.insert(0, "/app")

from tests.test_report_generation import TestPhase6BReportGenerationSuite


def main():
    print("=" * 80)
    print("GeoVault AI — Phase 6B Automated Professional Report Generation Verification")
    print("=" * 80)
    print("[*] Target Specification: AGENTS.md (Section 4.3 & Section 51)")
    print("[*] Core Rule: Deterministic Numbers + Grounded Qwen Executive Narrative")
    print("[*] Security Boundary: AUTHORIZATION BEFORE RETRIEVAL (Strict Pre-Retrieval Scoping)")
    print("[*] Storage Rule: /data/reports/ persistent volume (Coal Data/ strictly READ-ONLY)")
    print("-" * 80)

    suite = unittest.TestLoader().loadTestsFromTestCase(TestPhase6BReportGenerationSuite)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    print("\n" + "=" * 80)
    print("SUMMARY OF PHASE 6B TEST EXECUTION")
    print("=" * 80)
    print(f"Total Tests Run : {result.testsRun}")
    print(f"Passed Tests   : {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"Failures       : {len(result.failures)}")
    print(f"Errors         : {len(result.errors)}")

    if result.wasSuccessful():
        print("\n>>> ALL PHASE 6B AUTOMATED REPORT GENERATION TESTS PASSED! <<<")
        print("=" * 80)
        sys.exit(0)
    else:
        print("\n[!] SOME TESTS FAILED! REVIEW OUTPUT ABOVE.")
        print("=" * 80)
        sys.exit(1)


if __name__ == "__main__":
    main()
