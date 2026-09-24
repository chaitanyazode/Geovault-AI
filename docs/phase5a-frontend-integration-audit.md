# GeoVault AI — Phase 5A Frontend ↔ Backend Integration Audit Report

**Document Version:** 1.0  
**Phase:** 5A (Read-Only Inspection & Integration Audit)  
**Execution Timestamp:** September 21, 2026  
**Baseline Status:** Backend Verified (63/63 Tests Passing), Frontend Builds Cleanly (`next build` 10/10 Static Routes Generated)

---

## 1. Executive Summary & Baseline

Phase 5A conducts a comprehensive, read-only architectural and API integration audit between the Next.js frontend and the FastAPI/PostGIS/pgvector backend.

### Project Constraints Verified:
- **Read-Only Sources**: Both `F:\GeoVault\Coal Data\` (legacy) and `F:\GeoVault\geo_data\` (authoritative) remain 100% untouched.
- **Backend Stability**: All 63 automated tests in `backend/tests/` remain green. Zero backend files were modified during this audit.
- **Database Baseline**: PostgreSQL 16 + PostGIS + pgvector contains all 5 canonical mines (`GV001` Gevra, `GV002` Kusmunda, `GV003` Dipka, `GV004` Nigahi, `GV005` Dudhichua), 971 PostGIS features, 425 document chunks, and operational tables.
- **Container Health**: All 6 Docker containers (`geovault_backend`, `geovault_worker`, `geovault_postgres`, `geovault_frontend`, `geovault_redis`, `geovault_llm`) are up and healthy.
- **Frontend Compilation**: Next.js 14.2.35 compiles cleanly with 0 TypeScript and 0 linting errors.

---

## 2. Frontend Route Inventory

The user-facing Next.js application consists of seven active routes and one global shell:

| Route Path | File Path | Current Status | Primary Function | Navigation Visibility |
|---|---|---|---|---|
| `/` | `frontend/app/page.tsx` | Active | Landing Page / Capability Launchpad | Primary Sidebar Item 1 ("Dashboard") |
| `/ask` | `frontend/app/ask/page.tsx` | Active | Natural Language Query & AI Reasoning | Primary Sidebar Item 2 ("Ask GeoVault") |
| `/topics` | `frontend/app/topics/page.tsx` | Active | Topic Discovery, Terminology & Word Cloud | Primary Sidebar Item 3 ("Topics & Word Cloud") |
| `/reports` | `frontend/app/reports/page.tsx` | Active | Boardroom Report Generator & Viewer | Primary Sidebar Item 4 ("Report Generator") |
| `/logs` | `frontend/app/logs/page.tsx` | Active | Operational Governance & Query Audit Logs | Primary Sidebar Item 5 ("Logs") |
| `/evidence` | `frontend/app/evidence/page.tsx` | Unlinked | Evidence Inspector & Discrepancies Log | Unlinked in Sidebar (accessible via URL/links) |
| `/status` | `frontend/app/status/page.tsx` | Unlinked | System Health & Container Monitor | Unlinked in Sidebar (accessible via URL/links) |

### Navigation Shell Observations:
- `Sidebar.tsx` cleanly renders the 5 core items. Secondary links (`Help & Support`, `Feedback`) open mock modals.
- `/evidence` and `/status` remain functional standalone pages, but are currently not part of the standard 5-item operational navigation.

---

## 3. API Contract Audit & Comparison Matrix

For every frontend API call executed by `ApiClient` (`frontend/lib/api.ts`), the table below cross-references request/response schemas, TypeScript types, and backend FastAPI models:

| Frontend Module | API Endpoint | HTTP | Request Schema | Response Schema | TypeScript Type | Backend Model / Handler | Status |
|---|---|---|---|---|---|---|---|
| **Identity** | `/api/v1/auth/users` | `GET` | None | `List[Dict]` | `DemoUserOption[]` | `list_demo_users()` | **MATCH** |
| **Identity** | `/api/v1/auth/me` | `GET` | None | `Dict[str, Any]` | `UserProfileResponse` | `get_current_user_profile()` | **MATCH** |
| **Ask GeoVault** | `/api/v1/intelligence/natural-query` | `POST` | `NaturalQueryRequest` | `GroundedQueryResponse` | `GroundedQueryResponse` | `execute_natural_language_query()` | **MISMATCH (Minor)** |
| **Operational** | `/api/v1/intelligence/query` | `POST` | `IntelligenceQueryRequest` | `QueryResultPackage` | `QueryResultPackage` | `execute_intelligence_query()` | **MATCH** |
| **Operational** | `/api/v1/intelligence/analytics` | `POST` | `IntelligenceAnalyticsRequest` | `QueryResultPackage` | `QueryResultPackage` | `execute_intelligence_analytics()` | **MATCH** |
| **Operational** | `/api/v1/intelligence/compare` | `POST` | `MineCompareRequest` | `QueryResultPackage` | `QueryResultPackage` | `execute_mine_comparison()` | **MATCH** |
| **Topics** | `/api/v1/topics/analyze` | `POST` | `TopicAnalysisRequest` | `TopicAnalysisResponse` | `TopicResponse` | `analyze_topics_and_keywords()` | **MATCH** |
| **Topics** | `/api/v1/topics/keywords` | `GET` | Query params | `KeywordExtractionResponse` | `TopicKeywordItem[]` | `extract_scoped_keywords()` | **MATCH** |
| **Topics** | `/api/v1/topics/wordcloud/image/{fn}` | `GET` | Path param | `FileResponse (image/png)` | Image URL string | `serve_wordcloud_image()` | **MATCH** |
| **Reports** | `/api/v1/reports/generate` | `POST` | `ReportGenerateRequest` | `ReportMetadataResponse` | `ReportMetadataResponse` | `generate_report()` | **MATCH** |
| **Reports** | `/api/v1/reports/{id}` | `GET` | Path param | `ReportMetadataResponse` | `ReportMetadataResponse` | `get_report_metadata()` | **MATCH** |
| **Reports** | `/api/v1/reports/{id}/download/{fmt}` | `GET` | Path param | `FileResponse` | `Blob` | `download_report_docx/pdf()` | **MATCH** |
| **Evidence** | `/api/v1/evidence/{evidence_id}` | `GET` | Path param | `Dict[str, Any]` | `EvidenceItem` | `get_evidence_item()` | **MISMATCH (Critical)** |
| **Evidence** | `/api/v1/evidence/{id}/document` | `GET` | Path param | `FileResponse` | Stream / Blob | `stream_evidence_document()` | **MATCH** |
| **Conflicts** | `/api/v1/conflicts` | `GET` | None | `List[Dict]` | `ConflictItem[]` | `list_authorized_conflicts()` | **MATCH** |
| **Audit Logs** | `/api/v1/intelligence/logs` | `GET` | Query `limit` | `List[Dict]` | `AuditLogItem[]` | `get_operational_audit_logs()` | **MATCH** |
| **Health** | `/health` | `GET` | None | `Dict[str, str]` | `SystemHealth` | `health_check()` | **MATCH** |

### Specific Contract Mismatch Findings:

1. **Natural Query Route Enum (`GroundedQueryResponse.query_type`)**:
   - In `frontend/lib/types.ts`: `query_type: "SQL" | "ANALYTICS" | "RAG" | "HYBRID" | "REPORT" | "TOPIC"`.
   - In Phase 4 backend: Route can also be `"SPATIAL"` and `"GEOLOGY"`. When the backend returns `SPATIAL`, TypeScript type safety is bypassed or degraded.
2. **Confidence Status Values (`GroundedQueryResponse.confidence_status`)**:
   - In `frontend/lib/types.ts`: `"VERIFIED" | "PARTIAL" | "CONFLICT_DETECTED" | "INSUFFICIENT_AUTHORIZED_DATA"`.
   - In Phase 4 backend: Returns `"HIGH" | "GROUNDED" | "CONFLICT_DETECTED" | "INSUFFICIENT_DATA" | "PARTIAL_GROUNDING"`.
3. **Evidence Retrieval Endpoint (`/api/v1/evidence/{evidence_id}`)**:
   - Phase 4 generated spatial evidence IDs with prefix: `EV-SPATIAL-{mine_code}-{feature_id}` (e.g. `EV-SPATIAL-GEVRA-GV-BH-001`).
   - The backend `get_evidence_item()` endpoint in `backend/app/api/v1/evidence.py` checks the `Evidence` table, `DocumentChunk` table, and then falls back to `ProductionAnnual` checking legacy prefixes (`DEOM`, `KNUG`, `SSOP`). It does **NOT** query PostGIS spatial tables.
   - Result: Inspecting spatial evidence from the frontend triggers an HTTP 404, causing `EvidenceDrawer` to fall back to a generic document placeholder.

---

## 4. Phase 4 Capability Coverage Audit

| Capability Domain | Backend Support (Phase 4) | Frontend Consumability (Current) | Gap / Status |
|---|---|---|---|
| **STRUCTURED: Production** | Full 5 mines, 6 FYs (`production_annual`) | Consumed on Dashboard, Ask, Reports | **Supported** |
| **STRUCTURED: Equipment** | 150 HEMM records (`equipment_fleet`) | Routed in backend; no frontend UI cards/tables | **Backend Ready / Frontend Missing UI** |
| **STRUCTURED: Safety** | 30 incident records (`safety_records`) | Routed in backend; no frontend UI cards/tables | **Backend Ready / Frontend Missing UI** |
| **STRUCTURED: Environment** | 30 monitoring records (`environmental_records`) | Routed in backend; no frontend UI cards/tables | **Backend Ready / Frontend Missing UI** |
| **STRUCTURED: Geology** | 21 seams, 60 drillholes, 600 intervals | Routed in backend; no dedicated frontend geology table | **Backend Ready / Frontend Missing UI** |
| **RAG: Institutional PDFs** | 425 chunks with BGE-M3 vectors | Consumed via `/ask` and `/reports` | **Supported** |
| **POSTGIS: Geodesic Spatial** | `ST_DWithin`, `ST_Intersects`, `ST_Area`, `ST_Distance` | Routed via `/ask`; text answer rendered; no map visual | **Text Supported / Spatial Map Missing** |
| **HYBRID: SQL + RAG + Spatial** | Deterministic facts + qualitative context | Displayed in `/ask` progressive disclosure | **Supported** |
| **EVIDENCE: Traceability** | Citations, page numbers, coordinates, provenance | Displayed in `/ask`, `/reports`, `/evidence` | **Supported** |
| **CONFLICTS: Discrepancies** | Surfaced deterministically | Rendered in `ConflictAlert.tsx` | **Supported** |
| **DATA GAPS: Missing Periods** | Surfaced deterministically | Rendered in `DataGapAlert.tsx` | **Supported** |
| **AUDIT: Governance Logs** | Full `QueryAuditLog` capture | Rendered in `/logs` with filters | **Supported** |

---

## 5. Evidence Drawer Audit

The `EvidenceDrawer.tsx` slide-over component is the central inspection tool for grounded citations.

### Current Support Status:
1. **PDF Documents**:
   - Supports page number display, document classification tag, and page text preview.
   - **Failure Point**: The client performs `pageText.indexOf(highlightText)`. If tokenization or newline formatting differs between PyMuPDF and the chunker by even one character, `indexOf` returns `-1`. The drawer falls back to displaying: *"Exact highlight unavailable for this source; verified page text displayed above without arbitrary markers."*
2. **Excel Spreadsheets**:
   - Supports workbook name, sheet name, cell range, and table preview.
   - **Failure Point**: When `evidence.table_data` is absent, the component falls back to hardcoded mock HTML rows containing legacy DEOM-01 numbers (`4.10 MT`, `4.44 MT`, `108.3%`).
3. **Structured Database Records**:
   - Renders metadata (Mine, Department, Classification).
   - Shows formatted snippet and excerpt.
4. **PostGIS Spatial Evidence**:
   - **Failure Point**: The backend `/api/v1/evidence/{evidence_id}` endpoint does not have a handler for `EV-SPATIAL-*`. It throws 404, which triggers the frontend catch-block, disguising spatial records as a mock PDF reference.

---

## 6. Report API Audit

### Findings:
1. **Payload & Request Parameters**:
   - `ReportGenerateRequest` cleanly accepts `query`, `mine_code`, `compared_mines`, `start_year`, `end_year`, `include_charts`, `formats`.
   - Frontend `ReportGeneratorPage` provides a comprehensive parameter collapsible (`reportType`, `scopeLevel`, `timePeriod`, `detailLevel`, `selectedMine`, `startYear`, `endYear`).
2. **Natural Query Regex Limitation (Backend)**:
   - In `backend/app/services/report_service.py:70`:
     ```python
     mines_found = re.findall(r"\b(DEOM-01|KNUG-02|SSOP-03)\b", query, flags=re.IGNORECASE)
     ```
     Natural queries mentioning "Gevra", "Kusmunda", "Dipka", "Nigahi", or "Dudhichua" without explicit `mine_code` payload fail to extract the mine, falling back to the requesting user's assigned mine.
   - Admin default (line 133) defaults to `["DEOM-01", "KNUG-02", "SSOP-03"]`.
3. **Frontend Report Preview Hardcoding**:
   - In `frontend/app/reports/page.tsx` (lines 545–635), when displaying the report preview in the browser before PDF download, numerous fields fall back to hardcoded legacy mock strings:
     - `Dharani East Opencast Mine (DEOM-01)`
     - `Shakti Coalfields Ltd.`
     - `Central Coal Basin`
     - `Production_Data_DEOM-01.xlsx — Sheet: FY2024 — Range: B14:F14`
4. **SYNTHETIC_DEMO Disclosure in PDF**:
   - In `backend/app/services/report_pdf.py`, the running footer prints:
     `GeoVault AI • AI-Assisted Report • Generated: ...`
   - It does **not** currently print an explicit `PROVENANCE: SYNTHETIC_DEMO` watermark/disclosure on the PDF canvas.

---

## 7. Operational Audit Logs (`/logs`) Audit

### Findings:
- Backend `GET /api/v1/intelligence/logs` queries `QueryAuditLog` table directly with `limit` parameter.
- Administrators (`USR005`) receive enterprise-wide logs; scoped users receive only their authorized logs (`user_id == user.user_id`).
- Frontend displays:
  - Timestamp (formatted to locale string)
  - User ID badge
  - Action & Module (reconstructed from `route_selected`)
  - Route badge (`SQL`, `RAG`, `HYBRID`, `TOPIC`, `REPORT`)
  - Details / Question
  - Status badge (`Success`, `Discrepancy`, `Insufficient Data`, `Denied`)
  - Evidence count
- **Assessment**: The logs module is fully functional, grounded in real database rows, and does not fabricate logs.

---

## 8. Topics & Word Cloud (`/topics`) Audit

### Findings:
- **Data Source**: Analyzes authorized `DocumentChunk` records from PostgreSQL.
- **Backend API**: `POST /api/v1/topics/analyze`, `GET /api/v1/topics/keywords`, `GET /api/v1/topics/wordcloud/image/{filename}`.
- **Scoping**: Strictly filters chunks by user's authorized mines, department, and classification clearance before executing TF-IDF vectorization and WordCloud PNG generation.
- **Five-Mine Compatibility**: Fully compatible with all 5 canonical mines. The frontend dropdown dynamically populates available mines from the user's active scope (`normalizeAllowedMines(prof.scope.allowed_mines)`).
- **Normalization**: Handled cleanly via `normalizeTopicResponse()` in `frontend/lib/types.ts`.

---

## 9. Dashboard (`/`) Audit

### Comparison with Target Design Requirements:

| Target Design Specification | Current Implementation (`app/page.tsx`) | Audit Assessment |
|---|---|---|
| **Enterprise Aesthetic** | Soft gradient with large multi-colored SVG open-cast mine graphic (lines 21–144) | Needs simplification to clean, minimal white/light-gray enterprise palette |
| **GeoVault AI Branding** | Large typography with dual institutional logos in header | **Compliant** |
| **Unified Top Bar** | Dual logos (Ministry of Coal + Coal India) with user dropdown | **Compliant** |
| **User Selector Retained** | Dropdown with role switching (`USR001` through `USR005`) | **Compliant** |
| **No Unnecessary SIH Labels** | Removed in earlier refactor; no SIH badges on home | **Compliant** |
| **No Authorization Badges** | No intrusive clearance badges on home page | **Compliant** |
| **No Dummy Data** | Static SVG with no live data bindings | Clean, but lacks live status integration |
| **Three Prominent Cards** | Has 3 cards: "Ask Questions" (01), "Generate Reports" (02), "Explore Data" (03) | **Card 03 title should align to "Topics & Word Cloud"** |
| **Viewport Fit** | Hero is 340px, cards are 225px. May cause vertical scrolling on smaller laptop screens (1366x768) | Needs height optimization for 100% no-scroll desktop fit |

---

## 10. Catalog of Legacy, Mock & Static References

| File Path | Line(s) | Legacy / Mock Reference | Recommended Remediation |
|---|---|---|---|
| `frontend/app/ask/page.tsx` | 30–34 | `DEOM-01`, `KNUG-02`, `Mine A` sample prompts | Replace with canonical queries for Gevra, Kusmunda, Dipka, Nigahi, Dudhichua |
| `frontend/app/reports/page.tsx` | 28, 60 | Prompt placeholder referencing `Mine A` | Replace with canonical prompt referencing Gevra or Dudhichua |
| `frontend/app/reports/page.tsx` | 451, 550, 584, 606, 738, 802, 987, 1002, 1109, 1115 | Hardcoded `Dharani East Opencast Mine (DEOM-01)`, `Shakti Coalfields`, `Production_Data_DEOM-01.xlsx`, `EV-DEOM-2024` | Bind dynamically to `reportResult.mine_code`, `reportResult.mines_covered`, and real evidence citations |
| `frontend/app/reports/page.tsx` | 703, 837, 999 | Hardcoded `108.3%`, `+0.34 MT` fallbacks | Bind to dynamic metrics returned from `reportResult` |
| `frontend/components/EvidenceDrawer.tsx` | 475–492 | Hardcoded mock Excel table with DEOM-01 values | Render generic structured key-value view when tabular grid is absent; add PostGIS spatial renderer |
| `frontend/components/Header.tsx` | 48–63 | Hardcoded demo names (`Pavan Nimbalkar`, `Rajesh Kumar`, etc.) | Derive from user profile or provide clean canonical subsidiary engineering titles |
| `frontend/components/Header.tsx` | 67 | Hardcoded mine scope: `DEOM-01 & KNUG-02` | Dynamically display `formatScopeMines(profile.scope.allowed_mines)` |
| `frontend/app/evidence/page.tsx` | 120, 137, 141, 145, 149 | Hardcoded buttons for `EV-PRODUCTION_A-DEOM-01-2024` | Replace with canonical buttons (e.g. `EV-PRODUCTION_A-GEVRA-2024`, `EV-SPATIAL-GEVRA-GV-BH-001`) |
| `backend/app/services/report_service.py` | 70, 133 | Natural query regex only matches `DEOM-01\|KNUG-02\|SSOP-03`; admin default fallback | Add canonical mine names (`GEVRA`, `KUSMUNDA`, `DIPKA`, `NIGAHI`, `DUDHICHUA`) to regex |
| `backend/app/api/v1/evidence.py` | 158–175 | Evidence router checks legacy mine prefixes | Add handler for `EV-SPATIAL-*` to query `SpatialIntelligenceService` |

---

## 11. Missing Frontend Capabilities (Phase 4 Gap Analysis)

1. **Spatial Evidence Rendering**:
   - The frontend currently cannot display spatial evidence items (coordinates, distance in meters, spatial layer name, geometry type).
2. **Operational Domain Navigation**:
   - The frontend lacks direct tabular views for Equipment Fleet, Safety Incidents, Environmental PM10/Water metrics, and Coal Seam Master records. Users can only query them via natural language in `/ask`.
3. **Interactive Coalfield Spatial Map**:
   - The frontend currently has no Leaflet/MapLibre or GeoJSON map component to visually plot the 971 PostGIS features (boreholes, seam belts, hazard zones, lease boundaries) ingested in Phase 3B.

---

## 12. Recommended Remediation Strategy

To preserve stability and avoid breaking changes, fixes should follow a **minimal, backward-compatible** approach:

### Category A: Frontend Normalization & Clean-up (Zero Backend Changes)
- Update `frontend/lib/types.ts`:
  - Add `"SPATIAL" | "GEOLOGY"` to `GroundedQueryResponse.query_type`.
  - Expand `confidence_status` union to encompass backend return values (`"HIGH" | "GROUNDED" | "PARTIAL_GROUNDING" | "INSUFFICIENT_DATA"`).
- In `frontend/app/ask/page.tsx`: Replace legacy sample prompts (`DEOM-01`, `KNUG-02`, `Mine A`) with canonical 5-mine prompts.
- In `frontend/app/reports/page.tsx`: Replace hardcoded DEOM-01 strings with dynamic properties from `reportResult`.
- In `frontend/components/Header.tsx`: Replace static mine scope with dynamic `formatScopeMines(profile.scope.allowed_mines)`.
- In `frontend/components/EvidenceDrawer.tsx`: Add a dedicated view mode for spatial evidence (`source_type === "POSTGIS_SPATIAL"`).

### Category B: Minimal Backend Enhancements (Backward-Compatible)
- In `backend/app/services/report_service.py`: Extend `_parse_report_query()` regex to recognize canonical names (`GEVRA`, `KUSMUNDA`, `DIPKA`, `NIGAHI`, `DUDHICHUA`) and codes (`GV001`–`GV005`).
- In `backend/app/api/v1/evidence.py`: Add an explicit lookup branch for `evidence_id.startswith("EV-SPATIAL-")` that queries spatial tables and returns coordinates, distance, and layer metadata.
- In `backend/app/services/report_pdf.py`: Add `PROVENANCE: SYNTHETIC_DEMO` notice in running footers.

---

## 13. Files Requiring Modification in Subsequent Implementation

### Frontend:
1. `frontend/lib/types.ts` (Extend unions for query types and confidence statuses)
2. `frontend/app/page.tsx` (Align layout with minimal enterprise style and 3 capability cards)
3. `frontend/app/ask/page.tsx` (Update sample prompts to 5 canonical mines; add spatial response badge)
4. `frontend/app/reports/page.tsx` (Purge hardcoded DEOM text; bind to dynamic report metadata)
5. `frontend/components/EvidenceDrawer.tsx` (Add PostGIS spatial evidence rendering card; remove mock Excel fallback)
6. `frontend/components/Header.tsx` (Dynamic mine scope resolution)
7. `frontend/app/evidence/page.tsx` (Update sample lookup buttons)

### Backend (Minimal & Non-Breaking):
1. `backend/app/services/report_service.py` (Expand mine recognition regex)
2. `backend/app/api/v1/evidence.py` (Add `EV-SPATIAL-*` resolution branch)
3. `backend/app/services/report_pdf.py` (Add synthetic demo provenance notice)

---

## 14. Risk Assessment

| Risk | Severity | Impact | Mitigation Strategy |
|---|---|---|---|
| Modifying backend breaks existing 63 tests | HIGH | Regression | Keep all changes strictly additive; rerun `pytest tests/` after any backend edit |
| Next.js TypeScript build failure | MEDIUM | Broken CI/CD | Run `docker exec geovault_frontend npm run build` before committing |
| Modifying Report preview breaks PDF download | LOW | Formatting issue | Keep backend ReportLab builder decoupled from frontend DOM preview |

---

## 15. Build & Runtime Baseline Verification

- **Backend Pytest Suite**: 63/63 PASSED (100% green).
- **Frontend Production Build**: `npm run build` executed successfully, generating all 10 static pages with zero errors.
- **Docker Compose Health**: All 6 microservices running without restarts.

---

## 16. Recommended Implementation Order (Phase 5B Onward)

1. **Step 1 — Backend Backward-Compatible Enhancements**:
   - Update `report_service.py` regex for canonical 5-mine recognition.
   - Update `evidence.py` to resolve `EV-SPATIAL-*` citations.
   - Add synthetic demo notice to `report_pdf.py`.
   - Run `pytest tests/` to confirm 63/63 green.
2. **Step 2 — Frontend Type Definitions & Evidence Drawer**:
   - Update `types.ts` for spatial routes and status enums.
   - Implement PostGIS spatial evidence rendering in `EvidenceDrawer.tsx`.
3. **Step 3 — Report Generator Clean-up**:
   - Remove hardcoded DEOM-01 / Shakti Coalfields strings from `reports/page.tsx`.
   - Connect report preview directly to backend `reportResult`.
4. **Step 4 — Ask GeoVault & Header Modernization**:
   - Update `Header.tsx` to dynamically format active mine scope.
   - Update `ask/page.tsx` with canonical 5-mine prompts and spatial citation badges.
5. **Step 5 — Dashboard Refinement**:
   - Refine `page.tsx` to minimal enterprise aesthetic with 3 prominent capability cards fitting a desktop viewport without vertical scrolling.
6. **Step 6 — End-to-End Build & Validation**:
   - Run `npm run build` and browser verification.

---
*Audit complete. Awaiting user review and approval before proceeding to implementation.*
