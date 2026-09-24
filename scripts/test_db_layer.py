import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import numpy as np
from sqlalchemy import select, text
from app.core.database import SessionLocal, engine
from app.models import (
    Subsidiary,
    Mine,
    User,
    UserScope,
    ProductionAnnual,
    Document,
    DocumentChunk,
    Conflict,
    Evidence,
    QueryAuditLog
)

def run_tests():
    print("=== GeoVault AI Database Layer Integration Test ===")
    
    # 1. Connection test
    with engine.connect() as conn:
        res = conn.execute(text("SELECT version();")).scalar()
        print(f"[OK] Connected to PostgreSQL: {res[:40]}...")
        
        vec_res = conn.execute(text("SELECT extversion FROM pg_extension WHERE extname = 'vector';")).scalar()
        print(f"[OK] pgvector extension version: {vec_res}")

    session = SessionLocal()
    try:
        # 2. Master Data Insertion
        sub = Subsidiary(subsidiary_id="TEST_SUB", subsidiary_name="Test Subsidiary Ltd.")
        session.add(sub)
        session.flush()
        print(f"[OK] Created Subsidiary: {sub.subsidiary_id}")

        mine = Mine(
            mine_code="TEST-01",
            mine_name="Test Opencast Project",
            subsidiary_id=sub.subsidiary_id,
            mine_type="Opencast",
            coal_type="Non-coking thermal coal",
            location="Test Sector"
        )
        session.add(mine)
        session.flush()
        print(f"[OK] Created Mine: {mine.mine_code}")

        user = User(
            user_id="USR999",
            username="test_engineer",
            email="test_engineer@geovault.local",
            role="Mining Engineer",
            department="Mining",
            clearance_level="INTERNAL",
            assigned_mine_code=mine.mine_code,
            is_active=True
        )
        session.add(user)
        session.flush()
        print(f"[OK] Created User: {user.user_id} ({user.role})")

        scope = UserScope(
            user_id=user.user_id,
            mine_code=mine.mine_code,
            department="Mining",
            max_classification="INTERNAL"
        )
        session.add(scope)
        session.flush()
        print(f"[OK] Created UserScope for {user.user_id}")

        # 3. Operational Data Insertion
        prod = ProductionAnnual(
            mine_code=mine.mine_code,
            year=2024,
            target_mt=5.0,
            actual_production_mt=5.12,
            variance_mt=0.12,
            achievement_pct=102.4,
            dispatch_mt=4.95,
            equipment_or_face_availability_pct=94.5
        )
        session.add(prod)
        session.flush()
        print(f"[OK] Created ProductionAnnual for {prod.mine_code} ({prod.year})")

        # 4. Document & DocumentChunk with Vector(1024)
        doc = Document(
            document_id="DOC-TEST-001",
            file_name="test_memo.pdf",
            file_hash="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
            file_path="/data/documents/test_memo.pdf",
            category="Legacy Memo",
            mine_code=mine.mine_code,
            subsidiary_id=sub.subsidiary_id,
            department="Mining",
            year=2024,
            page_count=1,
            classification="INTERNAL",
            processing_status="PROCESSED"
        )
        session.add(doc)
        session.flush()
        print(f"[OK] Created Document: {doc.document_id}")

        # Generate a dummy 1024-dimensional normalized vector
        dummy_vector = np.random.randn(1024).astype(np.float32)
        dummy_vector /= np.linalg.norm(dummy_vector)
        
        chunk = DocumentChunk(
            chunk_id="CHK-TEST-001",
            document_id=doc.document_id,
            page_number=1,
            chunk_index=0,
            chunk_text="Test operational note regarding equipment maintenance and production schedule.",
            mine_code=mine.mine_code,
            subsidiary_id=sub.subsidiary_id,
            department="Mining",
            classification="INTERNAL",
            access_scope={"mine": "TEST-01", "clearance": "INTERNAL"},
            embedding=dummy_vector.tolist()
        )
        session.add(chunk)
        session.flush()
        print(f"[OK] Created DocumentChunk with 1024-dim Vector embedding")

        # 5. Permission-Aware Vector Distance Retrieval Test
        # Pre-filtering by mine_code and classification (Authorization Before Retrieval)
        auth_scope_mine = "TEST-01"
        user_clearance = "INTERNAL"
        
        query_vec = dummy_vector.tolist()
        stmt = (
            select(
                DocumentChunk.chunk_id,
                DocumentChunk.chunk_text,
                DocumentChunk.embedding.cosine_distance(query_vec).label("distance")
            )
            .where(DocumentChunk.mine_code == auth_scope_mine)
            .where(DocumentChunk.classification == user_clearance)
            .order_by("distance")
            .limit(1)
        )
        result = session.execute(stmt).fetchone()
        assert result is not None, "Vector search returned no results"
        print(f"[OK] Vector Search Result: chunk_id={result.chunk_id}, cosine_distance={result.distance:.6f}")

        # 6. Conflict & Audit Logging Test
        conflict = Conflict(
            conflict_id="CONF-TEST-001",
            mine_code=mine.mine_code,
            year=2024,
            metric_or_topic="Dispatch vs Operational Backlog",
            source_a_type="STRUCTURED_DISPATCH",
            source_a_reference="dispatch_summary.csv",
            source_a_value="Normal (0.08 MT gap)",
            source_b_type="OPERATIONAL_LOG",
            source_b_reference="mining_issue_log.csv",
            source_b_value="Rail congestion backlog of 0.31 MT",
            status="CONFLICT"
        )
        session.add(conflict)

        audit = QueryAuditLog(
            log_id="LOG-TEST-001",
            user_id=user.user_id,
            question="What was the production in 2024?",
            route_selected="SQL",
            authorized_scope_applied={"mine_code": "TEST-01", "clearance": "INTERNAL"},
            evidence_count=1,
            evidence_status="VERIFIED",
            response_summary="Production was 5.12 MT against 5.0 MT target.",
            execution_time_ms=14
        )
        session.add(audit)
        session.commit()
        print(f"[OK] Successfully committed Conflict and QueryAuditLog records")

        # 7. Clean up test records
        session.delete(audit)
        session.delete(conflict)
        session.delete(chunk)
        session.delete(doc)
        session.delete(prod)
        session.delete(scope)
        session.delete(user)
        session.delete(mine)
        session.delete(sub)
        session.commit()
        print(f"[OK] Successfully cleaned up all test records")
        print("\n>>> ALL DATABASE & PGVECTOR TESTS PASSED SUCCESSFULLY! <<<")

    except Exception as e:
        session.rollback()
        print(f"[FAILED] Test failed: {e}", file=sys.stderr)
        raise
    finally:
        session.close()

if __name__ == "__main__":
    run_tests()
