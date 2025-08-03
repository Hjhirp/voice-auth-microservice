"""Configuration management for the voice authentication microservice."""

import os
from typing import Optional
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False,
        extra="ignore"  # Ignore extra environment variables
    )
    
    # Server configuration
    port: int = 8000
    host: str = "0.0.0.0"
    
    # Supabase configuration
    supabase_url: str = "https://uwkkunglqsccaskobeva.supabase.co"
    supabase_anon_key: str = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InV3a2t1bmdscXNjY2Fza29iZXZhIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTQxNjgzNzEsImV4cCI6MjA2OTc0NDM3MX0.koxmEqBV-CQAgwBhmTrVzveUbWrCiq_JZHlD7Z9A4Mg"
    
    # Voice authentication settings
    voice_threshold: float = 0.82
    max_audio_duration: int = 30
    websocket_timeout: int = 65
    
    # Logging configuration
    log_level: str = "INFO"
    
    @field_validator('supabase_url')
    @classmethod
    def validate_supabase_url(cls, v):
        if not v:
            raise ValueError('SUPABASE_URL environment variable is required')
        return v
    
    @field_validator('supabase_anon_key')
    @classmethod
    def validate_supabase_anon_key(cls, v):
        if not v:
            raise ValueError('SUPABASE_ANON_KEY environment variable is required')
        return v
    
    @field_validator('voice_threshold')
    @classmethod
    def validate_voice_threshold(cls, v):
        if not 0.0 <= v <= 1.0:
            raise ValueError('VOICE_THRESHOLD must be between 0.0 and 1.0')
        return v


# Global settings instance
settings = Settings()