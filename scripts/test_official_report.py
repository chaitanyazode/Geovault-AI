"""
Comprehensive Verification Script for GeoVault AI Official-Style 3-4 Page Report Generator
Verifies:
1. Local image assets in images/
2. API report generation with DEOM-01 FY2024
3. PDF download & page count verification (target 3-4 pages)
4. Visual page inspection (renders PNG of each PDF page)
5. DOCX download verification
6. Evidence drawer resolution & highlighting endpoints
7. Pre-retrieval authorization enforcement (HTTP 403)
"""

import os
import sys
import requests

def run_verification():
    print("============================================================")
    print("GEOVAULT AI — OFFICIAL-STYLE 3-4 PAGE REPORT GENERATION TEST")
    print("============================================================")

    # 1. Local Image Assets
    print("\n--- STEP 1: Verify Local Image Assets in images/ ---")
    img_dir = "images"
    assert os.path.exists(img_dir), "images/ directory missing!"
    files = sorted(os.listdir(img_dir))
    print(f"Files in images/: {files}")
    assert "Ministry of coal.png" in files, "Ministry of coal.png missing!"
    assert "coal india.jpg" in files, "coal india.jpg missing!"
    print("PASS: Local image assets confirmed.")

    # 2. Generate Report via API
    print("\n--- STEP 2: Generate Official Performance Report ---")
    base_url = "http://localhost:8000/api/v1"
    headers = {"X-User-ID": "USR005"} # Administrator
    
    payload = {
        "query": "Generate a detailed annual performance report for DEOM-01 for FY2024-25 covering production, geological conditions, safety, transportation, key issues and recommendations.",
        "mine_code": "DEOM-01",
        "start_year": 2021,
        "end_year": 2025,
        "include_charts": True,
        "formats": ["PDF", "DOCX"]
    }

    resp = requests.post(f"{base_url}/reports/generate", json=payload, headers=headers, timeout=90)
    print(f"POST /reports/generate -> HTTP {resp.status_code}")
    assert resp.status_code == 200, f"Report generation failed: {resp.text}"
    report_data = resp.json()
    report_id = report_data["report_id"]
    print(f"Report ID: {report_id}")
    print(f"Title: {report_data.get('report_title')}")
    print(f"Period: {report_data.get('reporting_period')}")
    print(f"Validation Status: {report_data.get('validation_status')}")
    print(f"Evidence Count: {report_data.get('evidence_count')}")

    # 3. Download PDF & Check Page Count
    print("\n--- STEP 3: Download & Inspect Generated PDF ---")
    pdf_url = f"{base_url}/reports/{report_id}/download/pdf"
    pdf_resp = requests.get(pdf_url, headers=headers, timeout=20)
    print(f"GET {pdf_url} -> HTTP {pdf_resp.status_code}, size: {len(pdf_resp.content)} bytes")
    assert pdf_resp.status_code == 200, f"PDF download failed: {pdf_resp.status_code}"
    assert len(pdf_resp.content) > 30000, "PDF size suspiciously small"

    pdf_local_path = os.path.join("reports", f"{report_id}.pdf")
    os.makedirs("reports", exist_ok=True)
    with open(pdf_local_path, "wb") as f:
        f.write(pdf_resp.content)
    print(f"PDF saved locally to: {pdf_local_path}")

    # Inspect page count using PyMuPDF (fitz) or pypdf
    page_count = 0
    try:
        import fitz  # PyMuPDF
        doc = fitz.open(pdf_local_path)
        page_count = len(doc)
        print(f"PDF Page Count (PyMuPDF): {page_count} pages")
        
        # Render each page to an image for visual inspection
        rendered_images = []
        for p_idx in range(page_count):
            page = doc[p_idx]
            pix = page.get_pixmap(dpi=150)
            img_path = os.path.join("reports", f"{report_id}_page_{p_idx + 1}.png")
            pix.save(img_path)
            rendered_images.append(img_path)
            print(f"  Rendered Page {p_idx + 1} -> {img_path} ({pix.width}x{pix.height})")
    except ImportError:
        try:
            import pypdf
            reader = pypdf.PdfReader(pdf_local_path)
            page_count = len(reader.pages)
            print(f"PDF Page Count (pypdf): {page_count} pages")
        except ImportError:
            # Fallback read trailer
            with open(pdf_local_path, "rb") as f:
                content = f.read()
                page_count = content.count(b"/Type /Page\n") or content.count(b"/Type /Page/")
            print(f"PDF Page Count (raw count): {page_count}")

    print(f"Target is 3-4 pages. Actual: {page_count} pages.")
    assert 3 <= page_count <= 4, f"Expected 3-4 pages, but got {page_count} pages!"
    print("PASS: Exact 3-4 page length requirement verified.")

    # 4. Download DOCX
    print("\n--- STEP 4: Download & Inspect Generated DOCX ---")
    docx_url = f"{base_url}/reports/{report_id}/download/docx"
    docx_resp = requests.get(docx_url, headers=headers, timeout=20)
    print(f"GET {docx_url} -> HTTP {docx_resp.status_code}, size: {len(docx_resp.content)} bytes")
    assert docx_resp.status_code == 200, f"DOCX download failed: {docx_resp.status_code}"
    assert len(docx_resp.content) > 10000, "DOCX size suspiciously small"
    print("PASS: DOCX document generated and downloadable.")

    # 5. Verify Evidence Drawer Endpoints
    print("\n--- STEP 5: Verify Evidence Drawer Resolution & Highlights ---")
    # PDF Evidence Item
    r_pdf = requests.get(f"{base_url}/evidence/DOC-Coal_Production_25-26_pdf-P1", headers=headers, timeout=5)
    assert r_pdf.status_code == 200
    pdf_ev = r_pdf.json()
    assert pdf_ev.get("page_number") == 1
    assert "Annual Repo" in pdf_ev.get("highlight_text", "")
    print(f"PASS: PDF Evidence item resolved (Doc: {pdf_ev.get('document_name')}, Page: {pdf_ev.get('page_number')}).")

    # Excel Evidence Item
    r_xls = requests.get(f"{base_url}/evidence/EV-DEOM-2024", headers=headers, timeout=5)
    assert r_xls.status_code == 200
    xls_ev = r_xls.json()
    assert xls_ev.get("sheet_name") == "FY2024"
    rows = xls_ev.get("table_data", {}).get("rows", [])
    assert len(rows) > 0
    print(f"PASS: Excel Evidence item resolved (Sheet: {xls_ev.get('sheet_name')}, Rows: {len(rows)}).")

    # 6. Pre-retrieval Authorization Enforcement
    print("\n--- STEP 6: Pre-Retrieval Authorization Enforcement ---")
    unauth_headers = {"X-User-ID": "USR001"} # Mining Engineer assigned strictly to DEOM-01
    r_unauth = requests.get(f"{base_url}/evidence/EV-KNUG-2024", headers=unauth_headers, timeout=5)
    print(f"GET /evidence/EV-KNUG-2024 with USR001 -> HTTP {r_unauth.status_code}")
    assert r_unauth.status_code == 403, f"Expected HTTP 403, got {r_unauth.status_code}"
    print("PASS: Unauthorized evidence access strictly rejected with HTTP 403.")

    print("\n============================================================")
    print("ALL VERIFICATIONS COMPLETED SUCCESSFULLY (100% PASS)!")
    print(f"Generated PDF Report ID: {report_id}")
    print(f"Total Pages: {page_count}")
    print("============================================================")
    return report_id, page_count

if __name__ == "__main__":
    run_verification()
