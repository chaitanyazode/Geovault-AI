"""
GeoVault AI - Topic Identification & Word Cloud Schemas
Data models for keyword frequencies, topic clustering, and word cloud visualization.
"""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class KeywordItem(BaseModel):
    """Represents an extracted keyword or domain terminology with quantitative metrics."""
    keyword: str
    frequency: int
    tfidf_score: float
    document_count: int

    @property
    def document_frequency(self) -> int:
        return self.document_count


class TopicCluster(BaseModel):
    """Represents a discovered thematic topic cluster derived from authorized documents."""
    topic_id: str
    title: str
    top_keywords: List[str]
    document_chunk_count: int
    mines_covered: List[str]
    description: str
    representative_quotes: List[str] = Field(default_factory=list)

    @property
    def keywords(self) -> List[str]:
        return self.top_keywords

    @property
    def chunk_count(self) -> int:
        return self.document_chunk_count




class TopicAnalysisRequest(BaseModel):
    """Request parameters for scoped topic discovery and word cloud generation."""
    mine_code: Optional[str] = Field(None, description="Optional mine filter (must be within user's authorized scope)")
    department: Optional[str] = Field(None, description="Optional department filter (e.g. Mining, Geology, Safety)")
    year: Optional[int] = Field(None, description="Optional reporting year filter")
    max_keywords: int = Field(25, ge=5, le=100, description="Maximum keywords to extract")
    num_clusters: int = Field(4, ge=2, le=10, description="Target number of topic clusters")
    generate_wordcloud: bool = Field(True, description="Whether to render a visual word cloud PNG")


class TopicAnalysisResponse(BaseModel):
    """Complete topic discovery and keyword intelligence payload."""
    topics: List[TopicCluster]
    keywords: List[KeywordItem]
    total_chunks_analyzed: int
    total_documents_analyzed: int
    scope_applied: Dict[str, Any]
    wordcloud_url: Optional[str] = None
    wordcloud_path: Optional[str] = None
    data_gaps: List[str] = Field(default_factory=list)
    processing_time_ms: float = 0.0

    @property
    def wordcloud(self):
        class _WC:
            def __init__(self, url, path):
                self.image_url = url
                self.image_path = path
                self.wordcloud_url = url
                self.wordcloud_path = path
        return _WC(self.wordcloud_url, self.wordcloud_path)



class KeywordExtractionResponse(BaseModel):
    """Lightweight keyword extraction payload."""
    keywords: List[KeywordItem]
    total_chunks_analyzed: int
    scope_applied: Dict[str, Any]


class WordCloudResponse(BaseModel):
    """Word cloud image metadata and download reference."""
    wordcloud_url: str
    wordcloud_path: str
    total_words: int
    scope_applied: Dict[str, Any]
    image_width: int = 800
    image_height: int = 400
