"""
GeoVault AI - Authorization & Security Test Runner
Executes comprehensive automated security tests for Phase 4 compliance.
"""

import os
import sys
import unittest

sys.path.insert(0, "/app")

from tests.test_authorization import TestAuthorizationSuite


def main():
    print("=" * 75)
    print("GeoVault AI — Phase 4 Security, Authorization & Scope Verification")
    print("=" * 75)
    print("[*] Target Specification: AGENTS.md (RBAC + ABAC Authorization Engine)")
    print("[*] Security Principle: AUTHORIZATION BEFORE RETRIEVAL")
    print("-" * 75)

    suite = unittest.TestLoader().loadTestsFromTestCase(TestAuthorizationSuite)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    print("\n" + "=" * 75)
    print("SUMMARY OF SECURITY TEST EXECUTION")
    print("=" * 75)
    print(f"Total Security Tests Run : {result.testsRun}")
    print(f"Passed Tests             : {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"Failures                 : {len(result.failures)}")
    print(f"Errors                   : {len(result.errors)}")

    if result.wasSuccessful():
        print("\n>>> ALL PHASE 4 AUTHORIZATION & SECURITY TESTS PASSED! <<<")
        print("=" * 75)
        sys.exit(0)
    else:
        print("\n[!] SOME TESTS FAILED! REVIEW OUTPUT ABOVE.")
        print("=" * 75)
        sys.exit(1)


if __name__ == "__main__":
    main()
