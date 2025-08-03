"""VAPI integration API endpoints."""

import logging
from typing import Dict, Any, Optional

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel, HttpUrl

from src.clients.vapi_client import (
    capture_audio_from_vapi,
    VAPIConnectionError,
    VAPIAudioError
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/vapi", tags=["vapi"])


class VAPICaptureRequest(BaseModel):
    """Request model for VAPI audio capture."""
    listen_url: HttpUrl
    min_duration: float = 3.0
    silence_threshold: float = 0.01
    silence_duration: float = 2.0
    max_duration: float = 30.0
    connection_timeout: float = 10.0


class VAPICaptureResponse(BaseModel):
    """Response model for VAPI audio capture."""
    success: bool
    message: str
    audio_size_bytes: Optional[int] = None
    capture_duration_seconds: Optional[float] = None


class VAPITestResponse(BaseModel):
    """Response model for VAPI test endpoint."""
    status: str
    message: str
    websocket_client_available: bool


@router.get("/test", response_model=VAPITestResponse)
async def test_vapi_client() -> VAPITestResponse:
    """Test VAPI WebSocket client availability."""
    try:
        # Test if websockets library is available
        import websockets
        websocket_available = True
    except ImportError:
        websocket_available = False
    
    return VAPITestResponse(
        status="ok",
        message="VAPI client test completed",
        websocket_client_available=websocket_available
    )


@router.post("/capture", response_model=VAPICaptureResponse)
async def capture_vapi_audio(request: VAPICaptureRequest) -> VAPICaptureResponse:
    """
    Capture audio from VAPI WebSocket stream.
    
    Connects to the provided VAPI listen URL and captures audio with silence detection.
    """
    try:
        logger.info(f"Starting VAPI audio capture from: {request.listen_url}")
        
        import time
        start_time = time.time()
        
        # Capture audio from VAPI
        audio_data = await capture_audio_from_vapi(
            listen_url=str(request.listen_url),
            min_duration=request.min_duration,
            silence_threshold=request.silence_threshold,
            silence_duration=request.silence_duration,
            max_duration=request.max_duration,
            connection_timeout=request.connection_timeout
        )
        
        capture_duration = time.time() - start_time
        
        logger.info(f"VAPI audio capture completed. Duration: {capture_duration}s, Size: {len(audio_data)} bytes")
        
        return VAPICaptureResponse(
            success=True,
            message="Audio captured successfully from VAPI",
            audio_size_bytes=len(audio_data),
            capture_duration_seconds=capture_duration
        )
        
    except VAPIConnectionError as e:
        logger.error(f"VAPI connection failed: {e}")
        raise HTTPException(status_code=503, detail=f"Failed to connect to VAPI: {str(e)}")
        
    except VAPIAudioError as e:
        logger.error(f"VAPI audio capture failed: {e}")
        raise HTTPException(status_code=422, detail=f"Failed to capture audio: {str(e)}")
        
    except Exception as e:
        logger.error(f"Unexpected error during VAPI capture: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/config")
async def get_vapi_config() -> Dict[str, Any]:
    """Get VAPI client configuration options."""
    return {
        "default_settings": {
            "min_duration": 3.0,
            "silence_threshold": 0.01,
            "silence_duration": 2.0,
            "max_duration": 30.0,
            "connection_timeout": 10.0
        },
        "audio_format": {
            "sample_rate": "16kHz",
            "channels": "mono (1)",
            "bit_depth": "16-bit",
            "encoding": "PCM"
        },
        "supported_protocols": ["wss", "ws"],
        "description": "WebSocket client for capturing live audio from VAPI with silence detection"
    }