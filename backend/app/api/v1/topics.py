"""
GeoVault AI - Topic Intelligence & Word Cloud API Endpoints
Provides authenticated, permission-scoped endpoints for topic discovery,
keyword extraction, and word cloud image generation & retrieval.
"""

import os
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.schemas.topics import (
    TopicAnalysisRequest,
    TopicAnalysisResponse,
    KeywordExtractionResponse,
    WordCloudResponse,
)
from app.services.topic_service import TopicAnalysisService, WORDCLOUD_DIR
from app.security.context import UserContext, AuthorizedScope
from app.security.dependencies import (
    get_current_user,
    get_authorized_scope,
    get_db,
)
from app.security.roles import Permission, has_permission
from app.security.audit import AuditLogger

router = APIRouter(prefix="/topics", tags=["Topic Discovery & Word Clouds"])


@router.post("/analyze", response_model=TopicAnalysisResponse)
def analyze_topics_and_keywords(
    req: TopicAnalysisRequest,
    user: UserContext = Depends(get_current_user),
    scope: AuthorizedScope = Depends(get_authorized_scope),
    db: Session = Depends(get_db),
) -> TopicAnalysisResponse:
    """
    Executes scoped topic discovery, keyword ranking, and WordCloud rendering.
    Enforces authorization scope before accessing document chunks.
    """
    if not (has_permission(user.role, Permission.QUERY_STRUCTURED) or has_permission(user.role, Permission.QUERY_VECTOR)):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Access Denied: Role '{user.role}' lacks query permissions.",
        )

    result = TopicAnalysisService.analyze_topics(db=db, scope=scope, req=req)

    AuditLogger.log_query(
        db=db,
        user_id=user.user_id,
        question=f"Topic analysis mine={req.mine_code} dept={req.department} year={req.year}",
        route_selected="TOPIC",
        scope=scope,
        evidence_count=result.total_chunks_analyzed,
        evidence_status="VERIFIED" if result.topics else "INSUFFICIENT_AUTHORIZED_DATA",
        response_summary=f"Extracted {len(result.topics)} topics and {len(result.keywords)} keywords.",
    )

    return result


@router.get("/keywords", response_model=KeywordExtractionResponse)
@router.post("/keywords", response_model=KeywordExtractionResponse)
def extract_scoped_keywords(
    mine_code: Optional[str] = None,
    department: Optional[str] = None,
    year: Optional[int] = None,
    top_n: int = 25,
    req: Optional[TopicAnalysisRequest] = None,
    user: UserContext = Depends(get_current_user),
    scope: AuthorizedScope = Depends(get_authorized_scope),
    db: Session = Depends(get_db),
) -> KeywordExtractionResponse:
    """
    Extracts top keywords and terminology from authorized documents.
    """
    if not (has_permission(user.role, Permission.QUERY_STRUCTURED) or has_permission(user.role, Permission.QUERY_VECTOR)):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Access Denied: Role '{user.role}' lacks query permissions.",
        )

    m = (req.mine_code if req else None) or mine_code
    d = (req.department if req else None) or department
    y = (req.year if req else None) or year
    max_kw = (req.max_keywords if req else None) or top_n

    chunks = TopicAnalysisService.get_scoped_chunks(
        db=db, scope=scope, mine_code=m, department=d, year=y
    )
    keywords = TopicAnalysisService.extract_keywords_tfidf(chunks, max_keywords=max_kw)

    return KeywordExtractionResponse(
        keywords=keywords,
        total_chunks_analyzed=len(chunks),
        scope_applied=scope.to_dict(),
    )


@router.get("/wordcloud", response_model=WordCloudResponse)
@router.post("/wordcloud", response_model=WordCloudResponse)
def generate_scoped_wordcloud(
    mine_code: Optional[str] = None,
    department: Optional[str] = None,
    year: Optional[int] = None,
    top_n: int = 30,
    req: Optional[TopicAnalysisRequest] = None,
    user: UserContext = Depends(get_current_user),
    scope: AuthorizedScope = Depends(get_authorized_scope),
    db: Session = Depends(get_db),
) -> WordCloudResponse:
    """
    Renders and stores a visual WordCloud PNG from authorized document terminology.
    """
    if not (has_permission(user.role, Permission.QUERY_STRUCTURED) or has_permission(user.role, Permission.QUERY_VECTOR)):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Access Denied: Role '{user.role}' lacks query permissions.",
        )

    m = (req.mine_code if req else None) or mine_code
    d = (req.department if req else None) or department
    y = (req.year if req else None) or year
    max_kw = (req.max_keywords if req else None) or top_n

    chunks = TopicAnalysisService.get_scoped_chunks(
        db=db, scope=scope, mine_code=m, department=d, year=y
    )
    keywords = TopicAnalysisService.extract_keywords_tfidf(chunks, max_keywords=max_kw)

    if not keywords:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No authorized document content available to render word cloud.",
        )

    file_id = f"{m or 'ALL'}_{d or 'ALL'}_{scope.user_id}"
    url, path = TopicAnalysisService.generate_wordcloud_image(keywords, file_id)

    if not url or not path:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to render word cloud image.",
        )

    return WordCloudResponse(
        wordcloud_url=url,
        wordcloud_path=path,
        total_words=len(keywords),
        scope_applied=scope.to_dict(),
    )



@router.get("/wordcloud/image/{filename}")
def serve_wordcloud_image(filename: str):
    """
    Serves generated WordCloud PNG images from persistent derived storage.
    Includes directory traversal protection.
    """
    safe_filename = os.path.basename(filename)
    file_path = os.path.join(WORDCLOUD_DIR, safe_filename)

    if not os.path.exists(file_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Word cloud image '{safe_filename}' not found.",
        )

    return FileResponse(file_path, media_type="image/png")
