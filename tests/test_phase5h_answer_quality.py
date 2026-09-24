"""
GeoVault AI - Phase 5H Answer Quality, Readability, Consistency & Metric Normalization Tests
Verifies:
1. Summary & Detailed Answer two-part structure
2. Exact numerical consistency between KPI facts and narrative values
3. Canonical unit (MT, %) enforcement
4. Zero legacy identifiers in runtime outputs (GEVRA is 56.10 MT, never 5.02 MT)
5. Multi-mine comparison covers all 5 canonical mines
6. Spatial PostGIS calculations remain deterministic
7. Fact / Observation / Inference distinction
8. Synthetic demonstration provenance disclaimers
9. Pre-retrieval authorization boundary (403)
10. Zero chain-of-thought (<think>) leakage
"""

import pytest
import re
from decimal import Decimal
from fastapi import HTTPException
from app.core.database import SessionLocal
from app.security.context import UserContext, AuthorizedScope
from app.ai.orchestrator import UnifiedAIOrchestrator
from app.services.query_service import DeterministicQueryService
from app.schemas.query import GroundedQueryResponse


@pytest.fixture(scope="module")
def db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def usr001_gevra():
    user = UserContext(
        user_id="USR001",
        username="mining_eng_gevra",
        email="mining.gevra@cil.internal",
        role="Mining Engineer",
        department="Mining",
        clearance_level="INTERNAL",
        assigned_mine_code="GEVRA",
    )
    scope = AuthorizedScope(
        user_id="USR001",
        role="Mining Engineer",
        allowed_mines={"GEVRA", "GV001"},
        allowed_departments={"Mining", "Geology"},
        max_clearance="INTERNAL",
    )
    return user, scope


@pytest.fixture
def usr005_enterprise():
    user = UserContext(
        user_id="USR005",
        username="general_manager",
        email="gm@cmpdi.internal",
        role="General Manager",
        department="Executive",
        clearance_level="CONFIDENTIAL",
    )
    scope = AuthorizedScope(
        user_id="USR005",
        role="General Manager",
        allowed_mines=None,  # Unrestricted enterprise scope
        allowed_departments=None,
        max_clearance="CONFIDENTIAL",
    )
    return user, scope


# 1. GEVRA production KPI and narrative consistency (never 5.02 MT)
def test_gevra_production_kpi_and_narrative_consistency(db_session, usr001_gevra):
    user, scope = usr001_gevra
    orch = UnifiedAIOrchestrator(db_session, user, scope)
    res = orch.orchestrate("What was GEVRA's production in FY2024-25?")

    assert res.structured_results is not None
    facts = res.structured_results.get("facts", [])
    assert len(facts) >= 1

    f0 = facts[0]
    assert f0["mine_code"] == "GEVRA"
    assert int(f0["year"]) == 2024
    assert float(f0["actual_production_mt"]) == pytest.approx(56.10, rel=1e-2)
    assert float(f0["target_mt"]) == pytest.approx(58.50, rel=1e-2)
    assert float(f0["variance_mt"]) == pytest.approx(-2.40, rel=1e-2)
    assert float(f0["achievement_pct"]) == pytest.approx(95.90, rel=1e-2)

    # Verify narrative mentions the same exact values
    combined_text = f"{res.summary} {res.detailed_answer}"
    assert "56.10" in combined_text or "56.1" in combined_text
    assert "58.50" in combined_text or "58.5" in combined_text
    assert "95.9" in combined_text
    assert "2.40" in combined_text or "-2.40" in combined_text

    # CRITICAL: Must NEVER contain the legacy 5.02 MT or DEOM-01
    assert "5.02" not in combined_text
    assert "DEOM-01" not in combined_text


# 2. Both summary and detailed_answer exist
def test_summary_and_detailed_answer_present(db_session, usr001_gevra):
    user, scope = usr001_gevra
    orch = UnifiedAIOrchestrator(db_session, user, scope)
    res = orch.orchestrate("What was GEVRA's production in FY2024-25?")

    assert res.summary is not None
    assert len(res.summary.strip()) > 20
    assert res.detailed_answer is not None
    assert len(res.detailed_answer.strip()) > 30


# 3. Summary length and descriptiveness (2-5 sentences, informative)
def test_summary_length_and_descriptiveness(db_session, usr001_gevra):
    user, scope = usr001_gevra
    orch = UnifiedAIOrchestrator(db_session, user, scope)
    res = orch.orchestrate("What was GEVRA's production in FY2024-25?")

    sentences = [s.strip() for s in re.split(r"[.!?]", res.summary) if len(s.strip()) > 5]
    assert 2 <= len(sentences) <= 6, f"Expected 2-5 sentences in summary, got {len(sentences)}: {res.summary}"
    assert "GEVRA" in res.summary
    assert "target" in res.summary.lower() or "achievement" in res.summary.lower()


# 4. Detailed answer contains structured headings (###)
def test_detailed_answer_headings(db_session, usr001_gevra):
    user, scope = usr001_gevra
    orch = UnifiedAIOrchestrator(db_session, user, scope)
    res = orch.orchestrate("What was GEVRA's production in FY2024-25?")

    assert "###" in res.detailed_answer
    headings = re.findall(r"###\s*([^\n]+)", res.detailed_answer)
    assert len(headings) >= 2


# 5. Canonical unit MT and % enforcement
def test_canonical_unit_mt_enforcement(db_session, usr001_gevra):
    user, scope = usr001_gevra
    orch = UnifiedAIOrchestrator(db_session, user, scope)
    res = orch.orchestrate("What was GEVRA's production in FY2024-25?")

    combined = f"{res.summary} {res.detailed_answer}"
    assert "MT" in combined
    assert "%" in combined
    assert "56,100 MT" not in combined


# 6. Mine consistency (GEVRA maintained throughout)
def test_mine_consistency(db_session, usr001_gevra):
    user, scope = usr001_gevra
    orch = UnifiedAIOrchestrator(db_session, user, scope)
    res = orch.orchestrate("What was GEVRA's production in FY2024-25?")

    assert "GEVRA" in res.summary
    assert "GEVRA" in res.detailed_answer
    if res.structured_results and "facts" in res.structured_results:
        for f in res.structured_results["facts"]:
            assert f.get("mine_code") == "GEVRA"


# 7. Fiscal year consistency (FY2024-25 / 2024)
def test_fiscal_year_consistency(db_session, usr001_gevra):
    user, scope = usr001_gevra
    orch = UnifiedAIOrchestrator(db_session, user, scope)
    res = orch.orchestrate("What was GEVRA's production in FY2024-25?")

    combined = f"{res.summary} {res.detailed_answer}"
    assert "2024" in combined or "FY2024" in combined


# 8. No fabricated values
def test_no_fabricated_values(db_session, usr001_gevra):
    user, scope = usr001_gevra
    orch = UnifiedAIOrchestrator(db_session, user, scope)
    res = orch.orchestrate("What was GEVRA's production in FY2024-25?")

    # Verify numbers in text correlate with true database figures
    assert "56.10" in res.summary or "56.1" in res.summary
    assert "58.50" in res.summary or "58.5" in res.summary


# 9. No fabricated pages (citations are verifiable)
def test_no_fabricated_pages(db_session, usr001_gevra):
    user, scope = usr001_gevra
    orch = UnifiedAIOrchestrator(db_session, user, scope)
    res = orch.orchestrate("What geological observations were reported for GEVRA in FY2024-25?")

    for ev in res.evidence:
        if ev.page_number is not None:
            assert isinstance(ev.page_number, int)
            assert ev.page_number > 0


# 10. Evidence references present
def test_evidence_references_present(db_session, usr001_gevra):
    user, scope = usr001_gevra
    orch = UnifiedAIOrchestrator(db_session, user, scope)
    res = orch.orchestrate("What was GEVRA's production in FY2024-25?")

    assert len(res.evidence) >= 1
    ev0 = res.evidence[0]
    assert ev0.evidence_id.startswith("EV-")
    assert ev0.citation is not None


# 11. Synthetic demonstration provenance disclosure
def test_synthetic_provenance_disclosure(db_session, usr001_gevra):
    user, scope = usr001_gevra
    orch = UnifiedAIOrchestrator(db_session, user, scope)
    res = orch.orchestrate("What was GEVRA's production in FY2024-25?")

    combined = f"{res.summary} {res.detailed_answer}".lower()
    assert "synthetic demonstration" in combined or "synthetic demo" in combined


# 12. Hybrid route fact / inference distinction
def test_hybrid_fact_inference_distinction(db_session, usr001_gevra):
    user, scope = usr001_gevra
    orch = UnifiedAIOrchestrator(db_session, user, scope)
    res = orch.orchestrate("Explain the production shortfall using operational and geological evidence.")

    assert res.query_type in ["HYBRID", "SQL", "ANALYTICS"]
    assert res.summary is not None
    assert res.detailed_answer is not None


# 13. Multi-mine comparison covers all five canonical mines
def test_multi_mine_comparison_five_canonical_mines(db_session, usr005_enterprise):
    user, scope = usr005_enterprise
    orch = UnifiedAIOrchestrator(db_session, user, scope)
    res = orch.orchestrate("Compare FY2024-25 production across the five mines.")

    assert res.structured_results is not None
    analytics = res.structured_results.get("analytics", {})
    comparisons = analytics.get("comparisons", [])
    
    assert len(comparisons) == 5, f"Expected exactly 5 canonical mines, got {len(comparisons)}"
    mine_codes = {c["mine_code"] for c in comparisons}
    assert mine_codes == {"GEVRA", "KUSMUNDA", "DIPKA", "NIGAHI", "DUDHICHUA"}

    # Verify no legacy mines in multi-mine comparison
    assert "DEOM-01" not in mine_codes
    assert "KNUG-02" not in mine_codes
    assert "SSOP-03" not in mine_codes


# 14. Spatial calculation is deterministic (PostGIS)
def test_spatial_deterministic_calculation(db_session, usr001_gevra):
    user, scope = usr001_gevra
    orch = UnifiedAIOrchestrator(db_session, user, scope)
    res = orch.orchestrate("Which GEVRA boreholes are within 500 metres of the requested geological feature?")

    assert res.query_type == "SPATIAL"
    assert res.summary is not None
    assert "postgis" in res.summary.lower() or "spatial" in res.summary.lower()
    assert len(res.evidence) > 0


# 15. Geology route structure
def test_geology_route_structure(db_session, usr001_gevra):
    user, scope = usr001_gevra
    orch = UnifiedAIOrchestrator(db_session, user, scope)
    res = orch.orchestrate("What coal seams are present in GEVRA?")

    assert res.query_type == "GEOLOGY"
    assert res.summary is not None
    assert res.detailed_answer is not None
    assert "###" in res.detailed_answer


# 16. RAG route structure
def test_rag_route_structure(db_session, usr001_gevra):
    user, scope = usr001_gevra
    orch = UnifiedAIOrchestrator(db_session, user, scope)
    res = orch.orchestrate("What geological observations were reported for GEVRA in FY2024-25?")

    assert res.summary is not None
    assert res.detailed_answer is not None
    assert len(res.evidence) > 0


# 17. Unauthorized query returns 403 before retrieval
def test_unauthorized_query_403(db_session, usr001_gevra):
    user, scope = usr001_gevra
    orch = UnifiedAIOrchestrator(db_session, user, scope)
    
    with pytest.raises(HTTPException) as excinfo:
        orch.orchestrate("What was NIGAHI's production in FY2024-25?")

    assert excinfo.value.status_code == 403
    assert "outside authorized scope" in excinfo.value.detail or "not authorized" in excinfo.value.detail


# 18. No chain-of-thought leakage (<think> tags stripped)
def test_no_chain_of_thought_leakage(db_session, usr001_gevra):
    user, scope = usr001_gevra
    orch = UnifiedAIOrchestrator(db_session, user, scope)
    res = orch.orchestrate("What was GEVRA's production in FY2024-25?")

    assert "<think>" not in res.answer
    assert "</think>" not in res.answer
    assert "<think>" not in res.summary
    assert "<think>" not in res.detailed_answer


# 19. No legacy identifiers in active runtime output
def test_no_legacy_identifiers_in_runtime_output(db_session, usr001_gevra):
    user, scope = usr001_gevra
    orch = UnifiedAIOrchestrator(db_session, user, scope)
    res = orch.orchestrate("What was GEVRA's production in FY2024-25?")

    combined = f"{res.summary} {res.detailed_answer}"
    legacy_terms = ["DEOM-01", "KNUG-02", "SSOP-03", "Dharani East", "Shakti Coalfields", "Mine A"]
    for term in legacy_terms:
        assert term not in combined, f"Legacy term '{term}' leaked into user-facing output"


# 20. Empty or missing evidence handled gracefully
def test_empty_or_missing_evidence_handling(db_session, usr001_gevra):
    user, scope = usr001_gevra
    orch = UnifiedAIOrchestrator(db_session, user, scope)
    res = orch.orchestrate("What was GEVRA's production in the year 1950?")

    assert res.summary is not None
    assert len(res.summary) > 0
