"""
Audio processing utilities for voice authentication.

This module provides functions for:
- Downloading audio files from URLs
- Converting audio formats using ffmpeg
- PCM to WAV conversion
- Audio format standardization to 16kHz mono
"""

import asyncio
import io
import logging
import struct
import tempfile
from pathlib import Path
from typing import Optional, Tuple

import ffmpeg
import httpx
import numpy as np

logger = logging.getLogger(__name__)


class AudioProcessingError(Exception):
    """Raised when audio processing operations fail."""
    pass


class AudioDownloadError(Exception):
    """Raised when audio download operations fail."""
    pass


async def download_audio_file(url: str, timeout: int = 30) -> bytes:
    """
    Download audio file from URL using httpx.
    
    Args:
        url: URL to download audio from
        timeout: Request timeout in seconds
        
    Returns:
        Audio file content as bytes
        
    Raises:
        AudioDownloadError: If download fails
    """
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            logger.info(f"Downloading audio from URL: {url}")
            response = await client.get(url)
            response.raise_for_status()
            
            content_length = len(response.content)
            logger.info(f"Downloaded {content_length} bytes of audio data")
            
            if content_length == 0:
                raise AudioDownloadError("Downloaded audio file is empty")
                
            return response.content
            
    except httpx.TimeoutException as e:
        logger.error(f"Timeout downloading audio from {url}: {e}")
        raise AudioDownloadError(f"Timeout downloading audio: {e}")
    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error downloading audio from {url}: {e}")
        raise AudioDownloadError(f"HTTP error downloading audio: {e.response.status_code}")
    except Exception as e:
        logger.error(f"Unexpected error downloading audio from {url}: {e}")
        raise AudioDownloadError(f"Failed to download audio: {e}")


def pcm_to_wav(pcm_data: bytes, sample_rate: int = 16000, channels: int = 1, 
               sample_width: int = 2) -> bytes:
    """
    Convert PCM audio data to WAV format.
    
    Args:
        pcm_data: Raw PCM audio data
        sample_rate: Sample rate in Hz (default: 16000)
        channels: Number of audio channels (default: 1 for mono)
        sample_width: Sample width in bytes (default: 2 for 16-bit)
        
    Returns:
        WAV formatted audio data as bytes
        
    Raises:
        AudioProcessingError: If conversion fails
    """
    try:
        if not pcm_data:
            raise AudioProcessingError("PCM data is empty")
            
        # Calculate WAV header parameters
        data_size = len(pcm_data)
        file_size = data_size + 36  # 44 byte header - 8 bytes
        byte_rate = sample_rate * channels * sample_width
        block_align = channels * sample_width
        
        # Create WAV header
        wav_header = struct.pack(
            '<4sI4s4sIHHIIHH4sI',
            b'RIFF',           # Chunk ID
            file_size,         # Chunk size
            b'WAVE',           # Format
            b'fmt ',           # Subchunk1 ID
            16,                # Subchunk1 size (PCM)
            1,                 # Audio format (PCM)
            channels,          # Number of channels
            sample_rate,       # Sample rate
            byte_rate,         # Byte rate
            block_align,       # Block align
            sample_width * 8,  # Bits per sample
            b'data',           # Subchunk2 ID
            data_size          # Subchunk2 size
        )
        
        wav_data = wav_header + pcm_data
        logger.info(f"Converted {len(pcm_data)} bytes PCM to {len(wav_data)} bytes WAV")
        
        return wav_data
        
    except struct.error as e:
        logger.error(f"Error creating WAV header: {e}")
        raise AudioProcessingError(f"Failed to create WAV header: {e}")
    except Exception as e:
        logger.error(f"Unexpected error in PCM to WAV conversion: {e}")
        raise AudioProcessingError(f"PCM to WAV conversion failed: {e}")


async def convert_to_16khz_mono(audio_data: bytes, input_format: Optional[str] = None) -> bytes:
    """
    Convert audio to 16kHz mono WAV format using ffmpeg.
    
    Args:
        audio_data: Input audio data as bytes
        input_format: Input format hint (e.g., 'mp3', 'wav'). If None, ffmpeg will auto-detect.
        
    Returns:
        Converted audio data as 16kHz mono WAV bytes
        
    Raises:
        AudioProcessingError: If conversion fails
    """
    if not audio_data:
        raise AudioProcessingError("Audio data is empty")
        
    try:
        # Create temporary files for input and output
        with tempfile.NamedTemporaryFile(suffix=f'.{input_format or "audio"}') as input_file, \
             tempfile.NamedTemporaryFile(suffix='.wav') as output_file:
            
            # Write input data to temporary file
            input_file.write(audio_data)
            input_file.flush()
            
            logger.info(f"Converting audio to 16kHz mono WAV using ffmpeg")
            
            # Use ffmpeg to convert audio
            stream = ffmpeg.input(input_file.name)
            stream = ffmpeg.output(
                stream,
                output_file.name,
                acodec='pcm_s16le',  # 16-bit PCM
                ac=1,                # Mono (1 channel)
                ar=16000,            # 16kHz sample rate
                f='wav'              # WAV format
            )
            
            # Run ffmpeg conversion
            ffmpeg.run(stream, overwrite_output=True, quiet=True)
            
            # Read converted audio data
            output_file.seek(0)
            converted_data = output_file.read()
            
            if not converted_data:
                raise AudioProcessingError("ffmpeg conversion produced empty output")
                
            logger.info(f"Converted {len(audio_data)} bytes to {len(converted_data)} bytes (16kHz mono WAV)")
            
            return converted_data
            
    except ffmpeg.Error as e:
        error_msg = e.stderr.decode() if e.stderr else str(e)
        logger.error(f"ffmpeg conversion failed: {error_msg}")
        raise AudioProcessingError(f"Audio conversion failed: {error_msg}")
    except Exception as e:
        logger.error(f"Unexpected error in audio conversion: {e}")
        raise AudioProcessingError(f"Audio conversion failed: {e}")


def validate_audio_format(audio_data: bytes) -> Tuple[bool, str]:
    """
    Validate if audio data is in expected format (16kHz mono WAV).
    
    Args:
        audio_data: Audio data to validate
        
    Returns:
        Tuple of (is_valid, description)
    """
    try:
        if len(audio_data) < 44:
            return False, "Audio data too short to contain WAV header"
            
        # Check WAV header
        if audio_data[:4] != b'RIFF' or audio_data[8:12] != b'WAVE':
            return False, "Not a valid WAV file"
            
        # Extract format information from WAV header
        channels = struct.unpack('<H', audio_data[22:24])[0]
        sample_rate = struct.unpack('<I', audio_data[24:28])[0]
        bits_per_sample = struct.unpack('<H', audio_data[34:36])[0]
        
        if channels != 1:
            return False, f"Expected mono (1 channel), got {channels} channels"
            
        if sample_rate != 16000:
            return False, f"Expected 16kHz sample rate, got {sample_rate}Hz"
            
        if bits_per_sample != 16:
            return False, f"Expected 16-bit samples, got {bits_per_sample}-bit"
            
        return True, "Valid 16kHz mono WAV format"
        
    except (struct.error, IndexError) as e:
        return False, f"Error parsing WAV header: {e}"
    except Exception as e:
        return False, f"Validation error: {e}"


async def process_audio_for_enrollment(audio_url: str) -> bytes:
    """
    Complete audio processing pipeline for user enrollment.
    
    Downloads audio from URL and converts to 16kHz mono WAV format.
    
    Args:
        audio_url: URL to download audio from
        
    Returns:
        Processed audio data as 16kHz mono WAV bytes
        
    Raises:
        AudioDownloadError: If download fails
        AudioProcessingError: If processing fails
    """
    logger.info(f"Starting audio processing pipeline for enrollment: {audio_url}")
    
    # Download audio file
    audio_data = await download_audio_file(audio_url)
    
    # Convert to 16kHz mono WAV
    processed_audio = await convert_to_16khz_mono(audio_data)
    
    # Validate the result
    is_valid, description = validate_audio_format(processed_audio)
    if not is_valid:
        raise AudioProcessingError(f"Processed audio validation failed: {description}")
        
    logger.info(f"Audio processing pipeline completed successfully: {description}")
    
    return processed_audio


def get_audio_duration(audio_data: bytes) -> float:
    """
    Get duration of WAV audio data in seconds.
    
    Args:
        audio_data: WAV audio data
        
    Returns:
        Duration in seconds
        
    Raises:
        AudioProcessingError: If unable to determine duration
    """
    try:
        if len(audio_data) < 44:
            raise AudioProcessingError("Audio data too short to contain WAV header")
            
        # Extract format information
        channels = struct.unpack('<H', audio_data[22:24])[0]
        sample_rate = struct.unpack('<I', audio_data[24:28])[0]
        bits_per_sample = struct.unpack('<H', audio_data[34:36])[0]
        
        # Calculate data size (total size - header size)
        data_size = len(audio_data) - 44
        
        # Calculate duration
        bytes_per_sample = bits_per_sample // 8
        samples_per_second = sample_rate * channels
        bytes_per_second = samples_per_second * bytes_per_sample
        
        duration = data_size / bytes_per_second
        
        return duration
        
    except (struct.error, IndexError, ZeroDivisionError) as e:
        raise AudioProcessingError(f"Error calculating audio duration: {e}")