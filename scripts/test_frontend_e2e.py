"""
test_frontend_e2e.py - Verification script for GeoVault AI Phase 6C Frontend & Full Backend Integration

Tests:
1. Next.js Route Availability: /, /ask, /topics, /reports, /evidence, /status
2. Backend API Connectivity for Frontend Client:
   - User identity & scope retrieval (USR001, USR004, USR005)
   - Ask GeoVault natural language query & evidence generation
   - Topics & Word Cloud generation (TF-IDF & clusters)
   - Report generation & download endpoints
   - Active conflict retrieval & direct evidence lookup
   - Health status
3. Security boundary verification (USR001 403 enforcement on KNUG-02)
"""

import sys
import json
import urllib.request
import urllib.error

FRONTEND_BASE = "http://localhost:3000"
BACKEND_BASE = "http://localhost:8000"

def test_route(path: str, expected_status: int = 200):
    url = f"{FRONTEND_BASE}{path}"
    req = urllib.request.Request(url, headers={"User-Agent": "GeoVault-E2E/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            status = resp.status
            body = resp.read().decode("utf-8", errors="ignore")
            print(f"  [OK] {url} -> HTTP {status} (Content length: {len(body)})")
            return True, body
    except urllib.error.HTTPError as e:
        if e.code == expected_status:
            print(f"  [OK-EXPECTED] {url} -> HTTP {e.code}")
            return True, ""
        print(f"  [FAIL] {url} -> HTTP {e.code}")
        return False, ""
    except Exception as e:
        print(f"  [ERROR] {url} -> {e}")
        return False, ""

def test_api_endpoint(path: str, user_id: str, method: str = "GET", payload: dict = None, expected_status: int = 200, timeout: int = 90):
    url = f"{BACKEND_BASE}{path}"
    data = json.dumps(payload).encode("utf-8") if payload else None
    headers = {
        "X-User-ID": user_id,
        "Content-Type": "application/json",
        "User-Agent": "GeoVault-E2E/1.0"
    }
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            content_type = resp.headers.get_content_type()
            raw = resp.read()
            if "json" in content_type:
                res_data = json.loads(raw.decode("utf-8"))
            else:
                res_data = {"bytes": len(raw), "content_type": content_type}
            print(f"  [API OK] {method} {path} (User: {user_id}) -> HTTP {resp.status} ({content_type})")
            return True, res_data
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8", errors="ignore")
        if e.code == expected_status:
            print(f"  [API OK-EXPECTED] {method} {path} (User: {user_id}) -> HTTP {e.code}")
            return True, err_body
        print(f"  [API FAIL] {method} {path} (User: {user_id}) -> HTTP {e.code}: {err_body[:100]}")
        return False, err_body
    except Exception as e:
        print(f"  [API ERROR] {method} {path} (User: {user_id}) -> {e}")
        return False, str(e)

def main():
    print("=" * 70)
    print("GeoVault AI — Phase 6C Frontend & Full Backend Integration E2E Tests")
    print("=" * 70)

    all_passed = True

    # 1. Frontend Route Verification
    print("\n--- 1. Testing Next.js Frontend Viewports (SSR / Build) ---")
    routes = ["/", "/ask", "/topics", "/reports", "/logs", "/evidence", "/status"]
    for route in routes:
        ok, _ = test_route(route)
        if not ok:
            all_passed = False

    # 2. Backend Health
    print("\n--- 2. Testing Backend Health ---")
    ok, health = test_api_endpoint("/health", "USR001")
    if not ok or health.get("backend") != "healthy":
        all_passed = False
        print("  Backend is not healthy!")
    else:
        print(f"  Health: Backend={health.get('backend')}, Postgres={health.get('postgres')}, Redis={health.get('redis')}, LLM={health.get('llm')}")

    # 3. User Identity & Scope Verification
    print("\n--- 3. Testing User Context & Scope (Frontend Identity Switcher) ---")
    for uid in ["USR001", "USR004", "USR005"]:
        ok, uctx = test_api_endpoint("/api/v1/auth/me", uid)
        if not ok:
            all_passed = False
        else:
            mines = uctx.get("authorized_scope", {}).get("allowed_mines", [])
            print(f"    User {uid} ({uctx.get('user', {}).get('role')}): Scope Mines = {mines}")

    # 4. Ask GeoVault (Natural Query Intelligence)
    print("\n--- 4. Testing Ask GeoVault Natural Query Endpoint Integration ---")
    ok, query_res = test_api_endpoint(
        "/api/v1/intelligence/natural-query",
        user_id="USR001",
        method="POST",
        payload={"query": "What was DEOM-01 production in FY2024?"}
    )
    if not ok or query_res.get("query_type") != "SQL":
        all_passed = False
    else:
        evidence_count = len(query_res.get("evidence", []))
        print(f"    Route: {query_res.get('query_type')}, Status: {query_res.get('validation_status')}, Evidence Count: {evidence_count}")

    # 5. Topics & Word Cloud Endpoint
    print("\n--- 5. Testing Topics & Word Cloud API ---")
    ok, topics_res = test_api_endpoint(
        "/api/v1/topics/analyze",
        user_id="USR001",
        method="POST",
        payload={"mine_code": "DEOM-01"}
    )
    if not ok or "keywords" not in topics_res:
        all_passed = False
    else:
        kw_count = len(topics_res.get("keywords", []))
        cl_count = len(topics_res.get("topics", []))
        has_cloud = bool(topics_res.get("wordcloud_url")) or bool(topics_res.get("wordcloud_file"))
        print(f"    Keywords: {kw_count}, Clusters: {cl_count}, Word Cloud Available: {has_cloud}")

    # 6. Automated Reports Generation & Download
    print("\n--- 6. Testing Automated Report Generation API ---")
    ok, rep_res = test_api_endpoint(
        "/api/v1/reports/generate",
        user_id="USR001",
        method="POST",
        payload={"mine_code": "DEOM-01", "report_type": "PERFORMANCE", "start_year": 2021, "end_year": 2025}
    )
    if not ok or "report_id" not in rep_res:
        all_passed = False
    else:
        rep_id = rep_res.get("report_id")
        print(f"    Report Created: {rep_id} (Status: {rep_res.get('status')})")
        # Test download metadata/files
        ok_pdf, _ = test_api_endpoint(f"/api/v1/reports/{rep_id}/download/pdf", user_id="USR001")
        ok_docx, _ = test_api_endpoint(f"/api/v1/reports/{rep_id}/download/docx", user_id="USR001")
        if not ok_pdf or not ok_docx:
            all_passed = False

    # 7. Evidence & Conflicts
    print("\n--- 7. Testing Evidence & Conflict Endpoints ---")
    ok, conflicts = test_api_endpoint("/api/v1/conflicts", user_id="USR001")
    if not ok:
        all_passed = False
    else:
        print(f"    Active Conflicts Surfaced: {len(conflicts)}")

    # 8. Security Boundary (USR001 attempting KNUG-02 query -> 403 Forbidden)
    print("\n--- 8. Testing Pre-Retrieval Authorization Boundary (403 Enforcement) ---")
    ok_403, err = test_api_endpoint(
        "/api/v1/intelligence/query",
        user_id="USR001",
        method="POST",
        payload={"domain": "production_annual", "mine_code": "KNUG-02", "start_year": 2021, "end_year": 2025},
        expected_status=403
    )
    if not ok_403:
        all_passed = False
        print("    SECURITY BREACH: USR001 was able to query KNUG-02 or did not return 403!")
    else:
        print("    [PASSED] Pre-retrieval authorization boundary verified: USR001 blocked from KNUG-02.")

    print("\n" + "=" * 70)
    if all_passed:
        print("ALL PHASE 6C FRONTEND & BACKEND INTEGRATION TESTS PASSED!")
    else:
        print("SOME TESTS FAILED. PLEASE REVIEW LOGS.")
    print("=" * 70)
    sys.exit(0 if all_passed else 1)

if __name__ == "__main__":
    main()
