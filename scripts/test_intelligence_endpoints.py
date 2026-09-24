"""
GeoVault AI - Intelligence API Endpoints Verification
Tests HTTP endpoints via FastAPI TestClient:
- POST /api/v1/intelligence/query
- POST /api/v1/intelligence/analytics
- POST /api/v1/intelligence/compare
- Conflict surfacing & Security boundary enforcement
"""

import sys
sys.path.insert(0, "/app")
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

print("=" * 80)
print("TESTING FASTAPI INTELLIGENCE & ANALYTICS HTTP ENDPOINTS")
print("=" * 80)

# 1. Test POST /api/v1/intelligence/query as USR001 (DEOM-01 FY2024)
res1 = client.post(
    "/api/v1/intelligence/query",
    json={"domain": "production_annual", "mine_code": "DEOM-01", "year": 2024},
    headers={"X-User-Id": "USR001"},
)
print("\n--- 1. Query API (DEOM-01 FY2024) ---")
print("HTTP Status Code:", res1.status_code)
d1 = res1.json()
print("Domain:", d1["domain"])
print("Facts Count:", len(d1["facts"]))
print("Fact Actual MT:", d1["facts"][0]["actual_production_mt"])
print("Evidence Count:", len(d1["evidence"]))
print("Evidence ID:", d1["evidence"][0]["evidence_id"])
print("Evidence Snippet:", d1["evidence"][0]["snippet"])
print("Validation Evidence Status:", d1["validation"]["evidence_status"])
assert res1.status_code == 200
assert float(d1["facts"][0]["actual_production_mt"]) == 5.02
assert d1["validation"]["evidence_status"] == "VERIFIED"

# 2. Test POST /api/v1/intelligence/analytics as USR001 (5-year trend)
res2 = client.post(
    "/api/v1/intelligence/analytics",
    json={
        "operation": "trend",
        "domain": "production_annual",
        "metric": "actual_production_mt",
        "mine_code": "DEOM-01",
    },
    headers={"X-User-Id": "USR001"},
)
print("\n--- 2. Analytics API (DEOM-01 5-Year Trend) ---")
print("HTTP Status Code:", res2.status_code)
d2 = res2.json()
print("Total 5-Year MT:", d2["analytics"]["total"])
print("Average MT:", d2["analytics"]["average"])
print("Trajectory:", d2["analytics"]["trend"]["direction"])
print("Net Change MT:", d2["analytics"]["trend"]["net_change"])
print("Net Change Pct:", d2["analytics"]["trend"]["net_change_pct"], "%")
assert res2.status_code == 200
assert float(d2["analytics"]["total"]) == 23.69
assert d2["analytics"]["trend"]["direction"] == "UPWARD"

# 3. Test POST /api/v1/intelligence/compare as USR004 (Manager comparing DEOM-01 vs KNUG-02)
res3 = client.post(
    "/api/v1/intelligence/compare",
    json={
        "mine_codes": ["DEOM-01", "KNUG-02"],
        "start_year": 2021,
        "end_year": 2025,
    },
    headers={"X-User-Id": "USR004"},
)
print("\n--- 3. Compare API (USR004: DEOM-01 vs KNUG-02) ---")
print("HTTP Status Code:", res3.status_code)
d3 = res3.json()
for comp in d3["analytics"]["comparisons"]:
    print(f"Mine: {comp['mine_code']} ({comp['mine_name']}) - Total: {comp['total_production_mt']} MT, Avg: {comp['avg_annual_production_mt']} MT, Achievement: {comp['achievement_pct']}%")
assert res3.status_code == 200
assert len(d3["analytics"]["comparisons"]) == 2

# 4. Test Conflict detection on SSOP-03 FY2025 as USR005
res4 = client.post(
    "/api/v1/intelligence/query",
    json={"domain": "dispatch_summary", "mine_code": "SSOP-03", "year": 2025},
    headers={"X-User-Id": "USR005"},
)
print("\n--- 4. Conflict Surfacing API (SSOP-03 FY2025 Logistics) ---")
print("HTTP Status Code:", res4.status_code)
d4 = res4.json()
print("SSOP-03 Validation Status:", d4["validation"]["evidence_status"])
print("Conflicts Detected Count:", len(d4["validation"]["conflicts_detected"]))
if d4["validation"]["conflicts_detected"]:
    c = d4["validation"]["conflicts_detected"][0]
    print(f"Conflict ID: {c['conflict_id']}")
    print(f"Source A ({c['source_a_type']}): {c['source_a_value']}")
    print(f"Source B ({c['source_b_type']}): {c['source_b_value']}")
    print(f"Resolution Policy: {c['resolution_policy']}")
assert res4.status_code == 200
assert d4["validation"]["evidence_status"] == "CONFLICT"
assert len(d4["validation"]["conflicts_detected"]) == 1

# 5. Verify security: USR001 attempting to compare with unauthorized mine KNUG-02
res5 = client.post(
    "/api/v1/intelligence/compare",
    json={
        "mine_codes": ["DEOM-01", "KNUG-02"],
        "start_year": 2021,
        "end_year": 2025,
    },
    headers={"X-User-Id": "USR001"},
)
print("\n--- 5. Security Denial Check (USR001 accessing KNUG-02) ---")
print("HTTP Status Code:", res5.status_code)
print("Error Message:", res5.json().get("detail"))
assert res5.status_code == 403
assert "Access Denied" in res5.json().get("detail")

print("\n" + "=" * 80)
print("ALL INTELLIGENCE API ENDPOINTS & SECURITY CHECKS VERIFIED SUCCESSFULLY!")
print("=" * 80)
