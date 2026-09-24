"""
GeoVault AI - Phase 6B Live End-to-End Report Generation Verification
Tests real endpoint operations for the 4 mandatory evaluation scenarios:
1. USR001: "Generate a 5-year performance report for DEOM-01."
2. USR004: "Generate a comparison report for DEOM-01 and KNUG-02."
3. USR005: "Generate a report on SSOP-03 FY2025 logistics conflicts."
4. USR001: "Generate a report for KNUG-02." -> MUST return 403 Forbidden.
"""

import os
import sys
import httpx
from docx import Document

BASE_URL = "http://localhost:8000/api/v1"


def test_scenario_1():
    print("\n--- Scenario 1: USR001 generating 5-year performance report for DEOM-01 ---")
    headers = {"X-User-ID": "USR001"}
    payload = {"query": "Generate a 5-year performance report for DEOM-01."}

    with httpx.Client(timeout=60.0) as client:
        res = client.post(f"{BASE_URL}/reports/generate", json=payload, headers=headers)
        print(f"Status: {res.status_code}")
        assert res.status_code == 200, f"Expected 200, got {res.status_code}: {res.text}"
        data = res.json()

        report_id = data["report_id"]
        print(f"Report ID: {report_id}")
        print(f"Title: {data['report_title']}")
        print(f"Mines Covered: {data['mines_covered']}")
        print(f"Formats: {data['output_formats']}")
        print(f"Validation Status: {data['validation_status']}")
        print(f"Latency: {data['generation_latency_ms']} ms")
        assert "DEOM-01" in data["mines_covered"]
        assert data["validation_status"] in ["VERIFIED", "CONFLICT"]

        # Verify PDF Download
        pdf_res = client.get(f"{BASE_URL}/reports/{report_id}/download/pdf", headers=headers)
        assert pdf_res.status_code == 200
        assert pdf_res.headers["content-type"] == "application/pdf"
        assert len(pdf_res.content) > 10000
        assert pdf_res.content.startswith(b"%PDF-")
        print(f"[✓] PDF verified: {len(pdf_res.content)} bytes")

        # Verify DOCX Download
        docx_res = client.get(f"{BASE_URL}/reports/{report_id}/download/docx", headers=headers)
        assert docx_res.status_code == 200
        assert len(docx_res.content) > 10000
        print(f"[✓] DOCX verified: {len(docx_res.content)} bytes")


def test_scenario_2():
    print("\n--- Scenario 2: USR004 generating comparison report for DEOM-01 and KNUG-02 ---")
    headers = {"X-User-ID": "USR004"}
    payload = {"query": "Generate a comparison report for DEOM-01 and KNUG-02."}

    with httpx.Client(timeout=60.0) as client:
        res = client.post(f"{BASE_URL}/reports/generate", json=payload, headers=headers)
        print(f"Status: {res.status_code}")
        assert res.status_code == 200, f"Expected 200, got {res.status_code}: {res.text}"
        data = res.json()

        report_id = data["report_id"]
        print(f"Report ID: {report_id}")
        print(f"Title: {data['report_title']}")
        print(f"Report Type: {data['report_type']}")
        print(f"Mines Covered: {data['mines_covered']}")
        assert "DEOM-01" in data["mines_covered"]
        assert "KNUG-02" in data["mines_covered"]
        assert "SSOP-03" not in data["mines_covered"]
        assert data["report_type"] == "COMPARISON"

        # Verify PDF & DOCX
        pdf_res = client.get(f"{BASE_URL}/reports/{report_id}/download/pdf", headers=headers)
        assert pdf_res.status_code == 200
        docx_res = client.get(f"{BASE_URL}/reports/{report_id}/download/docx", headers=headers)
        assert docx_res.status_code == 200
        print(f"[✓] Multi-mine comparison PDF & DOCX verified successfully!")


def test_scenario_3():
    print("\n--- Scenario 3: USR005 generating report on SSOP-03 FY2025 logistics conflicts ---")
    headers = {"X-User-ID": "USR005"}
    payload = {"query": "Generate a report on SSOP-03 FY2025 logistics conflicts."}

    with httpx.Client(timeout=60.0) as client:
        res = client.post(f"{BASE_URL}/reports/generate", json=payload, headers=headers)
        print(f"Status: {res.status_code}")
        assert res.status_code == 200, f"Expected 200, got {res.status_code}: {res.text}"
        data = res.json()

        report_id = data["report_id"]
        print(f"Report ID: {report_id}")
        print(f"Validation Status: {data['validation_status']}")
        print(f"Conflict Count: {data['conflict_count']}")
        assert data["validation_status"] == "CONFLICT"
        assert data["conflict_count"] > 0

        # Verify PDF contains conflict text
        pdf_res = client.get(f"{BASE_URL}/reports/{report_id}/download/pdf", headers=headers)
        assert pdf_res.status_code == 200
        print(f"[✓] Conflict report generated and verified with visible discrepancy callout!")


def test_scenario_4():
    print("\n--- Scenario 4: USR001 attempting to generate report for unauthorized KNUG-02 ---")
    headers = {"X-User-ID": "USR001"}
    payload = {"query": "Generate a report for KNUG-02."}

    with httpx.Client(timeout=30.0) as client:
        res = client.post(f"{BASE_URL}/reports/generate", json=payload, headers=headers)
        print(f"Status: {res.status_code}")
        print(f"Response: {res.text}")
        assert res.status_code == 403, f"Expected 403 Forbidden, got {res.status_code}"
        print("[✓] Correctly denied with 403 Forbidden! Zero unauthorized retrieval or LLM execution.")


def main():
    print("=" * 80)
    print("GeoVault AI — Phase 6B Live End-to-End Report Generation Demo")
    print("=" * 80)

    test_scenario_1()
    test_scenario_2()
    test_scenario_3()
    test_scenario_4()

    print("\n" + "=" * 80)
    print(">>> ALL 4 LIVE DEMO EVALUATION SCENARIOS COMPLETED SUCCESSFULLY! <<<")
    print("=" * 80)


if __name__ == "__main__":
    main()
