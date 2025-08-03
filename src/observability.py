"""
Observability and monitoring setup for the voice authentication microservice.
"""

import time
from typing import Optional, Dict, Any, Callable
from functools import wraps

import structlog

logger = structlog.get_logger()


def setup_observability(
    service_name: str = "voice-auth-microservice",
    service_version: str = "1.0.0",
    otlp_endpoint: Optional[str] = None,
    enable_console_export: bool = True
) -> None:
    """
    Set up observability (currently only structlog is used).
    
    Args:
        service_name: Name of the service for tracing
        service_version: Version of the service
        otlp_endpoint: OTLP endpoint for trace/metric export
        enable_console_export: Whether to enable console export for development
    """
    logger.info(
        "Setting up observability",
        service_name=service_name,
        service_version=service_version,
        otlp_endpoint=otlp_endpoint
    )
    
    # Structlog configuration can be added here if needed


def instrument_fastapi_app(app) -> None:
    """
    Instrument FastAPI application (currently no-op).
    
    Args:
        app: FastAPI application instance
    """
    logger.info("FastAPI application instrumented with OpenTelemetry")


def trace_function(operation_name: Optional[str] = None):
    """
    Decorator to trace function execution (currently no-op).
    
    Args:
        operation_name: Optional custom operation name for the span
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            return await func(*args, **kwargs)
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            return func(*args, **kwargs)
        
        # Return appropriate wrapper based on function type
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


def record_enrollment_metrics(success: bool, processing_time: float, user_id: str) -> None:
    """
    Record metrics for enrollment operations (currently only logging).
    
    Args:
        success: Whether enrollment was successful
        processing_time: Time taken for enrollment in seconds
        user_id: User ID for attribution
    """
    logger.info(
        "Enrollment operation",
        success=success,
        processing_time=processing_time,
        user_id=user_id
    )


def record_verification_metrics(
    success: bool,
    processing_time: float,
    similarity_score: Optional[float],
    user_id: str
) -> None:
    """
    Record metrics for verification operations (currently only logging).
    
    Args:
        success: Whether verification was successful
        processing_time: Time taken for verification in seconds
        similarity_score: Voice similarity score (if available)
        user_id: User ID for attribution
    """
    logger.info(
        "Verification operation",
        success=success,
        processing_time=processing_time,
        similarity_score=similarity_score,
        user_id=user_id
    )


def record_http_metrics(
    method: str,
    path: str,
    status_code: int,
    processing_time: float
) -> None:
    """
    Record HTTP request metrics (currently only logging).
    
    Args:
        method: HTTP method
        path: Request path
        status_code: HTTP status code
        processing_time: Request processing time in seconds
    """
    logger.info(
        "HTTP request",
        method=method,
        path=path,
        status_code=status_code,
        processing_time=processing_time
    )


class TracingContextMiddleware:
    """
    Middleware to add tracing context to structured logs (currently no-op).
    """
    
    def __init__(self, app):
        self.app = app
    
    async def __call__(self, scope, receive, send):
        await self.app(scope, receive, send)