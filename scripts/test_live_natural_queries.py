"""
GeoVault AI - Live HTTP Natural Query Verification
Tests POST /api/v1/intelligence/natural-query with:
- "What was DEOM-01 production in FY2024?"
- "Compare DEOM-01 and KNUG-02 production."
- "What geological issues were reported for DEOM-01?"
- "Why did production change?"
- "What conflicts exist in the data?"
- Unauthorized KNUG-02 query using USR001 (Must return 403 Forbidden)
"""

import sys
sys.path.insert(0, "/app")

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

print("=" * 80)
print("LIVE NATURAL LANGUAGE INTELLIGENCE API VERIFICATION")
print("=" * 80)

# 1. SQL Query (DEOM-01 FY2024)
q1 = "What was DEOM-01 production in FY2024?"
r1 = client.post("/api/v1/intelligence/natural-query", json={"query": q1}, headers={"X-User-Id": "USR001"})
print(f"\n[1] Query: '{q1}' (User: USR001)")
print("Status Code:", r1.status_code)
d1 = r1.json()
print("Route Selected:", d1["query_type"])
print("Validation Status:", d1["validation_status"])
print("Evidence Count:", len(d1["evidence"]))
print("Answer Snippet:", d1["answer"][:180] + "...")
assert r1.status_code == 200
assert d1["query_type"] == "SQL"
assert d1["validation_status"] == "VERIFIED"
assert "5.02" in d1["answer"] or (d1.get("structured_results") and "5.02" in str(d1["structured_results"]))

# 2. Analytics Comparison Query (DEOM-01 vs KNUG-02 by Manager USR004)
q2 = "Compare DEOM-01 and KNUG-02 production."
r2 = client.post("/api/v1/intelligence/natural-query", json={"query": q2}, headers={"X-User-Id": "USR004"})
print(f"\n[2] Query: '{q2}' (User: USR004)")
print("Status Code:", r2.status_code)
d2 = r2.json()
print("Route Selected:", d2["query_type"])
print("Validation Status:", d2["validation_status"])
print("Mines Compared:", [c["mine_code"] for c in d2["structured_results"]["analytics"]["comparisons"]])
print("Answer Snippet:", d2["answer"][:180] + "...")
assert r2.status_code == 200
assert d2["query_type"] == "ANALYTICS"
assert len(d2["structured_results"]["analytics"]["comparisons"]) == 2

# 3. RAG Query (Geological Issues)
q3 = "What geological issues were reported for DEOM-01?"
r3 = client.post("/api/v1/intelligence/natural-query", json={"query": q3}, headers={"X-User-Id": "USR001"})
print(f"\n[3] Query: '{q3}' (User: USR001)")
print("Status Code:", r3.status_code)
d3 = r3.json()
print("Route Selected:", d3["query_type"])
print("Evidence Count:", len(d3["evidence"]))
print("First Evidence Citation:", d3["evidence"][0]["citation"] if d3["evidence"] else "None")
print("Answer Snippet:", d3["answer"][:180] + "...")
assert r3.status_code == 200
assert d3["query_type"] == "RAG"
assert len(d3["evidence"]) > 0

# 4. Hybrid Query (Why did production change)
q4 = "Why did production change between 2023 and 2024 for DEOM-01?"
r4 = client.post("/api/v1/intelligence/natural-query", json={"query": q4}, headers={"X-User-Id": "USR001"})
print(f"\n[4] Query: '{q4}' (User: USR001)")
print("Status Code:", r4.status_code)
d4 = r4.json()
print("Route Selected:", d4["query_type"])
print("Facts Count:", len(d4["structured_results"]["facts"]) if d4["structured_results"] else 0)
print("Evidence Count:", len(d4["evidence"]))
print("Answer Snippet:", d4["answer"][:180] + "...")
assert r4.status_code == 200
assert d4["query_type"] == "HYBRID"

# 5. Conflict Surfacing Query
q5 = "What conflicts exist in the data for SSOP-03 in 2025?"
r5 = client.post("/api/v1/intelligence/natural-query", json={"query": q5}, headers={"X-User-Id": "USR005"})
print(f"\n[5] Query: '{q5}' (User: USR005)")
print("Status Code:", r5.status_code)
d5 = r5.json()
print("Validation Status:", d5["validation_status"])
print("Conflicts Detected:", len(d5["conflicts"]))
if d5["conflicts"]:
    print("Conflict ID:", d5["conflicts"][0]["conflict_id"])
print("Answer Snippet:", d5["answer"][:180] + "...")
assert r5.status_code == 200
assert d5["validation_status"] == "CONFLICT"
assert len(d5["conflicts"]) > 0

# 6. Security Denial Check: USR001 querying unauthorized mine KNUG-02
q6 = "What was KNUG-02 production in FY2024?"
r6 = client.post("/api/v1/intelligence/natural-query", json={"query": q6}, headers={"X-User-Id": "USR001"})
print(f"\n[6] Unauthorized Query: '{q6}' (User: USR001)")
print("Status Code:", r6.status_code)
print("Error Detail:", r6.json().get("detail"))
assert r6.status_code == 403
assert "Access Denied" in r6.json().get("detail")

print("\n" + "=" * 80)
print("ALL LIVE NATURAL LANGUAGE QUERIES & SECURITY CHECKS VERIFIED SUCCESSFULLY!")
print("=" * 80)
