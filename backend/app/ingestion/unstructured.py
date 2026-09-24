import os
import re
from typing import Dict, Any, List, Tuple
import pymupdf # PyMuPDF
from sentence_transformers import SentenceTransformer
from sqlalchemy.orm import Session
from sqlalchemy import select, delete

from app.models import Document, DocumentChunk
from app.ingestion.hasher import compute_file_sha256

# Initialize embedding model once (1024-dimensional BAAI/bge-m3 model)
_embedding_model = None

def get_embedding_model():
    global _embedding_model
    if _embedding_model is None:
        model_path = "/models/bge-m3" if os.path.exists("/models/bge-m3") else "BAAI/bge-m3"
        _embedding_model = SentenceTransformer(model_path)
    return _embedding_model


def extract_metadata_from_filename(filename: str) -> Dict[str, Any]:
    """Infers canonical mine_code, year, department, and classification from filename."""
    meta = {
        "mine_code": None,
        "year": None,
        "department": "Mining",
        "classification": "INTERNAL",
        "category": "Operational Memo"
    }

    fn_lower = filename.lower()
    
    # Mine code
    if "deom" in fn_lower or "dharani" in fn_lower:
        meta["mine_code"] = "DEOM-01"
    elif "knug" in fn_lower or "koyna" in fn_lower:
        meta["mine_code"] = "KNUG-02"
    elif "ssop" in fn_lower or "satpura" in fn_lower:
        meta["mine_code"] = "SSOP-03"

    # Year
    year_match = re.search(r"(202\d)", filename)
    if year_match:
        meta["year"] = int(year_match.group(1))

    # Department
    if any(k in fn_lower for k in ["fault", "geolog", "water", "panel", "seam"]):
        meta["department"] = "Geology"
    elif any(k in fn_lower for k in ["ventilat", "dust", "safet", "hazard"]):
        meta["department"] = "Safety"
    elif any(k in fn_lower for k in ["logistics", "dispatch", "road", "rail"]):
        meta["department"] = "Transportation"
    elif any(k in fn_lower for k in ["equipment", "shovel", "miner", "monsoon"]):
        meta["department"] = "Mining"

    # Classification & Category
    if "confidential" in fn_lower:
        meta["classification"] = "CONFIDENTIAL"
    elif "restricted" in fn_lower or "geolog" in fn_lower:
        meta["classification"] = "RESTRICTED"
    else:
        meta["classification"] = "INTERNAL"

    if "ocr" in fn_lower or filename.endswith(".txt"):
        meta["category"] = "Scan Archive OCR"
    elif "coal directory" in fn_lower or "provisional" in fn_lower or "inventory" in fn_lower or "annual report" in fn_lower:
        meta["category"] = "Official Publication"
        meta["classification"] = "INTERNAL"

    return meta


def chunk_text_page(text: str, max_chars: int = 1200, overlap_chars: int = 150) -> List[str]:
    """Chunks long text into manageable paragraphs with overlap."""
    text = text.strip()
    if not text:
        return []
    if len(text) <= max_chars:
        return [text]

    chunks = []
    start = 0
    while start < len(text):
        end = min(start + max_chars, len(text))
        # Try to break on newline or period
        if end < len(text):
            break_point = text.rfind("\n", start, end)
            if break_point == -1 or break_point < start + (max_chars // 2):
                break_point = text.rfind(". ", start, end)
            if break_point != -1 and break_point > start + (max_chars // 2):
                end = break_point + 1
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        start = end - overlap_chars
        if start >= len(text) - overlap_chars:
            break
    return chunks


def ingest_unstructured_documents(db: Session, coal_data_dir: str) -> Dict[str, Any]:
    """Ingests legacy PDFs, scan text extracts, and official publication PDFs idempotently."""
    model = get_embedding_model()
    
    docs_created = 0
    docs_skipped = 0
    total_chunks = 0
    ocr_pages_flagged = 0
    warnings = []

    files_to_process = []
    
    # 1. Legacy PDFs and OCR extracts
    legacy_dir = os.path.join(coal_data_dir, "legacy_pdfs")
    if os.path.exists(legacy_dir):
        for f in sorted(os.listdir(legacy_dir)):
            if f.endswith(".pdf") or f.endswith(".txt"):
                files_to_process.append(os.path.join(legacy_dir, f))

    # 2. Official PDFs (controlled subset: short chapters first, index macro docs)
    official_dir = os.path.join(coal_data_dir, "Official Data")
    if os.path.exists(official_dir):
        for f in sorted(os.listdir(official_dir)):
            if f.endswith(".pdf"):
                files_to_process.append(os.path.join(official_dir, f))

    for fpath in files_to_process:
        fname = os.path.basename(fpath)
        fhash = compute_file_sha256(fpath)
        doc_id = f"DOC-{fname.replace(' ', '_').replace('.', '_')[:50]}"
        
        # Check idempotency
        existing_doc = db.execute(select(Document).where(Document.file_hash == fhash)).scalar_one_or_none()
        if existing_doc:
            docs_skipped += 1
            continue

        meta = extract_metadata_from_filename(fname)
        
        pages_data = [] # List of (page_num, text)
        page_count = 1

        if fname.endswith(".txt"):
            with open(fpath, "r", encoding="utf-8", errors="replace") as tf:
                content = tf.read().strip()
                pages_data.append((1, content))
        elif fname.endswith(".pdf"):
            try:
                pdf_doc = pymupdf.open(fpath)
                page_count = len(pdf_doc)
                # For very large directories (270 pages), sample introductory and chapter summary pages
                # to stay strictly within the 16 GB host RAM budget
                max_pages_to_extract = min(page_count, 15 if page_count > 50 else page_count)
                
                for pno in range(max_pages_to_extract):
                    ptxt = pdf_doc[pno].get_text().strip()
                    if len(ptxt) < 40 and page_count > 1:
                        ocr_pages_flagged += 1
                    pages_data.append((pno + 1, ptxt))
                pdf_doc.close()
            except Exception as e:
                warnings.append(f"Error reading PDF {fname}: {str(e)}")
                continue

        # Create Document record
        doc_record = Document(
            document_id=doc_id,
            file_name=fname,
            file_hash=fhash,
            file_path=fpath,
            category=meta["category"],
            mine_code=meta["mine_code"],
            department=meta["department"],
            year=meta["year"],
            page_count=page_count,
            classification=meta["classification"],
            processing_status="PROCESSED"
        )
        db.add(doc_record)
        db.flush()
        docs_created += 1

        # Prepare Chunks
        raw_chunks = []
        for pno, ptext in pages_data:
            if not ptext:
                continue
            text_blocks = chunk_text_page(ptext)
            for c_idx, blk in enumerate(text_blocks):
                # Contextual chunk header for high-fidelity retrieval
                header = f"[Source: {fname} | Mine: {meta['mine_code'] or 'ALL'} | Year: {meta['year'] or 'N/A'} | Page {pno}]\n"
                full_chunk_text = header + blk
                raw_chunks.append({
                    "chunk_id": f"{doc_id}-P{pno}-{c_idx:03d}",
                    "page_number": pno,
                    "chunk_index": c_idx,
                    "text": full_chunk_text,
                    "mine_code": meta["mine_code"],
                    "department": meta["department"],
                    "classification": meta["classification"]
                })

        if raw_chunks:
            # Batch embedding generation with BAAI/bge-m3 (1024 dimensions)
            chunk_texts = [rc["text"] for rc in raw_chunks]
            embeddings = model.encode(chunk_texts, batch_size=16, normalize_embeddings=True)

            for rc, emb in zip(raw_chunks, embeddings):
                chunk_obj = DocumentChunk(
                    chunk_id=rc["chunk_id"],
                    document_id=doc_record.document_id,
                    page_number=rc["page_number"],
                    chunk_index=rc["chunk_index"],
                    chunk_text=rc["text"],
                    mine_code=rc["mine_code"],
                    department=rc["department"],
                    classification=rc["classification"],
                    access_scope={"mine_code": rc["mine_code"], "department": rc["department"], "classification": rc["classification"]},
                    embedding=emb.tolist()
                )
                db.add(chunk_obj)
                total_chunks += 1

        db.commit()

    return {
        "documents_created": docs_created,
        "documents_skipped": docs_skipped,
        "total_chunks_created": total_chunks,
        "ocr_pages_flagged": ocr_pages_flagged,
        "warnings": warnings
    }
