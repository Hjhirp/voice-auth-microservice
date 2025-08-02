"""Audio processing API endpoints."""

import logging
from typing import Dict, Any

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel, HttpUrl

from ..utils.audio_utils import (
    process_audio_for_enrollment,
    AudioDownloadError,
    AudioProcessingError,
    get_audio_duration,
    validate_audio_format
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/audio", tags=["audio"])


class AudioProcessRequest(BaseModel):
    """Request model for audio processing."""
    audio_url: HttpUrl
    

class AudioProcessResponse(BaseModel):
    """Response model for audio processing."""
    success: bool
    message: str
    duration_seconds: float = None
    audio_size_bytes: int = None
    format_valid: bool = None


class AudioTestResponse(BaseModel):
    """Response model for audio test endpoint."""
    status: str
    message: str
    audio_utils_available: bool
    ffmpeg_available: bool


@router.get("/test", response_model=AudioTestResponse)
async def test_audio_processing() -> AudioTestResponse:
    """Test audio processing capabilities."""
    try:
        # Test if ffmpeg is available
        import subprocess
        result = subprocess.run(['ffmpeg', '-version'], 
                              capture_output=True, text=True, timeout=5)
        ffmpeg_available = result.returncode == 0
    except Exception:
        ffmpeg_available = False
    
    return AudioTestResponse(
        status="ok",
        message="Audio processing test completed",
        audio_utils_available=True,
        ffmpeg_available=ffmpeg_available
    )


@router.post("/process", response_model=AudioProcessResponse)
async def process_audio(request: AudioProcessRequest) -> AudioProcessResponse:
    """
    Process audio file from URL for voice authentication.
    
    Downloads audio from the provided URL and converts it to 16kHz mono WAV format.
    """
    try:
        logger.info(f"Processing audio from URL: {request.audio_url}")
        
        # Process the audio
        processed_audio = await process_audio_for_enrollment(str(request.audio_url))
        
        # Get audio information
        duration = get_audio_duration(processed_audio)
        is_valid, validation_msg = validate_audio_format(processed_audio)
        
        logger.info(f"Audio processing completed successfully. Duration: {duration}s, Size: {len(processed_audio)} bytes")
        
        return AudioProcessResponse(
            success=True,
            message=f"Audio processed successfully. {validation_msg}",
            duration_seconds=duration,
            audio_size_bytes=len(processed_audio),
            format_valid=is_valid
        )
        
    except AudioDownloadError as e:
        logger.error(f"Audio download failed: {e}")
        raise HTTPException(status_code=400, detail=f"Failed to download audio: {str(e)}")
        
    except AudioProcessingError as e:
        logger.error(f"Audio processing failed: {e}")
        raise HTTPException(status_code=422, detail=f"Failed to process audio: {str(e)}")
        
    except Exception as e:
        logger.error(f"Unexpected error processing audio: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/formats")
async def get_supported_formats() -> Dict[str, Any]:
    """Get information about supported audio formats."""
    return {
        "input_formats": [
            "mp3", "wav", "m4a", "aac", "ogg", "flac", "wma"
        ],
        "output_format": "wav",
        "output_specs": {
            "sample_rate": "16kHz",
            "channels": "mono (1)",
            "bit_depth": "16-bit",
            "encoding": "PCM"
        },
        "max_duration_seconds": 30,
        "max_file_size_mb": 50
    }