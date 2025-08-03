"""
Custom middleware for the voice authentication microservice.
"""

import time
from typing import Callable, Dict, Any
from datetime import datetime

import structlog
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

logger = structlog.get_logger()


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware for request/response logging with correlation ID support.
    """
    
    def __init__(self, app, exclude_paths: set = None):
        super().__init__(app)
        self.exclude_paths = exclude_paths or {"/healthz", "/docs", "/redoc", "/openapi.json"}
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Skip logging for health checks and docs
        if request.url.path in self.exclude_paths:
            return await call_next(request)
        
        # Extract correlation ID
        correlation_id = request.headers.get("X-Call-ID", f"req_{int(time.time() * 1000)}")
        
        # Add correlation ID to structured logging context
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(correlation_id=correlation_id)
        
        # Log request
        start_time = time.time()
        logger.info(
            "Request started",
            method=request.method,
            path=request.url.path,
            query_params=dict(request.query_params),
            user_agent=request.headers.get("User-Agent", "unknown"),
            correlation_id=correlation_id
        )
        
        try:
            # Process request
            response = await call_next(request)
            
            # Calculate processing time
            process_time = time.time() - start_time
            
            # Log response
            logger.info(
                "Request completed",
                status_code=response.status_code,
                process_time_ms=round(process_time * 1000, 2),
                correlation_id=correlation_id
            )
            
            # Add correlation ID to response headers
            response.headers["X-Call-ID"] = correlation_id
            
            return response
            
        except Exception as e:
            # Calculate processing time
            process_time = time.time() - start_time
            
            # Log error
            logger.error(
                "Request failed",
                error=str(e),
                error_type=type(e).__name__,
                process_time_ms=round(process_time * 1000, 2),
                correlation_id=correlation_id
            )
            
            # Return standardized error response
            return JSONResponse(
                status_code=500,
                content={
                    "error": "InternalServerError",
                    "message": "An unexpected error occurred",
                    "correlation_id": correlation_id,
                    "timestamp": datetime.utcnow().isoformat()
                },
                headers={"X-Call-ID": correlation_id}
            )


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Middleware to add security headers to responses.
    """
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)
        
        # Add security headers
        response.headers.update({
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "X-XSS-Protection": "1; mode=block",
            "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
            "Content-Security-Policy": "default-src 'self'",
            "Referrer-Policy": "strict-origin-when-cross-origin"
        })
        
        return response


class MetricsMiddleware(BaseHTTPMiddleware):
    """
    Middleware to collect basic metrics about requests.
    """
    
    def __init__(self, app):
        super().__init__(app)
        self.request_count = 0
        self.error_count = 0
        self.total_processing_time = 0.0
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start_time = time.time()
        
        try:
            response = await call_next(request)
            
            # Update metrics
            self.request_count += 1
            processing_time = time.time() - start_time
            self.total_processing_time += processing_time
            
            if response.status_code >= 400:
                self.error_count += 1
            
            return response
            
        except Exception as e:
            # Update error metrics
            self.request_count += 1
            self.error_count += 1
            processing_time = time.time() - start_time
            self.total_processing_time += processing_time
            
            raise e
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get current metrics."""
        avg_processing_time = (
            self.total_processing_time / self.request_count 
            if self.request_count > 0 else 0
        )
        
        return {
            "total_requests": self.request_count,
            "error_count": self.error_count,
            "error_rate": self.error_count / self.request_count if self.request_count > 0 else 0,
            "avg_processing_time_ms": round(avg_processing_time * 1000, 2)
        }


# Global metrics instance
metrics_middleware = MetricsMiddleware(None)


def get_metrics() -> Dict[str, Any]:
    """Get current application metrics."""
    return metrics_middleware.get_metrics()


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Simple rate limiting middleware (in-memory, for basic protection).
    """
    
    def __init__(self, app, max_requests: int = 100, window_seconds: int = 60):
        super().__init__(app)
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests: Dict[str, list] = {}
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        client_ip = request.client.host if request.client else "unknown"
        current_time = time.time()
        
        # Clean old requests
        if client_ip in self.requests:
            self.requests[client_ip] = [
                req_time for req_time in self.requests[client_ip]
                if current_time - req_time < self.window_seconds
            ]
        else:
            self.requests[client_ip] = []
        
        # Check rate limit
        if len(self.requests[client_ip]) >= self.max_requests:
            logger.warning(
                "Rate limit exceeded",
                client_ip=client_ip,
                request_count=len(self.requests[client_ip]),
                max_requests=self.max_requests
            )
            
            return JSONResponse(
                status_code=429,
                content={
                    "error": "RateLimitExceeded",
                    "message": f"Too many requests. Limit: {self.max_requests} per {self.window_seconds} seconds",
                    "correlation_id": request.headers.get("X-Call-ID", "unknown"),
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
        
        # Add current request
        self.requests[client_ip].append(current_time)
        
        return await call_next(request)