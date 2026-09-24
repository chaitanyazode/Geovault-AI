# GeoVault AI — Phase 5D: Topics & Word Cloud UX + Authorization Integration

**Smart India Hackathon 2026 — Problem Statement 26023**  
**Component**: Automated Topic Identification + Word Cloud (`/topics`)  
**Status**: Completed & Verified  

---

## 1. Overview & Objective

Phase 5D delivers the complete production-grade implementation of the second primary product outcome defined in `AGENTS.md`: **Automated Topic Identification and Word Cloud Visualization**.

The platform extracts, filters, ranks, and clusters terminology across real authorized document chunks and structured geological/mining records for the canonical five-mine demonstration scope (`GV001`–`GV005`):
- **GV001**: GEVRA (SECL)
- **GV002**: KUSMUNDA (SECL)
- **GV003**: DIPKA (SECL)
- **GV004**: NIGAHI (NCL)
- **GV005**: DUDHICHUA (NCL)

All analysis is strictly constrained by user identity, role, and permission scope prior to retrieval. No mock, static, or fabricated topic data is utilized.

---

## 2. Scoped Chunk Selection & Canonical Mapping

### 2.1 Multi-Representation Entity Resolution
In the underlying PostgreSQL database (`document_chunks`), document chunks are tagged with varying canonical representations:
- Canonical mine codes: `GV001`, `GV002`, `GV003`, `GV004`, `GV005`
- Canonical uppercase names: `GEVRA`, `KUSMUNDA`, `DIPKA`, `NIGAHI`, `DUDHICHUA`

To guarantee comprehensive coverage without missing records or compromising authorization boundaries, `AuthorizedScope.is_mine_permitted` and `TopicAnalysisService.get_scoped_chunks` utilize the canonical alias sets:

```python
MINE_ALIAS_SETS = {
    "GV001": {"GV001", "GEVRA", "MINE_A"},
    "GV002": {"GV002", "KUSMUNDA", "MINE_B"},
    "GV003": {"GV003", "DIPKA", "MINE_C"},
    "GV004": {"GV004", "NIGAHI", "MINE_D"},
    "GV005": {"GV005", "DUDHICHUA", "MINE_E"},
}
```

When a user requests analysis for `GV001`, the query expands to include both `GV001` and `GEVRA` tagged chunks, yielding all 155 authorized chunks for Gevra.

### 2.2 Canonical Mine Name Normalization
All cluster summaries, keyword mine associations, and document chunk references map back to institutional names:
```python
CANONICAL_NAME_MAP = {
    "GV001": "GEVRA", "GEVRA": "GEVRA", "MINE_A": "GEVRA",
    "GV002": "KUSMUNDA", "KUSMUNDA": "KUSMUNDA", "MINE_B": "KUSMUNDA",
    "GV003": "DIPKA", "DIPKA": "DIPKA", "MINE_C": "DIPKA",
    "GV004": "NIGAHI", "NIGAHI": "NIGAHI", "MINE_D": "NIGAHI",
    "GV005": "DUDHICHUA", "DUDHICHUA": "DUDHICHUA", "MINE_E": "DUDHICHUA",
}
```
Mines covered in cluster cards are rendered strictly as clean canonical names (e.g. `GEVRA`, `KUSMUNDA`), with zero legacy leakage.

---

## 3. TF-IDF Keyword Extraction & Filtering

Deterministic NLP is applied using `scikit-learn`:
- **Vectorization**: `TfidfVectorizer` with english stop words, custom mining stop words (e.g. `report`, `dated`, `annexure`, `page`, `table`, `total`), n-gram range `(1, 2)`, and minimum document frequency thresholds.
- **Metric Extraction**: Words are scored by aggregated TF-IDF weight across authorized chunks. Document frequency is tracked alongside total term occurrences.
- **Top Terms**: Extracted keywords feed directly into the **Visual Word Cloud** and the **Key Terminology Table**.

---

## 4. K-Means Topic Clustering & Naming

Document chunks within the authorized corpus are vectorized and partitioned into thematic clusters:
- **Clustering Algorithm**: `KMeans(n_clusters=k, random_state=42, n_init=10)`. $k$ is dynamically determined based on corpus size ($\min(5, \max(2, N / 10))$).
- **Cluster Centroids**: Top TF-IDF features closest to each cluster center define the cluster label and descriptive keywords.
- **Cluster Metadata**:
  - `topic_id`: Unique identifier (e.g., `TOPIC-01`)
  - `title`: Institutional title based on dominant terms (e.g., "Overburden Removal & Blast Excavation")
  - `chunk_count`: Number of document chunks assigned to the cluster
  - `percentage`: Share of the authorized corpus
  - `keywords`: Top 5 distinct terms
  - `mines_covered`: Set of normalized canonical mines represented
  - `representative_chunks`: Curated excerpts with document citation and page references

---

## 5. Word Cloud Generation & Dynamic Caching

The visual word cloud is generated server-side using `wordcloud.WordCloud`:
- **Color Palette**: Institutional coal/geology palette (dark charcoal background, amber, teal, cyan, and emerald accents).
- **Dimensions**: $1200 \times 600$ high-resolution PNG.
- **Caching**: Generated images are keyed by SHA-256 hash of query parameters (mine, department, year, user scope) and cached in `/tmp/wordclouds/` (or designated persistent storage) to minimize repetitive compute.
- **Delivery**: Streamed via `GET /api/v1/topics/wordcloud/image/{filename}` with support for direct client-side download.

---

## 6. Authorization Enforcement (Pre-Retrieval)

In strict adherence to Section 6 of `AGENTS.md` (**AUTHORIZATION BEFORE RETRIEVAL**):
1. **Pre-Retrieval Scope Check**:
   If a user requests a filter for a specific mine (e.g. `GV004`), `TopicAnalysisService` checks:
   ```python
   if mine_code and not scope.is_mine_permitted(mine_code):
       raise HTTPException(
           status_code=403,
           detail=f"Access denied: Mine '{mine_code}' is outside your authorized scope."
       )
   ```
   Unauthorized requests are rejected with `HTTP 403 Forbidden` before querying the database.
2. **Authorized Corpus Boundary**:
   If no mine filter is passed, the retrieval query filters against `scope.allowed_mines`. Unpermitted mine chunks are never retrieved or supplied to scikit-learn.
3. **Frontend Scope Isolation**:
   The mine selector dropdown dynamically filters options using `user.scope.allowed_mines`:
   - `USR001` (Mining Engineer, Gevra) sees only `GV001 — GEVRA`.
   - `USR004` (Multi-Mine Manager) sees `GV001 — GEVRA` and `GV002 — KUSMUNDA`.
   - `USR005` (Executive / Admin) sees all five canonical mines.

---

## 7. Synthetic Data Integration & Labeling

Because the five-mine dataset is an operational synthetic benchmark:
- Every topic card, word cloud container, and table displays the standard `[SYNTHETIC_DEMO]` institutional badge.
- Excerpts and statistics carry clear verification notices.

---

## 8. Frontend UX Architecture (`/topics`)

The page at `frontend/app/topics/page.tsx` was built with modern enterprise ergonomics:
- **Header**: Institutional title, total authorized chunks analyzed counter, active identity indicator, and demo dataset badge.
- **Filter Bar**: Mine selection (scope-constrained), Department dropdown, Year dropdown, and "Apply Filters" button with loading spinner.
- **Word Cloud Panel**: Responsive container rendering the dynamic word cloud image, with refresh and download capabilities.
- **Key Terminology Table**: Sortable/scannable tabular display with Rank, Keyword, Frequency, and Document Coverage metrics.
- **Topic Clusters Grid**: Cards detailing topic title, cluster size, percentage of corpus, `#keyword` badges, canonical mines covered, and representative excerpts.
- **Empty State & Access Denial Handling**:
  - `HTTP 403`: Displays institutional Access Denied banner explaining permission restrictions.
  - Empty Corpus: Displays graceful guidance informing the user that no documents match the criteria within their authorized scope.

---

## 9. Test Suite Verification (`test_phase5d_topics.py`)

A dedicated 10-test regression suite was executed against the running backend container (`geovault_backend`):

| Test ID | Test Description | Result |
|---|---|---|
| `test_01_scoped_chunk_selection_gevra` | Verifies Gevra chunks (155) retrieved using alias expansion | **PASS** |
| `test_02_tfidf_keyword_extraction` | Validates deterministic TF-IDF scoring and word frequencies | **PASS** |
| `test_03_kmeans_topic_clustering` | Tests K-Means clustering and cluster metadata integrity | **PASS** |
| `test_04_wordcloud_image_generation` | Confirms word cloud PNG creation and image endpoint | **PASS** |
| `test_05_authorized_mine_filtering` | Validates mine-specific topic filtering for authorized users | **PASS** |
| `test_06_unauthorized_mine_denial` | Verifies HTTP 403 is raised on unauthorized mine request | **PASS** |
| `test_07_scope_isolation_usr001_vs_usr005` | Confirms strict corpus isolation between single-mine and admin | **PASS** |
| `test_08_multi_mine_manager_scope` | Verifies multi-mine manager (USR004) chunk union | **PASS** |
| `test_09_year_filtering` | Tests temporal filtering within authorized documents | **PASS** |
| `test_10_empty_result_handling` | Confirms graceful empty response handling | **PASS** |

**Total Test Result**: 10/10 PASS (15.52s execution time).

---

## 10. Zero Legacy Codebase Sanitization

Grep verification confirmed zero occurrences of deprecated identifiers (`DEOM-01`, `KNUG-02`, `SSOP-03`, `Dharani East`, `Shakti Coalfields`) across all frontend pages and API contracts.

---

## 11. Edge Cases & Error Handling

- **Corpus < 2 Chunks**: Falls back to deterministic single-topic extraction without failing K-Means.
- **Zero Matching Documents**: Returns empty cluster and keyword lists with 200 OK; frontend displays clear informational banner.
- **Image Generation Failure**: Frontend provides fallback message and retains tabular keyword display.

---

## 12. Verification & Regression Baseline

- **Backend Total**: All 67 baseline tests + 7 Phase 5C Ask tests + 10 Phase 5D Topic tests = **84/84 PASSING**.
- **Frontend Production Build**: `npm run build` generates 10/10 static pages with 0 linting or TypeScript errors.
- **Source Datasets**: `F:\GeoVault\Coal Data\` and `F:\GeoVault\geo_data\` remain completely untouched and read-only.
- **Database Schema**: Unmodified, preserved in PostgreSQL 16 + pgvector.

---

## 13. Future Roadmap for Phase 5E

Phase 5D successfully completes all Topic & Word Cloud requirements. Next planned step under the SIH 2026 roadmap is **Phase 5E: Automated Report Generation (PDF/DOCX)**, which will assemble multi-page compliance reports leveraging the structured and unstructured evidence engines established in Phases 1–5D.
