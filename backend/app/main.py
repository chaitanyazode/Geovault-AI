import httpx
import redis
from fastapi import FastAPI, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, text
from app.core.config import settings
from app.api.v1 import api_v1_router

app = FastAPI(
    title="GeoVault AI API",
    description="Backend API for GeoVault AI — Geological & Mining Reporting Solution for CMPDI/CIL Subsidiaries",
    version="0.1.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount API v1 routes
app.include_router(api_v1_router)

@app.get("/")
def root():
    return {
        "service": "GeoVault AI API",
        "status": "online",
        "version": "0.1.0",
        "phase": "Phase 4 - Security, Authorization & Scope Enforcement"
    }

@app.get("/health", status_code=status.HTTP_200_OK)
async def health_check():
    health = {
        "backend": "healthy",
        "postgres": "unknown",
        "redis": "unknown",
        "llm": "unknown"
    }

    # Check Postgres connection
    try:
        engine = create_engine(settings.DATABASE_URL, connect_args={"connect_timeout": 3})
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
            health["postgres"] = "healthy"
    except Exception as e:
        health["postgres"] = f"unhealthy: {str(e)}"

    # Check Redis connection
    try:
        r = redis.from_url(settings.REDIS_URL, socket_timeout=2)
        if r.ping():
            health["redis"] = "healthy"
    except Exception as e:
        health["redis"] = f"unhealthy: {str(e)}"

    # Check Internal LLM connection
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            resp = await client.get(f"{settings.LLM_BASE_URL.replace('/v1', '')}/health")
            if resp.status_code == 200:
                health["llm"] = "healthy"
            else:
                health["llm"] = f"status_{resp.status_code}"
    except Exception as e:
        health["llm"] = f"waiting_or_initializing"

    return health
