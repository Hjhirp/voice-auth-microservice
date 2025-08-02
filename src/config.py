"""Configuration management for the voice authentication microservice."""

import os
from typing import Optional
from pydantic import validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Server configuration
    port: int = 8000
    host: str = "0.0.0.0"
    
    # Supabase configuration
    supabase_url: str
    supabase_anon_key: str
    
    # External data API (removed until auth is successful)
    # data_url: str
    
    # Voice authentication settings
    voice_threshold: float = 0.82
    max_audio_duration: int = 30
    websocket_timeout: int = 65
    
    # Logging configuration
    log_level: str = "INFO"
    
    @validator('supabase_url')
    def validate_supabase_url(cls, v):
        if not v:
            raise ValueError('SUPABASE_URL environment variable is required')
        return v
    
    @validator('supabase_anon_key')
    def validate_supabase_anon_key(cls, v):
        if not v:
            raise ValueError('SUPABASE_ANON_KEY environment variable is required')
        return v
    
    # @validator('data_url')
    # def validate_data_url(cls, v):
    #     if not v:
    #         raise ValueError('DATA_URL environment variable is required')
    #     return v
    
    @validator('voice_threshold')
    def validate_voice_threshold(cls, v):
        if not 0.0 <= v <= 1.0:
            raise ValueError('VOICE_THRESHOLD must be between 0.0 and 1.0')
        return v
    
    class Config:
        env_file = ".env"
        case_sensitive = False


# Global settings instance
settings = Settings()