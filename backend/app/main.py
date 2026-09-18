"""
Zaslon-QDS Backend Application Entrypoint.
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import logging

from .core.config import settings
from .core.exceptions import ZaslonBaseException
from .core.logging import setup_logging
from .api.router import api_router
from .db.base import Base
from .db.session import engine

# Setup logging
logger = setup_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"Starting {settings.PROJECT_NAME} v{settings.VERSION} [{settings.APP_ENV}]")
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Database schema initialized successfully.")
    except Exception as e:
        logger.warning(f"Database table verification deferred: {str(e)}")
    yield
    logger.info(f"Shutting down {settings.PROJECT_NAME}")


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Quantum-Teleportation-Based Cyber Threat Detection for Quantum Digital Signatures (SIH 26141)",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# CORS Middleware configuration - restricted to configured origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS if isinstance(settings.CORS_ORIGINS, list) else [settings.CORS_ORIGINS],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(ZaslonBaseException)
async def domain_exception_handler(request: Request, exc: ZaslonBaseException):
    logger.warning(f"Domain Exception [{exc.code}]: {exc.message} | Details: {exc.details}")
    status_map = {
        "SESSION_NOT_FOUND": status.HTTP_404_NOT_FOUND,
        "CUDA_Q_UNAVAILABLE": status.HTTP_503_SERVICE_UNAVAILABLE,
        "QUANTUM_EXECUTION_ERROR": status.HTTP_500_INTERNAL_SERVER_ERROR,
        "UNAUTHORIZED": status.HTTP_403_FORBIDDEN,
        "INTEGRITY_FAILURE": status.HTTP_422_UNPROCESSABLE_ENTITY,
        "REPLAY_DETECTED": status.HTTP_409_CONFLICT,
        "INVALID_STATE_TRANSITION": status.HTTP_400_BAD_REQUEST
    }
    http_status = status_map.get(exc.code, status.HTTP_400_BAD_REQUEST)
    return JSONResponse(
        status_code=http_status,
        content={
            "success": False,
            "data": None,
            "error": exc.message,
            "code": exc.code,
            "details": exc.details
        }
    )


# Mount Master Router
app.include_router(api_router)


@app.get("/", tags=["Root"])
def root():
    return {
        "system": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "docs": "/docs",
        "health": "/api/v1/health"
    }
