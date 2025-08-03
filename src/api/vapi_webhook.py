"""
VAPI webhook handler for voice authentication.
"""

import logging
from datetime import datetime
from typing import Dict, Any, Optional

import structlog
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse

from src.services.auth_service import get_auth_service, VerificationError
from src.observability import trace_function, record_verification_metrics

logger = structlog.get_logger()
router = APIRouter(prefix="/api/v1", tags=["vapi-webhook"])


def extract_phone_from_vapi_payload(payload: Dict[str, Any]) -> Optional[str]:
    """Extract phone number from VAPI webhook payload."""
    try:
        # Try to get phone from customer object in call
        call_data = payload.get("message", {}).get("call", {})
        customer = call_data.get("customer", {})
        
        if customer and "number" in customer:
            return customer["number"]
        
        # Try alternative path
        customer_alt = payload.get("message", {}).get("customer", {})
        if customer_alt and "number" in customer_alt:
            return customer_alt["number"]
            
        # Log the payload structure for debugging
        logger.warning("Could not extract phone number from VAPI payload", payload_keys=list(payload.keys()))
        return None
        
    except Exception as e:
        logger.error("Error extracting phone from VAPI payload", error=str(e))
        return None


def extract_listen_url_from_vapi_payload(payload: Dict[str, Any]) -> Optional[str]:
    """Extract WebSocket listen URL from VAPI webhook payload."""
    try:
        # Get monitor data from call
        call_data = payload.get("message", {}).get("call", {})
        monitor = call_data.get("monitor", {})
        
        if monitor and "listenUrl" in monitor:
            return monitor["listenUrl"]
            
        logger.warning("Could not extract listen URL from VAPI payload")
        return None
        
    except Exception as e:
        logger.error("Error extracting listen URL from VAPI payload", error=str(e))
        return None


@router.post("/vapi-webhook")
@trace_function("vapi_webhook")
async def handle_vapi_webhook(request: Request) -> JSONResponse:
    """
    Handle VAPI webhook for voice authentication.
    
    This endpoint receives VAPI webhooks when the assistant calls the verifyPassword function.
    It extracts the phone number and listen URL from the payload, then processes voice verification.
    """
    correlation_id = request.headers.get("X-Call-ID", "unknown")
    
    try:
        # Parse webhook payload
        payload = await request.json()
        logger.info("Received VAPI webhook", correlation_id=correlation_id)
        
        # Extract phone number from payload
        phone = extract_phone_from_vapi_payload(payload)
        if not phone:
            logger.error("Could not extract phone number from VAPI payload", correlation_id=correlation_id)
            return JSONResponse(
                status_code=400,
                content={
                    "error": "MissingPhoneNumber",
                    "message": "Could not extract phone number from call data",
                    "correlation_id": correlation_id
                }
            )
        
        # Extract listen URL from payload
        listen_url = extract_listen_url_from_vapi_payload(payload)
        if not listen_url:
            logger.error("Could not extract listen URL from VAPI payload", correlation_id=correlation_id)
            return JSONResponse(
                status_code=400,
                content={
                    "error": "MissingListenURL",
                    "message": "Could not extract WebSocket listen URL from call data",
                    "correlation_id": correlation_id
                }
            )
        
        logger.info(
            "Processing VAPI verification request",
            phone=phone,
            listen_url=listen_url,
            correlation_id=correlation_id
        )
        
        # Process voice verification
        auth_service = get_auth_service()
        
        try:
            success, message, score = await auth_service.verify_user(
                phone=phone,
                listen_url=listen_url
            )
            
            # Record metrics
            record_verification_metrics(
                success=success,
                processing_time=0.0,  # TODO: Add timing
                similarity_score=score,
                phone=phone
            )
            
            logger.info(
                "VAPI verification completed",
                phone=phone,
                success=success,
                score=score,
                correlation_id=correlation_id
            )
            
            # Return response that VAPI can use
            response_content = {
                "success": success,
                "message": message,
                "score": score,
                "phone": phone,
                "correlation_id": correlation_id,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            if success:
                # For successful verification, you could add user data here
                # response_content["user_data"] = await get_user_data(phone)
                pass
            
            return JSONResponse(
                status_code=200,
                content=response_content
            )
            
        except VerificationError as e:
            error_message = str(e)
            logger.error(
                "VAPI verification failed",
                phone=phone,
                error=error_message,
                correlation_id=correlation_id
            )
            
            # Record failed metrics
            record_verification_metrics(
                success=False,
                processing_time=0.0,
                similarity_score=None,
                phone=phone
            )
            
            # Return error response for VAPI
            return JSONResponse(
                status_code=400,
                content={
                    "success": False,
                    "error": "VerificationFailed",
                    "message": error_message,
                    "phone": phone,
                    "correlation_id": correlation_id,
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
            
    except Exception as e:
        logger.error(
            "Unexpected error in VAPI webhook",
            error=str(e),
            correlation_id=correlation_id
        )
        
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": "InternalServerError",
                "message": "An unexpected error occurred during verification",
                "correlation_id": correlation_id,
                "timestamp": datetime.utcnow().isoformat()
            }
        )


@router.post("/vapi-webhook/debug")
async def debug_vapi_payload(request: Request) -> JSONResponse:
    """
    Debug endpoint to inspect VAPI webhook payloads.
    
    Use this endpoint during development to see the exact structure
    of VAPI webhook payloads.
    """
    correlation_id = request.headers.get("X-Call-ID", "unknown")
    
    try:
        payload = await request.json()
        
        # Extract key information
        phone = extract_phone_from_vapi_payload(payload)
        listen_url = extract_listen_url_from_vapi_payload(payload)
        
        debug_info = {
            "extracted_phone": phone,
            "extracted_listen_url": listen_url,
            "payload_structure": {
                "message_keys": list(payload.get("message", {}).keys()) if "message" in payload else [],
                "call_keys": list(payload.get("message", {}).get("call", {}).keys()) if payload.get("message", {}).get("call") else [],
                "customer_data": payload.get("message", {}).get("customer"),
                "monitor_data": payload.get("message", {}).get("call", {}).get("monitor"),
            },
            "full_payload": payload,
            "correlation_id": correlation_id,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        logger.info("VAPI webhook debug", debug_info=debug_info)
        
        return JSONResponse(
            status_code=200,
            content=debug_info
        )
        
    except Exception as e:
        logger.error("Error in debug endpoint", error=str(e), correlation_id=correlation_id)
        return JSONResponse(
            status_code=500,
            content={
                "error": str(e),
                "correlation_id": correlation_id
            }
        )