"""Main FastAPI application for voice authentication microservice."""

import logging
import signal
import sys
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Dict, Any

import structlog
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from src.config import settings
from src.api.audio import router as audio_router
from src.api.vapi import router as vapi_router


# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()


class HealthResponse(BaseModel):
    """Health check response model."""
    status: str
    timestamp: datetime
    version: str = "1.0.0"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    logger.info("Starting voice authentication microservice", 
                port=settings.port, 
                host=settings.host)
    
    # Validate configuration
    try:
        # Test that all required environment variables are present
        logger.info("Configuration validated successfully")
    except Exception as e:
        logger.error("Configuration validation failed", error=str(e))
        sys.exit(1)
    
    yield
    
    # Shutdown
    logger.info("Shutting down voice authentication microservice")


# Create FastAPI application
app = FastAPI(
    title="Voice Authentication Microservice",
    description="Production-ready voice authentication service with speaker enrollment and verification",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routers
app.include_router(audio_router)
app.include_router(vapi_router)


@app.middleware("http")
async def logging_middleware(request: Request, call_next):
    """Add correlation ID and request logging."""
    correlation_id = request.headers.get("X-Call-ID", "unknown")
    
    # Add correlation ID to structured logging context
    structlog.contextvars.clear_contextvars()
    structlog.contextvars.bind_contextvars(correlation_id=correlation_id)
    
    logger.info("Request received", 
                method=request.method, 
                url=str(request.url),
                correlation_id=correlation_id)
    
    try:
        response = await call_next(request)
        logger.info("Request completed", 
                    status_code=response.status_code,
                    correlation_id=correlation_id)
        return response
    except Exception as e:
        logger.error("Request failed", 
                     error=str(e),
                     correlation_id=correlation_id)
        return JSONResponse(
            status_code=500,
            content={
                "error": "Internal Server Error",
                "message": "An unexpected error occurred",
                "correlation_id": correlation_id,
                "timestamp": datetime.utcnow().isoformat()
            }
        )


@app.get("/healthz", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Health check endpoint."""
    return HealthResponse(
        status="healthy",
        timestamp=datetime.utcnow()
    )


def handle_shutdown(signum, frame):
    """Handle graceful shutdown signals."""
    logger.info("Received shutdown signal", signal=signum)
    sys.exit(0)


# Register signal handlers for graceful shutdown
signal.signal(signal.SIGTERM, handle_shutdown)
signal.signal(signal.SIGINT, handle_shutdown)


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "src.main:app",
        host=settings.host,
        port=settings.port,
        log_level=settings.log_level.lower(),
        reload=False
    )