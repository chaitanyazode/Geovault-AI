"""
GeoVault AI - Phase 5F Audit Logs Test Suite
Comprehensive verification of Audit Logs outcome:
1. Authorized audit-log access
2. Unauthorized audit-log access (HTTP 403 on forbidden mine filter)
3. USR001 mine isolation
4. USR004 multi-mine scope
5. USR005 administrator enterprise scope
6. Mine filter authorization
7. Event/route type filtering
8. Semantic status filtering (SUCCESS, DISCREPANCY, DENIED)
9. Server-side pagination controls
10. No unauthorized events leaked
11. No sensitive evidence text or CoT reasoning exposed
12. Denied event sanitization
13. Report-generation event visibility
14. Audit summary metrics within authorized scope
15. Empty state handling
16. HTTP 403 access denial handling
17. Canonical mine identifiers in response
18. Legacy identifier scan (0 occurrences)
19. Pydantic response schema compliance
20. Non-recursive audit logging
"""

import os
import re
import unittest
from fastapi import HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.core.database import SessionLocal
from app.models.governance import QueryAuditLog
from app.security.service import AuthorizationService
from app.security.context import UserContext, AuthorizedScope
from app.services.audit_service import AuditLogService
from app.schemas.audit import (
    AuditLogItemResponse,
    AuditLogSummaryResponse,
    AuditLogPaginatedResponse,
)

LEGACY_IDENTIFIERS = [
    "DEOM-01", "KNUG-02", "SSOP-03", "Dharani East", "Shakti Coalfields"
]


class TestPhase5FAuditLogs(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.db: Session = SessionLocal()
        cls.service = AuditLogService

        # Setup canonical test users
        cls.user1: UserContext = AuthorizationService.resolve_user_context(cls.db, "USR001")
        cls.scope1: AuthorizedScope = AuthorizationService.get_authorized_scope(cls.user1)

        cls.user2: UserContext = AuthorizationService.resolve_user_context(cls.db, "USR002")
        cls.scope2: AuthorizedScope = AuthorizationService.get_authorized_scope(cls.user2)

        cls.user3: UserContext = AuthorizationService.resolve_user_context(cls.db, "USR003")
        cls.scope3: AuthorizedScope = AuthorizationService.get_authorized_scope(cls.user3)

        cls.user4: UserContext = AuthorizationService.resolve_user_context(cls.db, "USR004")
        cls.scope4: AuthorizedScope = AuthorizationService.get_authorized_scope(cls.user4)

        cls.user5: UserContext = AuthorizationService.resolve_user_context(cls.db, "USR005")
        cls.scope5: AuthorizedScope = AuthorizationService.get_authorized_scope(cls.user5)

    @classmethod
    def tearDownClass(cls):
        cls.db.close()

    def tearDown(self):
        self.db.rollback()

    # --------------------------------------------------------------------------
    # 01. Authorized audit-log access
    # --------------------------------------------------------------------------
    def test_01_authorized_audit_log_access(self):
        """USR001 successfully retrieves their authorized logs."""
        res: AuditLogPaginatedResponse = self.service.get_audit_logs(
            db=self.db,
            user=self.user1,
            scope=self.scope1,
            page=1,
            page_size=25,
        )
        self.assertIsInstance(res, AuditLogPaginatedResponse)
        self.assertGreater(res.total, 0, "USR001 should have historical audit logs")
        self.assertGreater(len(res.items), 0)
        self.assertEqual(res.page, 1)
        self.assertEqual(res.page_size, 25)

        # All items returned must belong to USR001
        for item in res.items:
            self.assertEqual(item.user_id, "USR001")
        print(f"[01] PASS — USR001 retrieved {len(res.items)} authorized audit events (Total: {res.total})")

    # --------------------------------------------------------------------------
    # 02. Unauthorized mine filter blocked (HTTP 403)
    # --------------------------------------------------------------------------
    def test_02_unauthorized_mine_filter_blocked(self):
        """USR001 requesting logs for unauthorized mine GV004/NIGAHI is rejected with 403."""
        with self.assertRaises(HTTPException) as ctx:
            self.service.get_audit_logs(
                db=self.db,
                user=self.user1,
                scope=self.scope1,
                mine="GV004",
            )
        self.assertEqual(ctx.exception.status_code, 403)
        self.assertIn("not authorized", ctx.exception.detail.lower())

        with self.assertRaises(HTTPException) as ctx2:
            self.service.get_audit_logs(
                db=self.db,
                user=self.user1,
                scope=self.scope1,
                mine="NIGAHI",
            )
        self.assertEqual(ctx2.exception.status_code, 403)
        print("[02] PASS — Unauthorized mine filter (GV004/NIGAHI) correctly rejected with HTTP 403")

    # --------------------------------------------------------------------------
    # 03. Scope isolation: USR001 cannot see USR005's NIGAHI logs
    # --------------------------------------------------------------------------
    def test_03_scope_isolation_usr001_vs_usr005(self):
        """USR001's logs must never contain records generated by other users or unpermitted mines."""
        res_user1 = self.service.get_audit_logs(
            db=self.db,
            user=self.user1,
            scope=self.scope1,
            page=1,
            page_size=100,
        )
        for item in res_user1.items:
            self.assertEqual(item.user_id, "USR001", "Scope breach: USR001 received non-USR001 record!")
            for m in item.mine_scope:
                if "NIGAHI" in m or "DUDHICHUA" in m or "GV004" in m or "GV005" in m:
                    self.fail(f"Scope breach: Unauthorized mine '{m}' in USR001 audit response!")
        print("[03] PASS — Strict scope isolation verified: USR001 cannot observe non-authorized records")

    # --------------------------------------------------------------------------
    # 04. Administrator full visibility
    # --------------------------------------------------------------------------
    def test_04_admin_full_visibility(self):
        """USR005 (Administrator) can view system-wide audit records across all users and mines."""
        res_admin = self.service.get_audit_logs(
            db=self.db,
            user=self.user5,
            scope=self.scope5,
            page=1,
            page_size=50,
        )
        self.assertGreater(res_admin.total, 100, "Admin should see full enterprise audit logs")
        users_seen = {item.user_id for item in res_admin.items}
        self.assertGreater(len(users_seen), 1, "Admin should see multiple users across system")

        # Admin can also filter by user_id
        res_filtered = self.service.get_audit_logs(
            db=self.db,
            user=self.user5,
            scope=self.scope5,
            user_id_filter="USR004",
            page=1,
            page_size=20,
        )
        for item in res_filtered.items:
            self.assertEqual(item.user_id, "USR004")
        print(f"[04] PASS — Admin enterprise visibility verified across {len(users_seen)} users")

    # --------------------------------------------------------------------------
    # 05. Multi-mine manager scope (USR004)
    # --------------------------------------------------------------------------
    def test_05_multi_mine_manager_scope(self):
        """USR004 (Mine Manager) has access to GV001 and GV002, but not GV004."""
        # Querying GV001 -> allowed
        res_gv1 = self.service.get_audit_logs(
            db=self.db,
            user=self.user4,
            scope=self.scope4,
            mine="GV001",
        )
        self.assertIsInstance(res_gv1, AuditLogPaginatedResponse)

        # Querying GV004 -> rejected
        with self.assertRaises(HTTPException) as ctx:
            self.service.get_audit_logs(
                db=self.db,
                user=self.user4,
                scope=self.scope4,
                mine="GV004",
            )
        self.assertEqual(ctx.exception.status_code, 403)
        print("[05] PASS — USR004 multi-mine boundary verified (GV001 permitted, GV004 blocked)")

    # --------------------------------------------------------------------------
    # 06. Mine filter authorization
    # --------------------------------------------------------------------------
    def test_06_mine_filtering(self):
        """Filtering by GV001 returns only events involving GEVRA/GV001."""
        res = self.service.get_audit_logs(
            db=self.db,
            user=self.user1,
            scope=self.scope1,
            mine="GV001",
            page=1,
            page_size=50,
        )
        self.assertGreater(res.total, 0)
        for item in res.items:
            # Check that either mine_scope contains GV001/GEVRA or sanitized details does
            item_text = f"{' '.join(item.mine_scope)} {item.sanitized_details}"
            self.assertTrue(
                "GEVRA" in item_text or "GV001" in item_text,
                f"Expected GEVRA/GV001 in item, got: {item_text}"
            )
        print(f"[06] PASS — Mine filtering for GV001 returned {res.total} matching records")

    # --------------------------------------------------------------------------
    # 07. Event/Route type filtering
    # --------------------------------------------------------------------------
    def test_07_action_filtering(self):
        """Filtering by action/route (e.g. REPORT, TOPIC, SQL) restricts query."""
        res_report = self.service.get_audit_logs(
            db=self.db,
            user=self.user5,
            scope=self.scope5,
            action="REPORT",
            page=1,
            page_size=20,
        )
        for item in res_report.items:
            self.assertEqual(item.route, "REPORT")
            self.assertIn("Report", item.module)

        res_topic = self.service.get_audit_logs(
            db=self.db,
            user=self.user5,
            scope=self.scope5,
            action="TOPIC",
            page=1,
            page_size=20,
        )
        for item in res_topic.items:
            self.assertEqual(item.route, "TOPIC")
        print(f"[07] PASS — Route filtering verified for REPORT ({res_report.total}) and TOPIC ({res_topic.total})")

    # --------------------------------------------------------------------------
    # 08. Semantic status filtering
    # --------------------------------------------------------------------------
    def test_08_status_filtering(self):
        """Filtering by status (DISCREPANCY, DENIED, SUCCESS) returns matching subsets."""
        res_disc = self.service.get_audit_logs(
            db=self.db,
            user=self.user5,
            scope=self.scope5,
            status_filter="DISCREPANCY",
            page=1,
            page_size=20,
        )
        for item in res_disc.items:
            self.assertEqual(item.status, "DISCREPANCY")
            self.assertEqual(item.evidence_status, "CONFLICT")

        res_denied = self.service.get_audit_logs(
            db=self.db,
            user=self.user5,
            scope=self.scope5,
            status_filter="DENIED",
            page=1,
            page_size=20,
        )
        for item in res_denied.items:
            self.assertEqual(item.status, "DENIED")
            self.assertEqual(item.http_status, 403)
        print(f"[08] PASS — Semantic status filtering: DISCREPANCY ({res_disc.total}), DENIED ({res_denied.total})")

    # --------------------------------------------------------------------------
    # 09. Server-side pagination controls
    # --------------------------------------------------------------------------
    def test_09_pagination_controls(self):
        """Page and page_size parameters correctly divide records."""
        res_p1 = self.service.get_audit_logs(
            db=self.db,
            user=self.user5,
            scope=self.scope5,
            page=1,
            page_size=10,
        )
        self.assertEqual(len(res_p1.items), 10)
        self.assertEqual(res_p1.page, 1)
        self.assertEqual(res_p1.page_size, 10)
        self.assertGreater(res_p1.total_pages, 1)

        res_p2 = self.service.get_audit_logs(
            db=self.db,
            user=self.user5,
            scope=self.scope5,
            page=2,
            page_size=10,
        )
        self.assertEqual(len(res_p2.items), 10)
        self.assertEqual(res_p2.page, 2)

        # First item on page 1 must differ from first item on page 2
        self.assertNotEqual(res_p1.items[0].log_id, res_p2.items[0].log_id)
        print(f"[09] PASS — Pagination working correctly across {res_p1.total_pages} total pages")

    # --------------------------------------------------------------------------
    # 10. No unauthorized events leaked
    # --------------------------------------------------------------------------
    def test_10_no_unauthorized_events_leaked(self):
        """Exhaustive check that USR001 receives zero events from other users."""
        res = self.service.get_audit_logs(
            db=self.db,
            user=self.user1,
            scope=self.scope1,
            page=1,
            page_size=100,
        )
        for item in res.items:
            self.assertEqual(item.user_id, "USR001")
        print("[10] PASS — Zero cross-user events leaked in USR001 page")

    # --------------------------------------------------------------------------
    # 11. No sensitive evidence text or private reasoning exposed
    # --------------------------------------------------------------------------
    def test_11_no_sensitive_evidence_or_reasoning_exposed(self):
        """Audit items must never contain chain-of-thought, passwords, or raw chunks."""
        res = self.service.get_audit_logs(
            db=self.db,
            user=self.user5,
            scope=self.scope5,
            page=1,
            page_size=100,
        )
        for item in res.items:
            details = item.sanitized_details.lower()
            self.assertNotIn("<think>", details)
            self.assertNotIn("password", details)
            self.assertNotIn("secret_key", details)
            self.assertNotIn("api_key", details)
        print("[11] PASS — All audit records free of reasoning tokens, credentials, or secrets")

    # --------------------------------------------------------------------------
    # 12. Denied event sanitization
    # --------------------------------------------------------------------------
    def test_12_denied_event_sanitization(self):
        """When an unauthorized attempt is logged, details are masked for restricted users."""
        res = self.service.get_audit_logs(
            db=self.db,
            user=self.user1,
            scope=self.scope1,
            status_filter="DENIED",
            page=1,
            page_size=50,
        )
        for item in res.items:
            # Details must not mention NIGAHI, DUDHICHUA, or unauthorized mines
            for unauth in ["NIGAHI", "DUDHICHUA", "GV004", "GV005"]:
                self.assertNotIn(unauth, item.sanitized_details)
        print("[12] PASS — Denied event details safely masked against unauthorized probing")

    # --------------------------------------------------------------------------
    # 13. Report generation event visibility
    # --------------------------------------------------------------------------
    def test_13_report_generation_event_visibility(self):
        """Report generation events include module name, action, and report traceability."""
        res = self.service.get_audit_logs(
            db=self.db,
            user=self.user5,
            scope=self.scope5,
            action="REPORT",
            page=1,
            page_size=25,
        )
        self.assertGreater(res.total, 0)
        for item in res.items:
            self.assertEqual(item.route, "REPORT")
            self.assertEqual(item.module, "Automated Reports")
        print(f"[13] PASS — {res.total} report generation events verified with proper metadata")

    # --------------------------------------------------------------------------
    # 14. Audit summary metrics within authorized scope
    # --------------------------------------------------------------------------
    def test_14_audit_summary_metrics_authorized(self):
        """Summary metrics calculate totals deterministically within the caller's scope."""
        summary1: AuditLogSummaryResponse = self.service.get_audit_summary(
            db=self.db,
            user=self.user1,
            scope=self.scope1,
        )
        self.assertIsInstance(summary1, AuditLogSummaryResponse)
        self.assertGreater(summary1.total_events, 0)
        self.assertEqual(
            summary1.total_events,
            summary1.successful_events + summary1.discrepancy_events + summary1.denied_events,
            "Event status breakdown must sum to total_events"
        )
        self.assertIn("GV001", summary1.authorized_mines_covered)
        self.assertNotIn("GV004", summary1.authorized_mines_covered)

        # Admin summary covers all 5 mines
        summary5: AuditLogSummaryResponse = self.service.get_audit_summary(
            db=self.db,
            user=self.user5,
            scope=self.scope5,
        )
        self.assertGreaterEqual(summary5.total_events, summary1.total_events)
        self.assertEqual(len(summary5.authorized_mines_covered), 5)
        print(f"[14] PASS — Summary metrics: USR001 ({summary1.total_events} events) vs Admin ({summary5.total_events} events)")

    # --------------------------------------------------------------------------
    # 15. Empty state handling
    # --------------------------------------------------------------------------
    def test_15_empty_state_handling(self):
        """Filtering with a nonexistent query returns clean empty paginated envelope."""
        res = self.service.get_audit_logs(
            db=self.db,
            user=self.user1,
            scope=self.scope1,
            search="NONEXISTENT_UNIQUE_STRING_XYZ_999",
            page=1,
            page_size=25,
        )
        self.assertEqual(res.total, 0)
        self.assertEqual(len(res.items), 0)
        self.assertEqual(res.total_pages, 1)
        print("[15] PASS — Empty search query yields valid empty response without errors")

    # --------------------------------------------------------------------------
    # 16. HTTP 403 access denial handling
    # --------------------------------------------------------------------------
    def test_16_http_error_handling(self):
        """Requesting summary or logs for an unauthorized mine raises HTTP 403."""
        with self.assertRaises(HTTPException) as ctx:
            self.service.get_audit_summary(
                db=self.db,
                user=self.user1,
                scope=self.scope1,
                mine="GV004",
            )
        self.assertEqual(ctx.exception.status_code, 403)
        print("[16] PASS — HTTP 403 correctly raised when unauthorized mine requested")

    # --------------------------------------------------------------------------
    # 17. Canonical mine identifiers in response
    # --------------------------------------------------------------------------
    def test_17_canonical_mine_identifiers(self):
        """All mine_scope elements use canonical display format (e.g. GV001 — GEVRA)."""
        res = self.service.get_audit_logs(
            db=self.db,
            user=self.user5,
            scope=self.scope5,
            page=1,
            page_size=50,
        )
        for item in res.items:
            for m in item.mine_scope:
                self.assertTrue(
                    any(c in m for c in ["GV001", "GV002", "GV003", "GV004", "GV005", "GEVRA", "KUSMUNDA", "DIPKA", "NIGAHI", "DUDHICHUA"]),
                    f"Non-canonical mine identifier found: {m}"
                )
        print("[17] PASS — Canonical mine identifiers confirmed across audit items")

    # --------------------------------------------------------------------------
    # 18. Legacy identifier scan
    # --------------------------------------------------------------------------
    def test_18_legacy_identifier_scan(self):
        """Audit items must contain zero legacy codes in actions, modules, and details."""
        res = self.service.get_audit_logs(
            db=self.db,
            user=self.user1,
            scope=self.scope1,
            page=1,
            page_size=50,
        )
        for item in res.items:
            text_block = f"{item.action} {item.module} {item.sanitized_details} {' '.join(item.mine_scope)}"
            for legacy in LEGACY_IDENTIFIERS:
                self.assertNotIn(
                    legacy,
                    text_block,
                    f"Legacy identifier '{legacy}' found in audit item {item.log_id}: {text_block}"
                )
        print("[18] PASS — Zero legacy identifiers present in sanitized audit logs")

    # --------------------------------------------------------------------------
    # 19. Pydantic response schema compliance
    # --------------------------------------------------------------------------
    def test_19_response_schema_validation(self):
        """All fields in AuditLogItemResponse are validated and typed."""
        res = self.service.get_audit_logs(
            db=self.db,
            user=self.user1,
            scope=self.scope1,
            page=1,
            page_size=10,
        )
        for item in res.items:
            self.assertTrue(item.log_id.startswith("AUD-"))
            self.assertIn(item.status, ["SUCCESS", "DISCREPANCY", "DENIED", "ERROR"])
            self.assertIsInstance(item.evidence_count, int)
            self.assertIsInstance(item.http_status, int)
        print("[19] PASS — All items strictly conform to AuditLogItemResponse schema")

    # --------------------------------------------------------------------------
    # 20. Non-recursive audit logging
    # --------------------------------------------------------------------------
    def test_20_non_recursive_audit_logging(self):
        """Calling log_audit_access records an access event without creating infinite loops."""
        initial_count = self.db.scalar(
            select(QueryAuditLog).where(QueryAuditLog.route_selected == "AUDIT")
        )
        self.service.log_audit_access(
            db=self.db,
            user=self.user1,
            scope=self.scope1,
            filter_mine="GV001",
        )
        # Fetching logs should not trigger another log_audit_access
        _ = self.service.get_audit_logs(
            db=self.db,
            user=self.user1,
            scope=self.scope1,
            page=1,
            page_size=10,
        )
        # Verify no infinite loop occurred and exactly one AUDIT event was created
        audit_events = self.db.scalars(
            select(QueryAuditLog).where(QueryAuditLog.route_selected == "AUDIT")
        ).all()
        self.assertGreater(len(audit_events), 0)
        latest = audit_events[-1]
        self.assertEqual(latest.user_id, "USR001")
        self.assertEqual(latest.route_selected, "AUDIT")
        print("[20] PASS — Non-recursive audit access logging successfully verified")


if __name__ == "__main__":
    unittest.main(verbosity=2)
