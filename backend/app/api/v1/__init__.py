"""
GeoVault AI - API v1 Router
Aggregates all version 1 endpoints.
"""

from fastapi import APIRouter
from app.api.v1.auth import router as auth_router
from app.api.v1.query import router as query_router
from app.api.v1.evidence import router as evidence_router
from app.api.v1.intelligence import router as intelligence_router
from app.api.v1.topics import router as topics_router
from app.api.v1.reports import router as reports_router
from app.api.v1.audit import router as audit_router

api_v1_router = APIRouter(prefix="/api/v1")

api_v1_router.include_router(auth_router)
api_v1_router.include_router(query_router)
api_v1_router.include_router(evidence_router)
api_v1_router.include_router(intelligence_router)
api_v1_router.include_router(topics_router)
api_v1_router.include_router(reports_router)
api_v1_router.include_router(audit_router)

