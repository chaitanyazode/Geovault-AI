# Phase 5C — Ask GeoVault & Evidence UX Report
**GeoVault AI — AI-Powered Geological, Mining and Operational Reporting Solution**  
**Smart India Hackathon 2026 — Problem Statement 26023**  
**Date:** September 22, 2026  
**Status:** COMPLETE & VERIFIED

---

## Executive Summary

Phase 5C establishes `/ask` as the premier conversational and evidence-grounded demonstration interface for GeoVault AI. The interface exposes the full multi-modal intelligence stack across **STRUCTURED**, **RAG**, **SPATIAL**, **GEOLOGY**, and **HYBRID** routes with verified source traceability down to page numbers, database records, and PostGIS vector coordinates.

All work adhered to core institutional safety invariants:
- Source datasets `F:\GeoVault\Coal Data\` and `F:\GeoVault\geo_data\` remained 100% read-only and untouched.
- Zero ingestion routines were run.
- Zero database migrations or schema modifications.
- Zero mock data or fabricated numbers; all metrics are directly bound to the backend API response.
- Next.js production build succeeded (`10/10` static pages compiled, 0 TypeScript/ESLint errors).
- Automated test suite expanded with a new comprehensive Phase 5C suite (`tests/test_phase5c_ask_evidence.py`).

---

## 1. Ask Page Structure (`frontend/app/ask/page.tsx`)

The `/ask` route has been engineered as an enterprise-grade conversational console:
- **Header Context**: Integrated with the system header displaying the active user profile, assigned mine, and dynamic organizational scope.
- **Main Container**:
  - Page Title: `Ask GeoVault`
  - Subtitle: *Ask evidence-grounded questions across authorized mining, geological and operational records.*
  - Query Input: Full-width responsive prompt box with keyboard shortcut support (Enter key submission).
  - Submit Button: Primary navy CTA (`Query`) with integrated loading spinner.
- **Canonical Example Prompts**:
  1. `"What was GEVRA's production in FY2024-25?"` (STRUCTURED/SQL route)
  2. `"What geological observations were reported for GEVRA in FY2024-25?"` (GEOLOGY/RAG route)
  3. `"Which boreholes are within 500 metres of a geological feature?"` (SPATIAL route)
  4. `"Compare FY2024-25 production across the five mines."` (ANALYTICS route)
  5. `"Explain the production shortfall using operational and geological evidence."` (HYBRID route)

---

## 2. Query Route Display

The interface directly reflects the actual backend intelligence route returned in `response.query_type`, eliminating frontend guesswork:
- `STRUCTURED` / `SQL`: Rendered in royal blue (`bg-blue-50 text-blue-900 border-blue-300`).
- `ANALYTICS`: Rendered in blue-indigo badge styling.
- `RAG`: Rendered in slate-neutral styling (`bg-slate-100 text-slate-700 border-slate-300`).
- `SPATIAL`: Rendered in high-visibility cyan (`bg-cyan-50 text-cyan-900 border-cyan-300`).
- `GEOLOGY`: Rendered in deep purple (`bg-purple-50 text-purple-900 border-purple-300`).
- `HYBRID`: Rendered in rich indigo (`bg-indigo-50 text-indigo-900 border-indigo-300`).
- Every response includes execution latency (e.g. `2.41s latency`) and an explicit dataset provenance badge (`SYNTHETIC_DEMO`).

---

## 3. Evidence UX & Multi-Modal Cards (`frontend/components/EvidenceCard.tsx`)

Evidence items are presented with clear distinction across four core modalities:
1. **DOCUMENT Evidence**:
   - Displays document filename, department/report type, mine code, page number, verbatim excerpt, and provenance tag.
   - Includes "Inspect" button to open the sliding Evidence Drawer.
2. **STRUCTURED Evidence**:
   - Displays source register/table name, mine code, financial year, record ID, and structured snippet.
3. **SPATIAL Evidence**:
   - Displays PostGIS layer name, feature ID, geometry type, operation (`ST_DWithin`, `ST_Distance`), calculated distance in meters, and WGS84 coordinates.
   - Micro SVG Radar preview indicating spatial proximity to mine centroid.
4. **GEOLOGY Evidence**:
   - Explicitly categorized by geological domain: Coal Seam Belts, Boreholes Master, or Geotechnical Hazard Zones.

---

## 4. PostGIS Spatial Evidence UX & Visualization (`frontend/components/EvidenceDrawer.tsx`)

The sliding Evidence Drawer (`EvidenceDrawer.tsx`) includes:
- **Interactive SVG Spatial Canvas**:
  - Displays a clean Cartesian grid with concentric buffer rings (100m, 250m, 500m).
  - Plots mine center origin vs. target feature point with dashed connection line and distance annotation.
  - Coordinate reference annotation: `EPSG:4326 (WGS84)` and PostGIS query engine tag.
- **Detailed Attributes**: Layer Name, Feature ID, Geometry Type, Spatial Operation, and WGS84 coordinates (`Longitude`, `Latitude`).
- **Zero Mock Fallback**: When structured metrics are absent, displays `"Source details are unavailable for this evidence item."` without fabricating numbers.
- **Document Stream**: Native link to `/api/v1/evidence/{id}/document` for authenticated PDF page streaming.

---

## 5. Dynamic Structured Results & KPIs

For queries returning structured operational data, the page dynamically extracts and renders:
- **KPI Metrics Cards**:
  - **Actual Production**: e.g., `56.10 MT`
  - **Target Output**: e.g., `58.50 MT`
  - **Achievement %**: e.g., `95.90%`
  - **Variance**: e.g., `-2.40 MT`
- **Multi-Mine Comparison Table**:
  - When comparing multiple mines (e.g. `GEVRA`, `KUSMUNDA`, `DIPKA`, `NIGAHI`, `DUDHICHUA`), dynamically lists Mine Code, Mine Name, Actual, Target, Achievement %, and Variance.
- All values originate directly from the API response (`response.structured_results`). No frontend calculation.

---

## 6. Hybrid Results ("How GeoVault Answered")

When a query triggers `HYBRID` intelligence (e.g., `"Explain the production shortfall..."`), the interface renders a compact synthesis equation:
```text
[Structured Operational Data] + [Document Reports (PyMuPDF)] + [PostGIS Spatial Vectors] = [Grounded Synthesis (Qwen3-8B)]
```
Only source categories actually returned in `response.evidence` are rendered. If PostGIS was not invoked for a particular hybrid query, spatial is omitted from the equation.

---

## 7. No-Guess & Uncertainty UX

To maintain strict epistemic integrity and prevent unsupported causal claims:
- **Measured Facts**: Grouped in an emerald card highlighting database-verified figures.
- **Source Observations**: Rendered in a separate context card highlighting observations from CMPDI/CIL reports.
- **Inference Note**: Clearly demarcated with italicized styling (*"Inference note: ..."*), preventing the user from confusing AI-synthesized explanation with primary source measurements.
- **Conflict & Limitation Alerts**:
  - Conflicting sources trigger `ConflictAlert`.
  - Data gaps trigger `DataGapAlert`.
  - Insufficient authorized data displays a high-visibility amber warning.

---

## 8. Robust Error Handling

The application handles all HTTP status codes gracefully without crashing or leaking protected information:
- **HTTP 403 (Forbidden)**:
  - Error: `"Access to this information is outside your authorized scope."`
  - Triggers `AccessRestrictedAlert` with zero leakage of protected mine metrics or sensitive records.
- **HTTP 400 / 422 (Validation)**:
  - Displays user-friendly query execution notice.
- **HTTP 404 / Empty Evidence**:
  - Displays `"No supporting evidence was returned for this query."`
  - Prevents the system from fabricating an answer when no data exists.
- **Network / 500 Errors**:
  - Displays network connectivity notice with actionable retry guidance.

---

## 9. Authorization Demonstration

Mine-level multi-tenant isolation was validated using evaluation identities:
- **USR001 (Mining Engineer, GEVRA)**:
  - Querying `"What was GEVRA's production in FY2024-25?"` succeeds with verified production metrics and citations.
  - Querying `"What was NIGAHI coal production in 2024?"` raises `HTTP 403 Forbidden` with `"Access Denied: User 'USR001' is not authorized to access data for mine 'NIGAHI'."`
  - Zero Nigahi production data or classified snippets are leaked in the error payload.
- **USR005 (Administrator)**:
  - Can query across all five mines simultaneously with enterprise scope.

---

## 10. Verification Results

### 10.1 Frontend Next.js Production Build
Executed `docker exec geovault_frontend npm run build`:
```text
> geovault-frontend@0.1.0 build
> next build

  ▲ Next.js 14.2.35

   Creating an optimized production build ...
 ✓ Compiled successfully
   Linting and checking validity of types ...
   Collecting page data ...
 ✓ Generating static pages (10/10)
   Finalizing page optimization ...
   Collecting build traces ...

Route (app)                              Size     First Load JS
┌ ○ /                                    2.85 kB        99.7 kB
├ ○ /_not-found                          873 B          88.1 kB
├ ○ /ask                                 8.53 kB         107 kB
├ ○ /evidence                            6.06 kB          96 kB
├ ○ /logs                                2.47 kB        92.7 kB
├ ○ /reports                             12.2 kB         108 kB
├ ○ /status                              2.81 kB          93 kB
└ ○ /topics                              6.66 kB        93.9 kB
+ First Load JS shared by all            87.3 kB

○  (Static)  prerendered as static content
```
- **Static Pages Compiled:** 10/10
- **TypeScript Errors:** 0
- **ESLint Errors:** 0

### 10.2 Backend Automated Test Suite
- New test suite: `backend/tests/test_phase5c_ask_evidence.py`
  - `test_01_canonical_gevra_production_structured`: PASS
  - `test_02_canonical_gevra_geology_observations`: PASS
  - `test_03_canonical_boreholes_spatial_500m`: PASS
  - `test_04_canonical_compare_production_across_mines`: PASS
  - `test_05_canonical_production_shortfall_hybrid`: PASS
  - `test_06_mine_isolation_403_denial_unauthorized`: PASS
  - `test_07_spatial_evidence_endpoint_wgs84`: PASS

---

## 11. Legacy Data Purge Audit

Exhaustive search across all frontend and user-facing code confirmed zero occurrences of:
- `DEOM-01`: 0 user-facing occurrences (historical fixture fallback updated to `GV001`).
- `KNUG-02`: 0 occurrences.
- `SSOP-03`: 0 occurrences.
- `Mine A`: 0 occurrences.
- `Dharani East`: 0 occurrences.
- `Shakti Coalfields`: 0 occurrences.
- `4.10 MT` / `4.44 MT` / `108.3%` / `+0.34 MT`: 0 occurrences.

---

## 12. Conclusion & Next Steps

Phase 5C successfully delivers an enterprise-grade conversational and evidence verification interface on `/ask`. The interface is fully backed by real PostGIS spatial queries, deterministic SQL analytics, semantic document retrieval, and Qwen3-8B synthesis with complete mathematical integrity and ABAC security.

Phase 5C is **COMPLETE**. System is paused awaiting user review.
