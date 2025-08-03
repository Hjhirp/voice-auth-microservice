"""
Authentication API endpoints for voice enrollment and verification.
"""

import logging
import time
from datetime import datetime
from typing import Dict, Any

import structlog
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse

from src.models.api_models import (
    EnrollmentRequest,
    EnrollmentResponse,
    VerificationRequest,
    VerificationResponse,
    ErrorResponse
)
from src.services.auth_service import get_auth_service, EnrollmentError, VerificationError
from src.observability import (
    trace_function,
    record_enrollment_metrics,
    record_verification_metrics
)

logger = structlog.get_logger()
router = APIRouter(prefix="/api/v1", tags=["authentication"])


def create_error_response(
    error_type: str,
    message: str,
    correlation_id: str,
    status_code: int = 500
) -> JSONResponse:
    """Create standardized error response."""
    error_response = ErrorResponse(
        error=error_type,
        message=message,
        correlation_id=correlation_id,
        timestamp=datetime.utcnow()
    )
    return JSONResponse(
        status_code=status_code,
        content=error_response.model_dump()
    )


@router.post("/enroll-user", response_model=EnrollmentResponse)
@trace_function("enrollment_endpoint")
async def enroll_user(request: EnrollmentRequest, http_request: Request) -> EnrollmentResponse:
    """
    Enroll a user for voice authentication.
    
    Downloads audio from provided URL, processes it to 16kHz mono WAV format,
    generates voice embedding using SpeechBrain ECAPA-TDNN, and stores user
    record in database.
    
    Args:
        request: Enrollment request containing userId, phone, and audioUrl
        http_request: HTTP request for correlation ID extraction
        
    Returns:
        EnrollmentResponse with status and confidence score
        
    Raises:
        HTTPException: For various error scenarios with appropriate status codes
    """
    correlation_id = http_request.headers.get("X-Call-ID", "unknown")
    auth_service = get_auth_service()
    start_time = time.time()
    
    logger.info(
        "Enrollment request received",
        user_id=str(request.userId),
        phone=request.phone,
        audio_url=request.audioUrl,
        correlation_id=correlation_id
    )
    
    try:
        # Perform user enrollment
        status, score = await auth_service.enroll_user(
            phone=request.phone,
            audio_url=request.audioUrl
        )
        
        # Record metrics
        processing_time = time.time() - start_time
        record_enrollment_metrics(
            success=True,
            processing_time=processing_time,
            phone=request.phone
        )
        
        logger.info(
            "Enrollment completed successfully",
            phone=request.phone,
            status=status,
            score=score,
            correlation_id=correlation_id
        )
        
        return EnrollmentResponse(status=status, score=score)
        
    except EnrollmentError as e:
        # Record failed metrics
        processing_time = time.time() - start_time
        record_enrollment_metrics(
            success=False,
            processing_time=processing_time,
            phone=request.phone
        )
        
        error_message = str(e)
        logger.error(
            "Enrollment failed",
            phone=request.phone,
            error=error_message,
            correlation_id=correlation_id
        )
        
        # Determine appropriate status code based on error type
        if "download" in error_message.lower():
            status_code = 400  # Bad Request - invalid audio URL
            error_type = "AudioDownloadError"
        elif "conversion" in error_message.lower() or "processing" in error_message.lower():
            status_code = 422  # Unprocessable Entity - audio conversion failed
            error_type = "AudioProcessingError"
        elif "store" in error_message.lower() or "database" in error_message.lower():
            status_code = 500  # Internal Server Error - database operation failed
            error_type = "DatabaseError"
        else:
            status_code = 400  # Bad Request - general enrollment error
            error_type = "EnrollmentError"
        
        raise HTTPException(
            status_code=status_code,
            detail={
                "error": error_type,
                "message": error_message,
                "correlation_id": correlation_id,
                "timestamp": datetime.utcnow().isoformat()
            }
        )
        
    except Exception as e:
        error_message = f"Unexpected error during enrollment: {str(e)}"
        logger.error(
            "Unexpected enrollment error",
            phone=request.phone,
            error=error_message,
            correlation_id=correlation_id
        )
        
        raise HTTPException(
            status_code=500,
            detail={
                "error": "InternalServerError",
                "message": "An unexpected error occurred during enrollment",
                "correlation_id": correlation_id,
                "timestamp": datetime.utcnow().isoformat()
            }
        )


@router.post("/verify-password", response_model=VerificationResponse)
@trace_function("verification_endpoint")
async def verify_password(request: VerificationRequest, http_request: Request) -> VerificationResponse:
    """
    Verify user identity through voice authentication.
    
    Connects to VAPI WebSocket to capture live audio, generates embedding,
    compares with stored user embedding, and returns verification result.
    
    Args:
        request: Verification request containing userId and listenUrl
        http_request: HTTP request for correlation ID extraction
        
    Returns:
        VerificationResponse with success status, message, and similarity score
        
    Raises:
        HTTPException: For various error scenarios
    """
    correlation_id = http_request.headers.get("X-Call-ID", "unknown")
    auth_service = get_auth_service()
    start_time = time.time()
    
    logger.info(
        "Verification request received",
        user_id=str(request.userId),
        listen_url=request.listenUrl,
        correlation_id=correlation_id
    )
    
    try:
        # Perform user verification
        success, message, score = await auth_service.verify_user(
            phone=request.phone,
            listen_url=request.listenUrl
        )
        
        # Record metrics
        processing_time = time.time() - start_time
        record_verification_metrics(
            success=success,
            processing_time=processing_time,
            similarity_score=score,
            phone=request.phone
        )
        
        logger.info(
            "Verification completed",
            phone=request.phone,
            success=success,
            score=score,
            correlation_id=correlation_id
        )
        
        # For successful verification, we could return user records here
        # Since you mentioned the pipeline ends at authentication, we'll return None
        records = None
        if success:
            # In a real implementation, you might fetch user records here
            # records = await fetch_user_records(request.userId)
            pass
        
        return VerificationResponse(
            success=success,
            message=message,
            records=records,
            score=score
        )
        
    except VerificationError as e:
        # Record failed metrics
        processing_time = time.time() - start_time
        record_verification_metrics(
            success=False,
            processing_time=processing_time,
            similarity_score=None,
            phone=request.phone
        )
        
        error_message = str(e)
        logger.error(
            "Verification failed",
            phone=request.phone,
            error=error_message,
            correlation_id=correlation_id
        )
        
        # Determine appropriate status code based on error type
        if "connect" in error_message.lower() or "websocket" in error_message.lower():
            status_code = 400  # Bad Request - WebSocket connection failed
            error_type = "ConnectionError"
        elif "capture" in error_message.lower() or "audio" in error_message.lower():
            status_code = 422  # Unprocessable Entity - audio capture/processing failed
            error_type = "AudioProcessingError"
        elif "user" in error_message.lower() and "not" in error_message.lower():
            status_code = 404  # Not Found - user not enrolled
            error_type = "UserNotFoundError"
        else:
            status_code = 500  # Internal Server Error - general verification error
            error_type = "VerificationError"
        
        raise HTTPException(
            status_code=status_code,
            detail={
                "error": error_type,
                "message": error_message,
                "correlation_id": correlation_id,
                "timestamp": datetime.utcnow().isoformat()
            }
        )
        
    except Exception as e:
        error_message = f"Unexpected error during verification: {str(e)}"
        logger.error(
            "Unexpected verification error",
            phone=request.phone,
            error=error_message,
            correlation_id=correlation_id
        )
        
        raise HTTPException(
            status_code=500,
            detail={
                "error": "InternalServerError",
                "message": "An unexpected error occurred during verification",
                "correlation_id": correlation_id,
                "timestamp": datetime.utcnow().isoformat()
            }
        )


@router.get("/health", response_model=Dict[str, Any])
async def auth_health_check() -> Dict[str, Any]:
    """
    Health check endpoint specific to authentication service.
    
    Returns:
        Dict with service health status and component checks
    """
    auth_service = get_auth_service()
    
    try:
        # Check database connectivity
        db_healthy = await auth_service.db.health_check()
        
        # Check embedding service
        embedding_info = auth_service.embedding_service.get_model_info()
        embedding_healthy = embedding_info.get("model_loaded", False)
        
        overall_healthy = db_healthy and embedding_healthy
        
        return {
            "status": "healthy" if overall_healthy else "unhealthy",
            "timestamp": datetime.utcnow().isoformat(),
            "components": {
                "database": {
                    "status": "healthy" if db_healthy else "unhealthy",
                    "details": "Database connectivity check"
                },
                "embedding_service": {
                    "status": "healthy" if embedding_healthy else "unhealthy",
                    "details": embedding_info
                }
            }
        }
        
    except Exception as e:
        logger.error("Health check failed", error=str(e))
        return {
            "status": "unhealthy",
            "timestamp": datetime.utcnow().isoformat(),
            "error": str(e)
        }


@router.get("/users/{phone}/auth-history")
async def get_user_auth_history(
    phone: str,
    http_request: Request,
    limit: int = 10
) -> Dict[str, Any]:
    """
    Get authentication history for a user.
    
    Args:
        phone: User's phone number to get history for
        http_request: HTTP request for correlation ID
        limit: Maximum number of attempts to return
        
    Returns:
        Dict with authentication attempts history
    """
    correlation_id = http_request.headers.get("X-Call-ID", "unknown")
    auth_service = get_auth_service()
    
    try:
        attempts = await auth_service.get_user_auth_history(phone, limit)
        
        return {
            "phone": phone,
            "attempts": [
                {
                    "id": attempt.id,
                    "success": attempt.success,
                    "score": attempt.score,
                    "created_at": attempt.created_at.isoformat()
                }
                for attempt in attempts
            ],
            "correlation_id": correlation_id
        }
        
    except Exception as e:
        logger.error(
            "Failed to get auth history",
            phone=phone,
            error=str(e),
            correlation_id=correlation_id
        )
        
        raise HTTPException(
            status_code=500,
            detail={
                "error": "InternalServerError",
                "message": "Failed to retrieve authentication history",
                "correlation_id": correlation_id,
                "timestamp": datetime.utcnow().isoformat()
            }
        )