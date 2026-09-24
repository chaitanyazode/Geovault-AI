# GeoVault AI — Phase 5F: Audit Logs & Enterprise Governance Report

> **Smart India Hackathon 2026 — Problem Statement 26023**  
> **Document Reference:** `docs/phase5f-audit-logs.md`  
> **Status:** Production Verified (All 20/20 Test Cases Passed)  
> **Execution Context:** Dockerized FastAPI Backend + Next.js Frontend + PostgreSQL 16/PostGIS/pgvector  

---

## 1. Executive Summary

Phase 5F delivers the centralized **Audit Logs & Governance System** (`/logs`) for GeoVault AI. While conventional systems treat logs as passive text dumps, GeoVault AI implements **Audit Logs as Protected Institutional Records**. 

Every interaction across the platform — whether structured SQL analytics, hybrid multi-source reasoning, topic clustering, report generation, or geospatial evaluations — is immutably logged with comprehensive execution metadata. Crucially, access to audit records themselves enforces the same strict **Authorization-Before-Retrieval** architectural boundary governing operational data: restricted personnel (such as Mine Engineers and Managers) can only observe audit history within their permitted organizational scope, while Enterprise Administrators possess full system-wide transparency.

All 20 test cases in `backend/tests/test_phase5f_audit_logs.py` pass with a 100% success rate, zero legacy mine identifiers are present, and the Next.js frontend builds with zero TypeScript or linting errors.

---

## 2. Architectural Context & Security Foundation

### The Authorization Boundary on Audit Data
A critical vulnerability in enterprise analytics is **Audit Log Leakage** — wherein a user denied direct access to sensitive data learns of its existence or operational details by reading audit records. GeoVault AI strictly eliminates this vulnerability:

```text
User / Role Identity (e.g. USR001 - Mining Engineer)
          │
          ▼
Central AuthorizationService (Resolves Role + Clearance + Assigned Mine Scope)
          │
          ▼
Pre-Retrieval Scope Filter (Applies WHERE user_id = USR001 AND mine in permitted_scope)
          │
          ▼
PostgreSQL query_audit_logs (Server-Side Pagination & Sub-query Isolation)
          │
          ▼
Sanitization Pipeline (Masks unauthorized targets, strips CoT reasoning, ensures zero credential leakage)
          │
          ▼
AuditLogPaginatedResponse Envelope (Delivered to Next.js UI)
```

### Key Security Invariants Enforced
1. **Scope Isolation:** Non-admin users (`USR001`–`USR004`) cannot view events performed by other users or query events referencing unpermitted mines.
2. **Denial Probing Protection:** When an unauthorized access attempt is recorded, the target entity is sanitized for restricted users (`"Security boundary enforced: Request outside authorized operational scope"`), preventing reconnaissance probing.
3. **No Chain-of-Thought / Secret Leakage:** Internal LLM reasoning tags (`<think>...</think>`), tokens, database connection strings, passwords, and private API keys are filtered before serialization.
4. **Non-Recursive Audit Logging:** Navigating to or filtering the `/logs` endpoint generates an `AUDIT_LOG_ACCESS` event without triggering an infinite audit-of-audit cascade.

---

## 3. Audit Log Data Model & Lifecycle

Audit logs are persisted in PostgreSQL table `query_audit_logs` with the following schema:

| Column | Type | Description |
| :--- | :--- | :--- |
| `log_id` | `VARCHAR(100)` PK | Unique event identifier (e.g., `LOG-A1B2C3D4E5F6` or `AUD-XXXXXXXXXXXX`) |
| `user_id` | `VARCHAR(50)` FK | Identity of requesting actor (`USR001`–`USR005`) |
| `question` | `TEXT` | Sanitized natural language prompt or structured query |
| `route_selected` | `VARCHAR(50)` | Architectural route: `SQL`, `RAG`, `HYBRID`, `ANALYTICS`, `TOPIC`, `REPORT`, `GEOLOGY`, `SPATIAL`, `AUDIT` |
| `authorized_scope_applied` | `JSONB` | Snapshot of RBAC/ABAC policy active at query execution time |
| `retrieval_filter` | `JSONB` | Metadata filters applied during retrieval |
| `evidence_count` | `INTEGER` | Number of verified evidence records retrieved |
| `evidence_status` | `VARCHAR(50)` | Grounding outcome: `VERIFIED`, `PARTIAL`, `CONFLICT`, `INSUFFICIENT_AUTHORIZED_DATA` |
| `response_summary` | `TEXT` | High-level summary of system response or denial notification |
| `execution_time_ms` | `INTEGER` | Wall-clock execution duration in milliseconds |
| `created_at` | `TIMESTAMPTZ` | Immutable UTC timestamp |

---

## 4. Backend Implementation

### 4.1 Schema Definitions (`backend/app/schemas/audit.py`)
- `AuditLogItemResponse`: Sanitized audit item containing `log_id`, `timestamp`, `user_id`, `action`, `module`, `route`, `mine_scope`, `status`, `evidence_status`, `evidence_count`, `execution_time_ms`, `sanitized_details`, `report_id`, `correlation_id`, `http_status`.
- `AuditLogSummaryResponse`: Scope-bounded KPI aggregates: `total_events`, `successful_events`, `discrepancy_events`, `denied_events`, `report_events`, `avg_latency_ms`, and `authorized_mines_covered`.
- `AuditLogPaginatedResponse`: Server-side paginated envelope with `items`, `total`, `page`, `page_size`, `total_pages`.

### 4.2 Centralized Audit Service (`backend/app/services/audit_service.py`)
- **`get_audit_logs()`**: Applies role-based WHERE clauses, filters by canonical mine aliases, validates dates, matches text queries, executes sub-query counting, and applies offset pagination.
- **`get_audit_summary()`**: Computes deterministic KPI metrics across authorized rows only, guaranteeing partition invariant: `total_events == successful_events + discrepancy_events + denied_events`.
- **`serialize_log_entry()`**: Canonicalizes mine identifiers to primary labels (`GV001 — GEVRA`, `GV002 — KUSMUNDA`, etc.), sanitizes private reasoning tags, and filters `mine_scope` so unauthorized mines are never exposed to restricted actors.
- **`log_audit_access()`**: Safely logs audit view actions with route `AUDIT` and non-recursive error handling.

### 4.3 API Router (`backend/app/api/v1/audit.py`)
- `GET /api/v1/audit-logs/`: Paginated endpoint accepting query parameters (`page`, `page_size`, `mine`, `action`, `status_filter`, `user_id_filter`, `start_date`, `end_date`, `search`).
- `GET /api/v1/audit-logs/summary`: Scope-bounded summary card metrics endpoint.
- `GET /api/v1/intelligence/logs`: Maintained with full backward compatibility delegating to `AuditLogService`.

---

## 5. Frontend Implementation (`/logs`)

The `/logs` interface in `frontend/app/logs/page.tsx` delivers an enterprise governance control center:

1. **Header & Context Badge**: Displays active user persona (`USR001` Mining Engineer vs `USR005` Administrator), institutional role, clearance level, and authorized mine scope tags.
2. **KPI Summary Cards**:
   - Total System Events
   - Successful Queries (`status: SUCCESS`)
   - Verified Discrepancies (`status: DISCREPANCY` with conflict badge)
   - Security Denials (`status: DENIED` / HTTP 403)
   - Reports Generated (`route: REPORT` with download links)
3. **Institutional Filter Toolbar**:
   - Authorized Mine dropdown (dynamically populated based on active user clearance)
   - Architectural Route filter (`SQL`, `RAG`, `HYBRID`, `ANALYTICS`, `TOPIC`, `REPORT`, `GEOLOGY`, `SPATIAL`, `AUDIT`)
   - Semantic Status filter (`ALL`, `SUCCESS`, `DISCREPANCY`, `DENIED`, `ERROR`)
   - Text Search input (searches correlation IDs, questions, details)
   - Refresh button with loading spinner
4. **Server-Side Paginated Table**:
   - Timestamp (ISO with relative age)
   - User ID with role badge
   - Target Mine Scope (canonical tags)
   - Module & Institutional Action
   - Route (badge with distinct theme color)
   - Semantic Outcome Status (`SUCCESS`, `DISCREPANCY`, `DENIED`)
   - Evidence Count & Latency (ms)
   - Quick Action: View Detail button
5. **Event Detail Drawer (Modal)**:
   - Complete metadata breakdown (Correlation ID, HTTP code, Evidence Status)
   - Scope snapshot applied during execution
   - Sanitized request details
   - Associated Report ID link (navigating to `/reports` if applicable)

---

## 6. Canonical Five-Mine Scope Alignment

All audit logging logic strictly conforms to the canonical 5-mine scope:

| Canonical ID | Canonical Mine Name | Primary Subsidiary | Status |
| :--- | :--- | :--- | :--- |
| `GV001` | GEVRA | SECL | Operational |
| `GV002` | KUSMUNDA | SECL | Operational |
| `GV003` | DIPKA | SECL | Operational |
| `GV004` | NIGAHI | NCL | Operational |
| `GV005` | DUDHICHUA | NCL | Operational |

Zero occurrences of legacy mock identifiers (`DEOM-01`, `KNUG-02`, `SSOP-03`, `Dharani`, `Shakti`, `Mine A`) exist in active user-facing UI or serialized response payloads.

---

## 7. Test Verification & Results

### 7.1 Dedicated Phase 5F Test Suite (`backend/tests/test_phase5f_audit_logs.py`)
All 20 test cases pass deterministically:

```text
tests/test_phase5f_audit_logs.py::TestPhase5FAuditLogs::test_01_authorized_audit_log_access PASSED [  5%]
tests/test_phase5f_audit_logs.py::TestPhase5FAuditLogs::test_02_unauthorized_mine_filter_blocked PASSED [ 10%]
tests/test_phase5f_audit_logs.py::TestPhase5FAuditLogs::test_03_scope_isolation_usr001_vs_usr005 PASSED [ 15%]
tests/test_phase5f_audit_logs.py::TestPhase5FAuditLogs::test_04_admin_full_visibility PASSED [ 20%]
tests/test_phase5f_audit_logs.py::TestPhase5FAuditLogs::test_05_multi_mine_manager_scope PASSED [ 25%]
tests/test_phase5f_audit_logs.py::TestPhase5FAuditLogs::test_06_mine_filtering PASSED [ 30%]
tests/test_phase5f_audit_logs.py::TestPhase5FAuditLogs::test_07_action_filtering PASSED [ 35%]
tests/test_phase5f_audit_logs.py::TestPhase5FAuditLogs::test_08_status_filtering PASSED [ 40%]
tests/test_phase5f_audit_logs.py::TestPhase5FAuditLogs::test_09_pagination_controls PASSED [ 45%]
tests/test_phase5f_audit_logs.py::TestPhase5FAuditLogs::test_10_no_unauthorized_events_leaked PASSED [ 50%]
tests/test_phase5f_audit_logs.py::TestPhase5FAuditLogs::test_11_no_sensitive_evidence_or_reasoning_exposed PASSED [ 55%]
tests/test_phase5f_audit_logs.py::TestPhase5FAuditLogs::test_12_denied_event_sanitization PASSED [ 60%]
tests/test_phase5f_audit_logs.py::TestPhase5FAuditLogs::test_13_report_generation_event_visibility PASSED [ 65%]
tests/test_phase5f_audit_logs.py::TestPhase5FAuditLogs::test_14_audit_summary_metrics_authorized PASSED [ 70%]
tests/test_phase5f_audit_logs.py::TestPhase5FAuditLogs::test_15_empty_state_handling PASSED [ 75%]
tests/test_phase5f_audit_logs.py::TestPhase5FAuditLogs::test_16_http_error_handling PASSED [ 80%]
tests/test_phase5f_audit_logs.py::TestPhase5FAuditLogs::test_17_canonical_mine_identifiers PASSED [ 85%]
tests/test_phase5f_audit_logs.py::TestPhase5FAuditLogs::test_18_legacy_identifier_scan PASSED [ 90%]
tests/test_phase5f_audit_logs.py::TestPhase5FAuditLogs::test_19_response_schema_validation PASSED [ 95%]
tests/test_phase5f_audit_logs.py::TestPhase5FAuditLogs::test_20_non_recursive_audit_logging PASSED [100%]
======================== 20 passed in 1.52s ========================
```

### 7.2 Frontend Production Build
```text
✓ Compiled successfully
✓ Generating static pages (10/10)
Routes: /, /ask, /evidence, /logs, /reports, /status, /topics
TypeScript errors: 0
ESLint errors: 0
```

---

## 8. Summary of Files Created & Modified

1. **`backend/app/schemas/audit.py`** (Created): Pydantic response models for audit items, summary cards, and pagination envelope.
2. **`backend/app/services/audit_service.py`** (Created): Centralized service enforcing Authorization-Before-Retrieval, safe sanitization, and metric aggregation.
3. **`backend/app/api/v1/audit.py`** (Created): REST API endpoints `/api/v1/audit-logs/` and `/summary`.
4. **`backend/app/api/v1/__init__.py`** (Updated): Registered `audit_router`.
5. **`backend/app/api/v1/intelligence.py`** (Updated): Maintained `/logs` route compatibility.
6. **`backend/app/services/report_service.py`** (Updated): Aligned alias resolution for consistent security rejection.
7. **`frontend/lib/types.ts`** (Updated): Added TypeScript definitions for audit items and summary envelopes.
8. **`frontend/lib/api.ts`** (Updated): Added `getAuditLogsPaged` and `getAuditSummary` methods.
9. **`frontend/app/logs/page.tsx`** (Updated): Enterprise UI with filters, KPI cards, table, and detail drawer.
10. **`backend/tests/test_phase5f_audit_logs.py`** (Created): 20 comprehensive unit and integration tests.
11. **`docs/phase5f-audit-logs.md`** (Created): Formal Phase 5F documentation.
