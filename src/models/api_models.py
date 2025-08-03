"""Pydantic models for API requests and responses."""

from datetime import datetime
from typing import Dict, List, Optional

from pydantic import BaseModel, Field, field_validator


class EnrollmentRequest(BaseModel):
    """Request model for user enrollment endpoint."""
    
    phone: str = Field(..., min_length=10, max_length=20, description="User's phone number (unique identifier)")
    audioUrl: str = Field(..., description="URL to download the enrollment audio file")
    
    @field_validator('phone')
    @classmethod
    def validate_phone(cls, v):
        """Validate phone number format."""
        # Remove common phone number characters
        cleaned = ''.join(c for c in v if c.isdigit() or c in '+()-. ')
        if len(cleaned.replace(' ', '').replace('-', '').replace('(', '').replace(')', '').replace('+', '').replace('.', '')) < 10:
            raise ValueError('Phone number must contain at least 10 digits')
        return v
    
    @field_validator('audioUrl')
    @classmethod
    def validate_audio_url(cls, v):
        """Validate audio URL format."""
        if not v.startswith(('http://', 'https://')):
            raise ValueError('Audio URL must be a valid HTTP/HTTPS URL')
        return v


class EnrollmentResponse(BaseModel):
    """Response model for user enrollment endpoint."""
    
    status: str = Field(..., description="Enrollment status")
    score: float = Field(..., ge=0.0, le=1.0, description="Enrollment confidence score")
    
    class Config:
        schema_extra = {
            "example": {
                "status": "enrolled",
                "score": 1.0
            }
        }


class VerificationRequest(BaseModel):
    """Request model for password verification endpoint."""
    
    phone: str = Field(..., min_length=10, max_length=20, description="User's phone number (unique identifier)")
    listenUrl: str = Field(..., description="WebSocket URL for live audio capture")
    
    @field_validator('listenUrl')
    @classmethod
    def validate_listen_url(cls, v):
        """Validate WebSocket URL format."""
        if not v.startswith(('ws://', 'wss://')):
            raise ValueError('Listen URL must be a valid WebSocket URL (ws:// or wss://)')
        return v


class VerificationResponse(BaseModel):
    """Response model for password verification endpoint."""
    
    success: bool = Field(..., description="Whether verification was successful")
    message: str = Field(..., description="Human-readable verification result message")
    records: Optional[List[Dict]] = Field(None, description="User records to be spoken by VAPI (only on success)")
    score: Optional[float] = Field(None, ge=0.0, le=1.0, description="Voice similarity score")
    
    class Config:
        schema_extra = {
            "example": {
                "success": True,
                "message": "Voice verification successful",
                "records": [{"field": "value"}],
                "score": 0.89
            }
        }


class HealthResponse(BaseModel):
    """Response model for health check endpoint."""
    
    status: str = Field(..., description="Service health status")
    timestamp: datetime = Field(..., description="Health check timestamp")
    version: str = Field(..., description="Service version")
    
    class Config:
        schema_extra = {
            "example": {
                "status": "healthy",
                "timestamp": "2024-01-01T12:00:00Z",
                "version": "1.0.0"
            }
        }


class ErrorResponse(BaseModel):
    """Standard error response model."""
    
    error: str = Field(..., description="Error type or category")
    message: str = Field(..., description="Human-readable error message")
    correlation_id: str = Field(..., description="Request correlation ID for tracing")
    timestamp: datetime = Field(..., description="Error timestamp")
    
    class Config:
        schema_extra = {
            "example": {
                "error": "ValidationError",
                "message": "Invalid request format",
                "correlation_id": "req_123456789",
                "timestamp": "2024-01-01T12:00:00Z"
            }
        }