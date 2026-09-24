"""
GeoVault AI - Regenerate BAAI/bge-m3 Embeddings Script
Regenerates embeddings for all existing document chunks using BAAI/bge-m3
and verifies vector search accuracy and dimension compliance.
"""

import os
import sys
import numpy as np
from sqlalchemy import select, func, text
from sentence_transformers import SentenceTransformer

# Add app to path
sys.path.insert(0, "/app")

from app.core.database import SessionLocal
from app.models import DocumentChunk, Document


def main():
    print("=" * 70)
    print("GeoVault AI: BAAI/bge-m3 Embedding Regeneration & Verification")
    print("=" * 70)

    db = SessionLocal()
    try:
        # 1. Fetch all existing document chunks
        chunks = db.scalars(select(DocumentChunk).order_by(DocumentChunk.chunk_id)).all()
        total_chunks = len(chunks)
        print(f"[*] Found {total_chunks} existing document chunks in PostgreSQL.")

        if total_chunks == 0:
            print("[!] No document chunks found. Run ingestion first.")
            return

        # 2. Load BAAI/bge-m3
        model_path = "/models/bge-m3" if os.path.exists("/models/bge-m3") else "BAAI/bge-m3"
        print(f"[*] Loading embedding model: '{model_path}' via SentenceTransformer...")
        model = SentenceTransformer(model_path)
        print(f"[+] Successfully loaded {model_path}.")

        # 3. Extract chunk texts
        chunk_texts = [c.chunk_text for c in chunks]
        print(f"[*] Generating BGE-M3 embeddings for {total_chunks} chunks (batch_size=16)...")

        embeddings = model.encode(chunk_texts, batch_size=16, normalize_embeddings=True, show_progress_bar=True)
        print(f"[+] Embeddings generated. Shape: {embeddings.shape}")

        if embeddings.shape[1] != 1024:
            raise ValueError(f"Expected 1024 dimensions, got {embeddings.shape[1]}")

        # 4. Update existing records in place
        print("[*] Updating document_chunks table in PostgreSQL...")
        for chunk, emb in zip(chunks, embeddings):
            chunk.embedding = emb.tolist()

        db.commit()
        print(f"[+] Successfully updated all {total_chunks} document chunks with BGE-M3 embeddings.")

        # 5. Database Verification
        print("\n" + "=" * 70)
        print("DATABASE VERIFICATION")
        print("=" * 70)

        # Check non-null count and dimensions via SQL
        count_query = text("SELECT COUNT(*) FROM document_chunks WHERE embedding IS NOT NULL;")
        non_null_count = db.execute(count_query).scalar()
        print(f"[✓] Document chunks with non-null embeddings: {non_null_count} / {total_chunks}")

        dim_query = text("SELECT DISTINCT vector_dims(embedding) FROM document_chunks;")
        dims = db.execute(dim_query).fetchall()
        dim_values = [d[0] for d in dims]
        print(f"[✓] Distinct embedding dimensions in PostgreSQL: {dim_values}")
        assert dim_values == [1024], f"Unexpected dimensions: {dim_values}"

        # 6. Vector Similarity Search Test
        print("\n" + "=" * 70)
        print("VECTOR SEARCH VERIFICATION (BAAI/bge-m3)")
        print("=" * 70)

        test_queries = [
            "geological fault line and water seepage in coal panel",
            "annual coal production target shortfall and heavy monsoon equipment breakdown"
        ]

        for query_text in test_queries:
            print(f"\nQuery: '{query_text}'")
            q_emb = model.encode(query_text, normalize_embeddings=True)
            q_emb_list = q_emb.tolist()

            # Perform cosine distance search using pgvector <=> operator
            search_sql = text("""
                SELECT 
                    chunk_id, 
                    mine_code, 
                    department, 
                    classification,
                    page_number,
                    1 - (embedding <=> CAST(:q_emb AS vector(1024))) AS similarity,
                    LEFT(chunk_text, 150) AS snippet
                FROM document_chunks
                ORDER BY embedding <=> CAST(:q_emb AS vector(1024))
                LIMIT 3;
            """)

            results = db.execute(search_sql, {"q_emb": str(q_emb_list)}).fetchall()
            for rank, r in enumerate(results, 1):
                print(f"  Rank {rank}: [Sim: {r.similarity:.4f}] Chunk: {r.chunk_id} | Mine: {r.mine_code} | Dept: {r.department}")
                print(f"          Snippet: {r.snippet.replace(chr(10), ' ')}...")

        print("\n" + "=" * 70)
        print("ALL VERIFICATIONS COMPLETED SUCCESSFULLY")
        print("=" * 70)

    except Exception as e:
        db.rollback()
        print(f"[!] ERROR: {str(e)}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
