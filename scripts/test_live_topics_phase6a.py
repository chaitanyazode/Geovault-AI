"""
GeoVault AI - Phase 6A Live End-to-End Topic Identification & Word Cloud Verification
Executes live API tests via FastAPI TestClient against:
1. POST /api/v1/topics/analyze for USR001 (DEOM-01 scoped)
2. GET /api/v1/topics/keywords for USR001
3. GET /api/v1/topics/wordcloud for USR001
4. GET /api/v1/topics/wordcloud/image/{filename} verifying binary PNG retrieval
5. POST /api/v1/topics/analyze for USR004 with mine_code="KNUG-02"
6. POST /api/v1/topics/analyze for USR001 with mine_code="KNUG-02" -> 403 Forbidden verification
7. POST /api/v1/intelligence/natural-query with topic question -> TOPIC route verification
"""

import sys
sys.path.insert(0, "/app")

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

print("=" * 80)
print("PHASE 6A LIVE TOPIC IDENTIFICATION & WORD CLOUD VERIFICATION")
print("=" * 80)

# 1. Full Topic Analysis for USR001 (Mining Engineer, DEOM-01)
print("\n[1] Testing POST /api/v1/topics/analyze (User: USR001, Mine: DEOM-01)")
r1 = client.post(
    "/api/v1/topics/analyze",
    json={"mine_code": "DEOM-01", "num_topics": 3, "top_keywords": 15},
    headers={"X-User-Id": "USR001"}
)
print("Status Code:", r1.status_code)
assert r1.status_code == 200
d1 = r1.json()
print("Chunks Analyzed:", d1["total_chunks_analyzed"])
print("Keywords Extracted:", len(d1["keywords"]))
print("Top 5 Keywords:")
for kw in d1["keywords"][:5]:
    print(f"  - {kw['keyword']}: freq={kw['frequency']}, score={kw['tfidf_score']:.4f}")
print("Topics Identified:")
for top in d1["topics"]:
    c_count = top.get("document_chunk_count", top.get("chunk_count", 0))
    kws = top.get("top_keywords", top.get("keywords", []))
    print(f"  * [{top['title']}] ({c_count} chunks) -> {top['description']}")
    print(f"    Keywords: {', '.join(kws)}")
print("Word Cloud Image URL:", d1.get("wordcloud_url"))
print("Processing Time:", f"{d1['processing_time_ms']:.2f} ms")


# 2. Keywords Endpoint for USR001
print("\n[2] Testing GET /api/v1/topics/keywords (User: USR001)")
r2 = client.get(
    "/api/v1/topics/keywords?top_n=10",
    headers={"X-User-Id": "USR001"}
)
print("Status Code:", r2.status_code)
assert r2.status_code == 200
d2 = r2.json()
kws2 = d2.get("keywords", [])
print(f"Extracted {len(kws2)} keywords. Top 3:", [k["keyword"] for k in kws2[:3]])


# 3. Dedicated WordCloud Endpoint
print("\n[3] Testing GET /api/v1/topics/wordcloud (User: USR001)")
r3 = client.get(
    "/api/v1/topics/wordcloud?top_n=20",
    headers={"X-User-Id": "USR001"}
)
print("Status Code:", r3.status_code)
assert r3.status_code == 200
d3 = r3.json()
url_val = d3.get("wordcloud_url") or d3.get("image_url")
path_val = d3.get("wordcloud_path") or d3.get("image_path")

print("WordCloud Image URL:", url_val)
print("WordCloud File Path:", path_val)

# 4. Binary Image Retrieval
filename = url_val.split("/")[-1]

print(f"\n[4] Testing GET /api/v1/topics/wordcloud/image/{filename} (Binary PNG stream)")
r4 = client.get(f"/api/v1/topics/wordcloud/image/{filename}")
print("Status Code:", r4.status_code)
print("Content-Type:", r4.headers.get("content-type"))
print("Image Byte Size:", len(r4.content))
assert r4.status_code == 200
assert r4.headers.get("content-type") == "image/png"
assert len(r4.content) > 1000

# 5. Mine Manager (USR004) analyzing KNUG-02
print("\n[5] Testing POST /api/v1/topics/analyze (User: USR004, Mine: KNUG-02)")
r5 = client.post(
    "/api/v1/topics/analyze",
    json={"mine_code": "KNUG-02", "num_topics": 3, "top_keywords": 10},
    headers={"X-User-Id": "USR004"}
)
print("Status Code:", r5.status_code)
assert r5.status_code == 200
d5 = r5.json()
print(f"USR004 successfully analyzed KNUG-02: {d5['total_chunks_analyzed']} chunks analyzed.")

# 6. Security Boundary: USR001 attempting to query KNUG-02 topics (Must be 403)
print("\n[6] Testing Security Denial: USR001 attempting to request KNUG-02 topics")
r6 = client.post(
    "/api/v1/topics/analyze",
    json={"mine_code": "KNUG-02"},
    headers={"X-User-Id": "USR001"}
)
print("Status Code:", r6.status_code)
print("Detail:", r6.json().get("detail"))
assert r6.status_code == 403
assert "Access Denied" in r6.json().get("detail")
print(">>> Security Denial successfully verified! (Pre-retrieval scope enforcement)")

# 7. Unified AI Orchestrator TOPIC route integration
print("\n[7] Testing Natural Language Topic Query through UnifiedAIOrchestrator")
q7 = "What are the major topics and recurring terminology in mine reports?"
r7 = client.post(
    "/api/v1/intelligence/natural-query",
    json={"query": q7},
    headers={"X-User-Id": "USR001"}
)
print("Status Code:", r7.status_code)
assert r7.status_code == 200
d7 = r7.json()
print("Route Selected:", d7["query_type"])
print("Validation Status:", d7["validation_status"])
print("WordCloud URL in Metadata:", d7.get("processing_metadata", {}).get("wordcloud_url"))
print("Answer Snippet:\n", d7["answer"][:300] + "...\n")
assert d7["query_type"] == "TOPIC"
assert len(d7["answer"]) > 0
assert d7.get("processing_metadata", {}).get("wordcloud_url") is not None


print("=" * 80)
print("ALL PHASE 6A LIVE VERIFICATIONS PASSED SUCCESSFULLY!")
print("=" * 80)
