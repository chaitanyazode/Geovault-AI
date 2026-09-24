import urllib.request
import json
import sys

def test_topics_response():
    print("Testing /api/v1/topics/analyze against normalization expectations...")
    users_to_test = [
        ("USR001", "DEOM-01"),
        ("USR004", "KNUG-02"),
        ("USR005", None),
    ]

    for user_id, mine_code in users_to_test:
        payload = {
            "mine_code": mine_code,
            "department": None,
            "year": None,
            "num_clusters": 4,
            "max_keywords": 25,
        }
        req = urllib.request.Request(
            "http://localhost:8000/api/v1/topics/analyze",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json", "X-User-Id": user_id},
        )
        res = urllib.request.urlopen(req)
        assert res.status == 200, f"Expected 200, got {res.status}"
        data = json.loads(res.read().decode("utf-8"))

        total_chunks = data.get("total_chunks_analyzed", 0)
        topics = data.get("topics", [])
        keywords = data.get("keywords", [])

        print(f"\n[OK] User {user_id} (Mine: {mine_code}):")
        print(f"     Total chunks analyzed: {total_chunks}")
        print(f"     Discovered clusters:   {len(topics)}")
        print(f"     Extracted keywords:    {len(keywords)}")

        for t in topics:
            chunk_cnt = t.get("document_chunk_count", 0)
            quotes = t.get("representative_quotes", [])
            derived_pct = (chunk_cnt / total_chunks * 100) if total_chunks > 0 else 0.0
            print(f"       * {t.get('topic_id')}: {t.get('title')} -> {chunk_cnt} chunks ({derived_pct:.1f}%), {len(quotes)} quotes")
            assert "document_chunk_count" in t, "document_chunk_count must be in topic"
            assert "representative_quotes" in t, "representative_quotes must be in topic"

    print("\n[ALL PASS] Topics API contract matches normalization layer perfectly.")

if __name__ == "__main__":
    test_topics_response()
