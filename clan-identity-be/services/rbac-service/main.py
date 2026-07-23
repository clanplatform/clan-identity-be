"""
RBAC Service - Main Application Entry Point
Handles role-based access control
"""
from fastapi import FastAPI
from contextlib import asynccontextmanager
import logging

from app.core.config import settings
from app.db.database import init_db
from app.api.routes import rbac

logging.basicConfig(
    level=logging.INFO if not settings.DEBUG else logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    logger.info(f"Starting {settings.PROJECT_NAME}...")
    logger.info(f"Environment: {settings.ENVIRONMENT}")
    logger.info(f"Database: {settings.POSTGRES_DB}")
    
    try:
        init_db()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
    
    yield
    
    logger.info(f"Shutting down {settings.PROJECT_NAME}...")


app = FastAPI(
    title=settings.PROJECT_NAME,
    description="RBAC Service API - Role-Based Access Control",
    version="1.0.0",
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url=f"{settings.API_V1_STR}/docs",
    redoc_url=f"{settings.API_V1_STR}/redoc",
    lifespan=lifespan
)


# --- CORS (env-driven via CORS_ORIGINS) ------------------------------------
# Authoritative CORS is the API gateway (Envoy). This block only applies while
# the service is exposed directly (Render/nginx ingress). Origins come from the
# CORS_ORIGINS env var (JSON list or comma-separated). Empty => no CORS (prod
# default-deny); dev falls back to localhost.
import os as _os
import json as _json
from fastapi.middleware.cors import CORSMiddleware as _CORSMiddleware


def _clan_cors_origins() -> list:
    raw = (_os.getenv("CORS_ORIGINS") or "").strip()
    if raw.startswith("["):
        try:
            return [str(o).strip() for o in _json.loads(raw) if str(o).strip()]
        except Exception:
            return []
    origins = [o.strip() for o in raw.split(",") if o.strip()]
    if not origins and _os.getenv("ENVIRONMENT", "development").lower().startswith(("dev", "local")):
        origins = ["http://localhost:3000", "http://localhost:8080"]
    return origins


_clan_origins = _clan_cors_origins()
if _clan_origins:
    app.add_middleware(
        _CORSMiddleware,
        allow_origins=_clan_origins,
        allow_credentials="*" not in _clan_origins,
        allow_methods=["*"],
        allow_headers=["*"],
    )
# ---------------------------------------------------------------------------

app.include_router(
    rbac.router,
    prefix=f"{settings.API_V1_STR}/rbac",
    tags=["RBAC"]
)


@app.get("/")
async def root():
    return {
        "service": settings.PROJECT_NAME,
        "version": "1.0.0",
        "status": "running",
        "environment": settings.ENVIRONMENT,
        "database": settings.POSTGRES_DB
    }


@app.get("/health")
async def health_check():
    from app.db.database import engine
    from sqlalchemy import text
    
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        db_status = "healthy"
    except Exception as e:
        db_status = f"unhealthy: {str(e)}"
    
    return {
        "status": "healthy",
        "database": db_status,
        "service": settings.PROJECT_NAME
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=settings.DEBUG)
