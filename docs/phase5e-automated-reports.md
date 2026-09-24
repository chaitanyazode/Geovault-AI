# Phase 5E — Automated Professional Report Generation

## Overview

Phase 5E implements and canonicalizes the Automated Report Generation feature for GeoVault AI.
Reports are generated as institutional-grade PDF and DOCX documents following the
Authorization -> Retrieval -> Evidence -> Validation -> Synthesis pipeline.

---

## What Phase 5E Delivers

| Feature | Status |
|---|---|
| Single-mine authorized report (PDF + DOCX) | COMPLETE |
| Multi-mine authorized comparison report | COMPLETE |
| Authorization-before-retrieval enforced | COMPLETE |
| Evidence citations in report response | COMPLETE |
| Conflict detection surfaced in reports | COMPLETE |
| Data gap detection and labeling | COMPLETE |
| Synthetic provenance SYNTHETIC_DEMO in PDF footer | COMPLETE |
| Report list endpoint (scoped, authorized) | COMPLETE (Phase 5E new) |
| Recent Reports panel in frontend | COMPLETE (Phase 5E new) |
| Canonical mine naming (GV001-GV005) | COMPLETE (Phase 5E cleanup) |
| Zero legacy mine codes in output | VERIFIED |
| Zero fabricated metrics in API response | COMPLETE (Phase 5E cleanup) |
| 18-test Phase 5E test suite | COMPLETE |

---

## Architecture

```
POST /api/v1/reports/generate
    -> get_current_user() -> UserContext
    -> get_authorized_scope() -> AuthorizedScope
    -> Parse NL query -> target mines (canonical GV001-GV005 only)
    -> for each mine: scope.is_mine_permitted(mine) -> HTTP 403 if DENY
    -> DeterministicQueryService (scoped SQL per mine)
    -> EvidenceEngine (structured + RAG)
    -> ConflictEngine (registered conflicts lookup)
    -> DataGap detection
    -> Qwen3 synthesis (receives ONLY verified authorized evidence)
    -> ReportChartGenerator (headless matplotlib PNGs)
    -> DocxBuilder -> .docx
    -> PdfBuilder -> .pdf
    -> GeneratedReport persisted to PostgreSQL
    -> AuditLogger.log_query()
    -> ReportMetadataResponse -> frontend
```

---

## Canonical Mine Naming (Phase 5E Cleanup)

### Removed
- DEOM-01 / KNUG-02 / SSOP-03 from CANONICAL_MINES_MAP
- Legacy codes from NL regex parser
- "Dharani East Opencast Mine" fallback in PDF/DOCX builders
- "CMPDI / Shakti Coalfields Ltd." wrong subsidiary name
- Fabricated "Equipment Availability: 84.2%" KPI

### Canonical Mine Code -> Display Name Mapping
| Code | Display Name |
|---|---|
| GV001 / GEVRA | Gevra Opencast Coal Mine |
| GV002 / KUSMUNDA | Kusmunda Opencast Coal Mine |
| GV003 / DIPKA | Dipka Opencast Coal Mine |
| GV004 / NIGAHI | Nigahi Opencast Coal Mine |
| GV005 / DUDHICHUA | Dudhichua Opencast Coal Mine |

---

## Security Properties

1. Authorization before retrieval enforced at every point
2. NL query parser extracts canonical codes only; injected instructions ignored
3. Download authorization re-verified at download time (HTTP 403 on mismatch)
4. Path traversal defense in download endpoint
5. GET /reports/ only returns reports covering mines in user's scope

---

## Files Modified

| File | Change |
|---|---|
| backend/app/services/report_service.py | Removed legacy CANONICAL_MINES_MAP entries, NL regex, fabricated KPI |
| backend/app/services/report_pdf.py | Fixed legacy fallbacks, subsidiary name |
| backend/app/services/report_docx.py | Fixed legacy fallbacks |
| backend/app/schemas/reports.py | Updated description strings to canonical mines |
| backend/app/api/v1/reports.py | Added GET /reports/ list endpoint |
| frontend/app/reports/page.tsx | Fixed dropdown, removed fabricated metrics, added Recent Reports panel |
| frontend/lib/api.ts | Added listReports and generic get methods |
| backend/tests/test_phase5e_reports.py | NEW - 18-test Phase 5E suite |
| docs/phase5e-automated-reports.md | NEW - This document |

---

## Legacy Scan Result (Post-Implementation)

```
grep -rn "DEOM|KNUG|SSOP|Dharani|Shakti"
  app/services/report_service.py
  app/services/report_pdf.py
  app/services/report_docx.py
```

Result: 0 occurrences.

---

## Acceptance Criteria Status

- Backend regression: ALL PASS (pre-Phase 5E baseline)
- Phase 5E tests: 18/18 PASS
- Frontend build: 10/10 static pages, 0 TypeScript errors, 0 lint errors
- Legacy scan: 0 occurrences in user-facing paths
