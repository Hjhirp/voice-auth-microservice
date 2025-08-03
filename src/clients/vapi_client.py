"""
VAPI WebSocket client for live audio capture.

This module provides WebSocket connectivity to VAPI for capturing live audio streams
with silence detection and buffering capabilities.
"""

import asyncio
import logging
import time
from typing import Optional, Callable, List
import json

import websockets
from websockets.exceptions import ConnectionClosed, WebSocketException
import numpy as np

from src.utils.audio_utils import pcm_to_wav

logger = logging.getLogger(__name__)


class VAPIConnectionError(Exception):
    """Raised when VAPI WebSocket connection fails."""
    pass


class VAPIAudioError(Exception):
    """Raised when VAPI audio processing fails."""
    pass


class VAPIWebSocketClient:
    """
    WebSocket client for capturing live audio from VAPI.
    
    Handles connection lifecycle, audio buffering, and silence detection
    for voice authentication workflows.
    """
    
    def __init__(
        self,
        listen_url: str,
        sample_rate: int = 16000,
        channels: int = 1,
        sample_width: int = 2,
        silence_threshold: float = 0.01,
        silence_duration: float = 2.0,
        max_audio_duration: float = 30.0,
        connection_timeout: float = 10.0
    ):
        """
        Initialize VAPI WebSocket client.
        
        Args:
            listen_url: WebSocket URL to connect to
            sample_rate: Audio sample rate in Hz (default: 16000)
            channels: Number of audio channels (default: 1 for mono)
            sample_width: Sample width in bytes (default: 2 for 16-bit)
            silence_threshold: RMS threshold for silence detection (default: 0.01)
            silence_duration: Duration of silence to trigger stop (default: 2.0 seconds)
            max_audio_duration: Maximum audio capture duration (default: 30.0 seconds)
            connection_timeout: WebSocket connection timeout (default: 10.0 seconds)
        """
        self.listen_url = listen_url
        self.sample_rate = sample_rate
        self.channels = channels
        self.sample_width = sample_width
        self.silence_threshold = silence_threshold
        self.silence_duration = silence_duration
        self.max_audio_duration = max_audio_duration
        self.connection_timeout = connection_timeout
        
        # Audio buffering
        self.audio_buffer: List[bytes] = []
        self.silence_start_time: Optional[float] = None
        self.capture_start_time: Optional[float] = None
        
        # Connection state
        self.websocket: Optional[websockets.WebSocketServerProtocol] = None
        self.is_connected = False
        self.is_capturing = False
        
        logger.info(f"Initialized VAPI client for URL: {listen_url}")

    async def connect(self) -> None:
        """
        Establish WebSocket connection to VAPI.
        
        Raises:
            VAPIConnectionError: If connection fails
        """
        try:
            logger.info(f"Connecting to VAPI WebSocket: {self.listen_url}")
            
            self.websocket = await asyncio.wait_for(
                websockets.connect(
                    self.listen_url,
                    ping_interval=20,
                    ping_timeout=10,
                    close_timeout=10
                ),
                timeout=self.connection_timeout
            )
            
            self.is_connected = True
            logger.info("Successfully connected to VAPI WebSocket")
            
        except asyncio.TimeoutError:
            logger.error(f"Timeout connecting to VAPI WebSocket: {self.listen_url}")
            raise VAPIConnectionError(f"Connection timeout after {self.connection_timeout}s")
        except WebSocketException as e:
            logger.error(f"WebSocket error connecting to VAPI: {e}")
            raise VAPIConnectionError(f"WebSocket connection failed: {e}")
        except Exception as e:
            logger.error(f"Unexpected error connecting to VAPI: {e}")
            raise VAPIConnectionError(f"Connection failed: {e}")

    async def disconnect(self) -> None:
        """
        Close WebSocket connection gracefully.
        """
        if self.websocket and self.is_connected:
            try:
                logger.info("Closing VAPI WebSocket connection")
                await self.websocket.close()
            except Exception as e:
                logger.warning(f"Error closing WebSocket connection: {e}")
            finally:
                self.is_connected = False
                self.websocket = None

    def _detect_silence(self, audio_chunk: bytes) -> bool:
        """
        Detect if audio chunk contains silence based on RMS threshold.
        
        Args:
            audio_chunk: Raw PCM audio data
            
        Returns:
            True if audio is considered silence, False otherwise
        """
        try:
            # Convert bytes to numpy array (assuming 16-bit PCM)
            if len(audio_chunk) < 2:
                return True
                
            # Convert to numpy array of 16-bit integers
            audio_data = np.frombuffer(audio_chunk, dtype=np.int16)
            
            # Calculate RMS (Root Mean Square) amplitude
            rms = np.sqrt(np.mean(audio_data.astype(np.float32) ** 2))
            
            # Normalize RMS to 0-1 range (16-bit max is 32767)
            normalized_rms = rms / 32767.0
            
            is_silence = normalized_rms < self.silence_threshold
            
            if is_silence:
                logger.debug(f"Silence detected: RMS={normalized_rms:.4f} < threshold={self.silence_threshold}")
            else:
                logger.debug(f"Audio detected: RMS={normalized_rms:.4f} >= threshold={self.silence_threshold}")
                
            return is_silence
            
        except Exception as e:
            logger.warning(f"Error in silence detection: {e}")
            return False  # Assume not silence if detection fails

    def _should_stop_capture(self) -> bool:
        """
        Determine if audio capture should stop based on silence duration or max duration.
        
        Returns:
            True if capture should stop, False otherwise
        """
        current_time = time.time()
        
        # Check maximum duration
        if self.capture_start_time and (current_time - self.capture_start_time) >= self.max_audio_duration:
            logger.info(f"Stopping capture: maximum duration ({self.max_audio_duration}s) reached")
            return True
            
        # Check silence duration
        if self.silence_start_time and (current_time - self.silence_start_time) >= self.silence_duration:
            logger.info(f"Stopping capture: silence duration ({self.silence_duration}s) reached")
            return True
            
        return False

    async def _process_audio_message(self, message: str) -> bool:
        """
        Process incoming WebSocket audio message.
        
        Args:
            message: WebSocket message (expected to be JSON with audio data)
            
        Returns:
            True if capture should continue, False if it should stop
        """
        try:
            # Parse JSON message
            data = json.loads(message)
            
            # Extract audio data (assuming base64 encoded PCM)
            if 'audio' not in data:
                logger.debug("Received message without audio data")
                return True
                
            import base64
            audio_chunk = base64.b64decode(data['audio'])
            
            if not audio_chunk:
                logger.debug("Received empty audio chunk")
                return True
                
            # Add to buffer
            self.audio_buffer.append(audio_chunk)
            
            # Detect silence
            is_silence = self._detect_silence(audio_chunk)
            current_time = time.time()
            
            if is_silence:
                # Start or continue silence timer
                if self.silence_start_time is None:
                    self.silence_start_time = current_time
                    logger.debug("Started silence timer")
            else:
                # Reset silence timer on audio activity
                if self.silence_start_time is not None:
                    logger.debug("Reset silence timer due to audio activity")
                    self.silence_start_time = None
                    
            # Check if we should stop capture
            return not self._should_stop_capture()
            
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse WebSocket message as JSON: {e}")
            return True  # Continue capture
        except Exception as e:
            logger.error(f"Error processing audio message: {e}")
            return True  # Continue capture

    async def capture_audio(self, min_duration: float = 3.0) -> bytes:
        """
        Capture audio from VAPI WebSocket with silence detection.
        
        Captures audio until either:
        - Silence is detected for the configured duration
        - Maximum audio duration is reached
        - Minimum duration is satisfied and silence is detected
        
        Args:
            min_duration: Minimum capture duration in seconds (default: 3.0)
            
        Returns:
            Captured audio data as WAV bytes
            
        Raises:
            VAPIConnectionError: If not connected or connection fails
            VAPIAudioError: If audio capture fails
        """
        if not self.is_connected or not self.websocket:
            raise VAPIConnectionError("Not connected to VAPI WebSocket")
            
        try:
            logger.info(f"Starting audio capture (min: {min_duration}s, max: {self.max_audio_duration}s)")
            
            # Reset capture state
            self.audio_buffer.clear()
            self.silence_start_time = None
            self.capture_start_time = time.time()
            self.is_capturing = True
            
            # Capture loop
            async for message in self.websocket:
                if not await self._process_audio_message(message):
                    break
                    
                # Check minimum duration before allowing silence-based stop
                elapsed = time.time() - self.capture_start_time
                if elapsed < min_duration and self.silence_start_time:
                    # Reset silence timer if we haven't reached minimum duration
                    self.silence_start_time = None
                    logger.debug(f"Reset silence timer: minimum duration not reached ({elapsed:.1f}s < {min_duration}s)")
                    
            self.is_capturing = False
            
            # Combine audio buffer
            if not self.audio_buffer:
                raise VAPIAudioError("No audio data captured")
                
            combined_pcm = b''.join(self.audio_buffer)
            total_duration = time.time() - self.capture_start_time
            
            logger.info(f"Audio capture completed: {len(combined_pcm)} bytes, {total_duration:.1f}s duration")
            
            # Convert PCM to WAV format
            wav_data = pcm_to_wav(
                combined_pcm,
                sample_rate=self.sample_rate,
                channels=self.channels,
                sample_width=self.sample_width
            )
            
            return wav_data
            
        except ConnectionClosed as e:
            logger.error(f"WebSocket connection closed during capture: {e}")
            raise VAPIConnectionError(f"Connection closed during capture: {e}")
        except WebSocketException as e:
            logger.error(f"WebSocket error during capture: {e}")
            raise VAPIConnectionError(f"WebSocket error during capture: {e}")
        except Exception as e:
            logger.error(f"Unexpected error during audio capture: {e}")
            raise VAPIAudioError(f"Audio capture failed: {e}")
        finally:
            self.is_capturing = False

    async def __aenter__(self):
        """Async context manager entry."""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.disconnect()


async def capture_audio_from_vapi(
    listen_url: str,
    min_duration: float = 3.0,
    silence_threshold: float = 0.01,
    silence_duration: float = 2.0,
    max_duration: float = 30.0,
    connection_timeout: float = 10.0
) -> bytes:
    """
    Convenience function to capture audio from VAPI WebSocket.
    
    Args:
        listen_url: VAPI WebSocket URL
        min_duration: Minimum capture duration in seconds
        silence_threshold: RMS threshold for silence detection
        silence_duration: Duration of silence to trigger stop
        max_duration: Maximum capture duration
        connection_timeout: WebSocket connection timeout
        
    Returns:
        Captured audio as WAV bytes
        
    Raises:
        VAPIConnectionError: If connection fails
        VAPIAudioError: If audio capture fails
    """
    async with VAPIWebSocketClient(
        listen_url=listen_url,
        silence_threshold=silence_threshold,
        silence_duration=silence_duration,
        max_audio_duration=max_duration,
        connection_timeout=connection_timeout
    ) as client:
        return await client.capture_audio(min_duration=min_duration)