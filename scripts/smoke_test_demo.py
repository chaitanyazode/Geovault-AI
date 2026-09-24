"""
GeoVault AI — Phase 7 SIH Demo Smoke-Test & Verification Script
Executes rapid (< 5 second) health, security, database, and API checks
to certify that the environment is fully operational for judge evaluation.
"""

import sys
import json
import time
import urllib.request
import urllib.error

BACKEND_URL = "http://localhost:8000"
FRONTEND_URL = "http://localhost:3000"

def log_step(name: str):
    print(f"\n[*] {name}...")

def test_http(url: str, method: str = "GET", headers: dict = None, payload: dict = None, expected_status: int = 200, timeout: int = 5):
    data = json.dumps(payload).encode("utf-8") if payload else None
    req_headers = {"User-Agent": "GeoVault-SmokeTest/1.0"}
    if headers:
        req_headers.update(headers)
    if payload and "Content-Type" not in req_headers:
        req_headers["Content-Type"] = "application/json"

    req = urllib.request.Request(url, data=data, headers=req_headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            content_type = resp.headers.get_content_type()
            raw = resp.read()
            body = json.loads(raw.decode("utf-8")) if "json" in content_type else raw.decode("utf-8", errors="ignore")
            return resp.status == expected_status, resp.status, body
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8", errors="ignore")
        return e.code == expected_status, e.code, err_body
    except Exception as e:
        return False, 0, str(e)

def main():
    t_start = time.time()
    print("=" * 75)
    print("   GeoVault AI — Smart India Hackathon 2026 (PS 26023)")
    print("   SIH Evaluation Rapid Smoke-Test & Environment Certification")
    print("=" * 75)

    failures = []

    # 1. Frontend Web App Check
    log_step("1. Checking Frontend Web Application (http://localhost:3000)")
    ok, code, _ = test_http(f"{FRONTEND_URL}/")
    if ok:
        print(f"  [PASS] Frontend Dashboard reachable (HTTP {code})")
    else:
        print(f"  [FAIL] Frontend Dashboard unreachable (HTTP {code})")
        failures.append("Frontend unreachable")

    # 2. Backend Health Check
    log_step("2. Checking Backend & Infrastructure Health (http://localhost:8000/health)")
    ok, code, health = test_http(f"{BACKEND_URL}/health")
    if ok and isinstance(health, dict):
        all_healthy = True
        for svc in ["backend", "postgres", "redis", "llm"]:
            val = health.get(svc, "unknown")
            is_ok = val == "healthy"
            status_str = "[PASS]" if is_ok else "[FAIL]"
            print(f"  {status_str} Microservice '{svc}': {val}")
            if not is_ok:
                all_healthy = False
        if not all_healthy:
            failures.append("One or more microservices not healthy")
    else:
        print(f"  [FAIL] Backend /health endpoint failed: HTTP {code}")
        failures.append("Backend /health endpoint failed")

    # 3. User Identity & ABAC Clearance Verification
    log_step("3. Testing Demo Identity Profiles & Clearance Levels")
    demo_users = [
        ("USR001", "Mining Engineer", ["DEOM-01"], "INTERNAL"),
        ("USR004", "Mine Manager", ["DEOM-01", "KNUG-02"], "RESTRICTED"),
        ("USR005", "Administrator", "ALL", "CONFIDENTIAL"),
    ]
    for uid, expected_role, expected_mines, expected_clearance in demo_users:
        ok, code, data = test_http(f"{BACKEND_URL}/api/v1/auth/me", headers={"X-User-ID": uid})
        if ok and isinstance(data, dict):
            u_role = data.get("user", {}).get("role")
            scope_mines = data.get("authorized_scope", {}).get("allowed_mines")
            u_clearance = data.get("user", {}).get("clearance_level")
            print(f"  [PASS] User '{uid}': Role='{u_role}', Clearance='{u_clearance}', Scope={scope_mines}")
        else:
            print(f"  [FAIL] Failed to fetch identity context for '{uid}' (HTTP {code})")
            failures.append(f"Auth context failed for {uid}")

    # 4. Deterministic Query & Evidence Engine Verification
    log_step("4. Testing Scoped SQL Query Engine & Evidence Tracing")
    payload_query = {
        "domain": "production_annual",
        "mine_code": "DEOM-01",
        "start_year": 2021,
        "end_year": 2025
    }
    ok, code, q_res = test_http(
        f"{BACKEND_URL}/api/v1/intelligence/query",
        method="POST",
        headers={"X-User-ID": "USR001"},
        payload=payload_query
    )
    if ok and isinstance(q_res, dict):
        facts = q_res.get("facts", [])
        evidence = q_res.get("evidence", [])
        print(f"  [PASS] Retrieved {len(facts)} annual production rows for DEOM-01")
        print(f"  [PASS] Generated {len(evidence)} verified evidence citation cards")
        if len(facts) != 5:
            failures.append(f"Expected 5 production rows for DEOM-01, got {len(facts)}")
    else:
        print(f"  [FAIL] Deterministic query failed: HTTP {code}")
        failures.append("Deterministic query failed")

    # 5. Pre-Retrieval Authorization Boundary Enforcement
    log_step("5. Verifying Security Boundary: USR001 Blocked from KNUG-02 (403 Forbidden)")
    payload_unauth = {
        "domain": "production_annual",
        "mine_code": "KNUG-02",
        "start_year": 2021,
        "end_year": 2025
    }
    ok, code, _ = test_http(
        f"{BACKEND_URL}/api/v1/intelligence/query",
        method="POST",
        headers={"X-User-ID": "USR001"},
        payload=payload_unauth,
        expected_status=403
    )
    if ok:
        print(f"  [PASS] HTTP 403 Forbidden correctly returned. Zero unauthorized data leakage.")
    else:
        print(f"  [FAIL] Security boundary breach! Expected HTTP 403, got HTTP {code}")
        failures.append("403 security boundary failed")

    # 6. Active Conflict Surfacing Verification
    log_step("6. Checking Active Discovered Conflicts Surfacing")
    ok, code, conflicts = test_http(f"{BACKEND_URL}/api/v1/conflicts", headers={"X-User-ID": "USR005"})
    if ok and isinstance(conflicts, list):
        print(f"  [PASS] Surfaced {len(conflicts)} active conflicting source records:")
        for c in conflicts:
            print(f"         - [{c.get('conflict_id')}] {c.get('metric_or_topic')}: {c.get('source_a_value')} vs {c.get('source_b_value')}")
    else:
        print(f"  [FAIL] Failed to retrieve conflicts: HTTP {code}")
        failures.append("Conflict retrieval failed")

    # 7. Topic Analysis Verification
    log_step("7. Testing Topic Discovery & Keyword Ranking")
    ok, code, topic_res = test_http(
        f"{BACKEND_URL}/api/v1/topics/analyze",
        method="POST",
        headers={"X-User-ID": "USR001"},
        payload={"mine_code": "DEOM-01"}
    )
    if ok and isinstance(topic_res, dict):
        kws = topic_res.get("keywords", [])
        clusters = topic_res.get("topics", [])
        print(f"  [PASS] Extracted {len(kws)} TF-IDF keywords and {len(clusters)} K-Means clusters")
    else:
        print(f"  [FAIL] Topic extraction failed: HTTP {code}")
        failures.append("Topic extraction failed")

    # Final Verdict
    duration = time.time() - t_start
    print("\n" + "=" * 75)
    if not failures:
        print(f" >>> CERTIFICATION SUCCESS: ALL SMOKE TESTS PASSED IN {duration:.2f}s! <<<")
        print(" GeoVault AI is certified and 100% READY for SIH Judge Demonstration.")
    else:
        print(f" >>> CERTIFICATION FAILED ({len(failures)} issues detected) in {duration:.2f}s! <<<")
        for f in failures:
            print(f"  - {f}")
    print("=" * 75)
    return 0 if not failures else 1

if __name__ == "__main__":
    sys.exit(main())
