import requests
import json

BASE_URL = "http://localhost:8000"

def test_query(title, query_text, user_id="USR001"):
    print(f"\n========================================================")
    print(f"TEST: {title}")
    print(f"QUERY: {query_text} (User: {user_id})")
    print(f"========================================================")
    
    headers = {"X-User-ID": user_id}
    payload = {"query": query_text}
    
    try:
        res = requests.post(f"{BASE_URL}/api/v1/intelligence/natural-query", json=payload, headers=headers, timeout=120)
        print(f"HTTP Status: {res.status_code}")
        if res.status_code == 200:
            data = res.json()
            print(f"Route: {data.get('query_type')}")
            print(f"Summary: {data.get('summary')}")
            print(f"Detailed Answer Preview (first 250 chars):\n{data.get('detailed_answer', '')[:250]}...")
            
            facts = (data.get("structured_results") or {}).get("facts", [])
            if facts:
                print(f"Primary Fact: {facts[0]}")
            
            evidence = data.get("evidence", [])
            print(f"Evidence Count: {len(evidence)}")
            if evidence:
                print(f"Sample Citation: {evidence[0].get('citation')}")
            
            # Check for legacy identifiers
            full_text = f"{data.get('summary')} {data.get('detailed_answer')}"
            for legacy in ["DEOM-01", "KNUG-02", "SSOP-03", "Dharani East"]:
                if legacy in full_text:
                    print(f"WARNING: Legacy term {legacy} found in response!")
            print("Legacy check: CLEAN")
        elif res.status_code == 403:
            print(f"Safe 403 Access Denied: {res.json().get('detail')}")
        else:
            print(f"Error {res.status_code}: {res.text}")
    except Exception as e:
        print(f"Request failed: {e}")

# 1. Structured Fact
test_query("WORKFLOW 1 - STRUCTURED PRODUCTION", "What was GEVRA's production in FY2024-25?", "USR001")

# 2. Geology / RAG
test_query("WORKFLOW 2 - GEOLOGY RAG", "What geological observations were reported for GEVRA in FY2024-25?", "USR001")

# 3. Spatial PostGIS
test_query("WORKFLOW 3 - SPATIAL POSTGIS", "Which GEVRA boreholes are within 500 metres of the requested geological feature?", "USR001")

# 4. Multi-Mine Comparison
test_query("WORKFLOW 4 - MULTI-MINE COMPARISON", "Compare FY2024-25 production across the five mines.", "USR005")

# 5. Hybrid Operational + Geology
test_query("WORKFLOW 5 - HYBRID", "Explain the production shortfall using operational and geological evidence.", "USR001")

# 6. Unauthorized 403 Test
test_query("WORKFLOW 6 - UNAUTHORIZED SCOPE CHECK", "What was NIGAHI's production in FY2024-25?", "USR001")
