import os
import sys
import json
import time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy import select, func, text
from app.core.database import SessionLocal, engine
from app.models import DocumentChunk, Conflict, ProductionAnnual, Mine
from app.ingestion.pipeline import run_full_ingestion_pipeline

def main():
    print("=================================================================")
    print("       GeoVault AI — Phase 3 Ingestion & Embedding Pipeline       ")
    print("=================================================================")

    coal_data_dir = "/data/coal_data"
    if not os.path.exists(coal_data_dir):
        # Fallback to local Windows path if running outside Docker
        coal_data_dir = r"F:\GeoVault\Coal Data"

    print(f"[*] Authoritative Source Directory (READ-ONLY): {coal_data_dir}")

    # 1. First Run (Initial Ingestion)
    print("\n--- [RUN 1] Executing Initial Ingestion Pipeline ---")
    t0 = time.time()
    res1 = run_full_ingestion_pipeline(coal_data_dir)
    t1 = time.time()

    print(f"[+] Run 1 completed in {res1['duration_seconds']}s with status: {res1['status']}")
    print(f"[+] Files discovered: {res1['discovery']['total_files']}")
    print(f"    File types breakdown: {res1['discovery']['file_types']}")
    print(f"[+] Structured records inserted:")
    for tbl, cnt in res1["operational_records"].items():
        print(f"    - {tbl}: {cnt}")
    for tbl, cnt in res1["macro_records"].items():
        print(f"    - {tbl}: {cnt}")
    print(f"[+] Master records created: {res1['master_records']}")
    print(f"[+] Unstructured documents created: {res1['unstructured']['documents_created']}")
    print(f"[+] Document chunks created & embedded: {res1['unstructured']['total_chunks_created']}")
    print(f"[+] Conflicts registered: {res1['conflicts_registered']}")

    # 2. Second Run (Idempotency & Duplicate Check)
    print("\n--- [RUN 2] Executing Pipeline Again (Idempotency Verification) ---")
    t2 = time.time()
    res2 = run_full_ingestion_pipeline(coal_data_dir)
    t3 = time.time()

    print(f"[+] Run 2 completed in {res2['duration_seconds']}s")
    print(f"[+] Documents skipped (already present with identical SHA-256): {res2['unstructured']['documents_skipped']}")
    print(f"[+] New documents created on re-run: {res2['unstructured']['documents_created']}")
    print(f"[+] New chunks created on re-run: {res2['unstructured']['total_chunks_created']}")

    # 3. Vector & Database Integrity Verification
    print("\n--- [VERIFICATION] Database Integrity & Vector Dimension Check ---")
    session = SessionLocal()
    try:
        # Check vector dimensions and non-null count
        chunk_count = session.scalar(select(func.count(DocumentChunk.chunk_id)))
        sample_chunk = session.execute(select(DocumentChunk).where(DocumentChunk.embedding.isnot(None)).limit(1)).scalar_one_or_none()
        
        assert sample_chunk is not None, "No document chunks with embeddings found!"
        # In pgvector / sqlalchemy, embedding is an ndarray or list
        emb_dim = len(sample_chunk.embedding)
        print(f"[VERIFIED] Total Document Chunks: {chunk_count}")
        print(f"[VERIFIED] Sample Chunk ID: {sample_chunk.chunk_id}")
        print(f"[VERIFIED] Embedding Vector Dimension: {emb_dim} (Expected: 1024)")
        assert emb_dim == 1024, f"Expected 1024 dimensions, got {emb_dim}"

        # Check Conflicts
        conflicts = session.execute(select(Conflict)).scalars().all()
        print(f"[VERIFIED] Total Registered Conflicts: {len(conflicts)}")
        for c in conflicts:
            print(f"    - [{c.status}] {c.conflict_id}: {c.metric_or_topic}")
            print(f"      Source A: {c.source_a_value}")
            print(f"      Source B: {c.source_b_value}")

        # Check Production Annual record count
        prod_count = session.scalar(select(func.count(ProductionAnnual.id)))
        print(f"[VERIFIED] Total Production Annual records: {prod_count} (Expected: 15)")
        assert prod_count == 15, f"Expected 15 rows, got {prod_count}"

        # Check Mines
        mines = session.execute(select(Mine)).scalars().all()
        print(f"[VERIFIED] Canonical Mines in DB: {[m.mine_code for m in mines]}")
        assert len(mines) == 3, f"Expected 3 mines, got {len(mines)}"

        print("\n=================================================================")
        print(">>> ALL INGESTION, IDEMPOTENCY & VECTOR TESTS PASSED! <<<")
        print("=================================================================")

    finally:
        session.close()

if __name__ == "__main__":
    main()
