"""
GeoVault AI - LlamaIndex Scoped Vector Retriever
Enforces strict AUTHORIZATION BEFORE RETRIEVAL for vector RAG operations.
Uses BAAI/bge-m3 embeddings and pre-filters PostgreSQL pgvector document_chunks.
"""

from typing import List, Optional, Tuple, Any
from sqlalchemy.orm import Session

from llama_index.core.retrievers import BaseRetriever
from llama_index.core.schema import NodeWithScore, TextNode, QueryBundle

from app.security.context import AuthorizedScope
from app.security.service import AuthorizationService
from app.services.evidence_engine import EvidenceEngine
from app.schemas.query import EvidenceItem
from app.ingestion.unstructured import get_embedding_model


class ScopedVectorRetriever(BaseRetriever):
    """
    LlamaIndex-compliant Retriever with mandatory Authorization pre-filtering.
    Enforces mine, department, and classification scopes inside pgvector BEFORE retrieval.
    """

    def __init__(
        self,
        db: Session,
        scope: AuthorizedScope,
        top_k: int = 5,
        target_mine: Optional[str] = None,
    ):
        super().__init__()
        self.db = db
        self.scope = scope
        self.top_k = top_k
        self.target_mine = target_mine

    def _retrieve(self, query_bundle: QueryBundle) -> List[NodeWithScore]:
        """
        Retrieves matching document chunks within the user's authorized scope.
        Never retrieves unauthorized data into memory.
        """
        query_str = query_bundle.query_str

        # 1. Generate 1024-dim BAAI/bge-m3 query vector
        emb_model = get_embedding_model()
        q_vec = emb_model.encode(query_str, normalize_embeddings=True).tolist()

        # 2. Execute SQL pre-filtered vector retrieval via AuthorizationService
        matches = AuthorizationService.scoped_vector_search(
            db=self.db,
            query_embedding=q_vec,
            scope=self.scope,
            top_k=self.top_k,
            target_mine=self.target_mine,
        )

        nodes: List[NodeWithScore] = []
        for chunk, score in matches:
            node = TextNode(
                id_=chunk.chunk_id,
                text=chunk.chunk_text,
                metadata={
                    "document_id": chunk.document_id,
                    "page_number": chunk.page_number,
                    "mine_code": chunk.mine_code,
                    "department": chunk.department,
                    "classification": chunk.classification,
                    "provenance_type": chunk.provenance_type,
                },
            )
            nodes.append(NodeWithScore(node=node, score=float(score)))

        return nodes

    def retrieve_with_evidence(self, query_str: str) -> Tuple[List[NodeWithScore], List[EvidenceItem]]:
        """
        Convenience method that retrieves LlamaIndex nodes and translates them
        into standardized, verifiable EvidenceItem models for synthesis.
        """
        bundle = QueryBundle(query_str=query_str)
        nodes = self._retrieve(bundle)

        # Retrieve raw chunks from db to build rich evidence items
        if not nodes:
            return [], []

        chunk_ids = [n.node.node_id for n in nodes]
        from app.models.knowledge import DocumentChunk
        from sqlalchemy import select

        chunks = self.db.scalars(
            select(DocumentChunk).where(DocumentChunk.chunk_id.in_(chunk_ids))
        ).all()

        # Preserve order of relevance
        chunk_map = {c.chunk_id: c for c in chunks}
        ordered_chunks = [chunk_map[cid] for cid in chunk_ids if cid in chunk_map]

        evidence_items = EvidenceEngine.from_document_chunks(ordered_chunks)
        return nodes, evidence_items
