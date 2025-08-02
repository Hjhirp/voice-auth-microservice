"""
Tests for VAPI WebSocket client.
"""

import asyncio
import json
import base64
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import numpy as np

from src.clients.vapi_client import (
    VAPIWebSocketClient,
    VAPIConnectionError,
    VAPIAudioError,
    capture_audio_from_vapi,
)


class TestVAPIWebSocketClient:
    """Test cases for VAPI WebSocket client."""

    def test_init(self):
        """Test client initialization."""
        client = VAPIWebSocketClient("ws://example.com/listen")
        
        assert client.listen_url == "ws://example.com/listen"
        assert client.sample_rate == 16000
        assert client.channels == 1
        assert client.sample_width == 2
        assert client.silence_threshold == 0.01
        assert client.silence_duration == 2.0
        assert client.max_audio_duration == 30.0
        assert client.connection_timeout == 10.0
        assert not client.is_connected
        assert not client.is_capturing

    def test_detect_silence_with_silence(self):
        """Test silence detection with silent audio."""
        client = VAPIWebSocketClient("ws://example.com/listen")
        
        # Create silent audio (all zeros)
        silent_audio = b'\x00\x00' * 100  # 100 samples of silence
        
        is_silence = client._detect_silence(silent_audio)
        assert is_silence == True

    def test_detect_silence_with_audio(self):
        """Test silence detection with actual audio."""
        client = VAPIWebSocketClient("ws://example.com/listen")
        
        # Create audio with some amplitude
        audio_samples = np.random.randint(-1000, 1000, 100, dtype=np.int16)
        audio_bytes = audio_samples.tobytes()
        
        is_silence = client._detect_silence(audio_bytes)
        assert is_silence == False

    def test_detect_silence_empty_chunk(self):
        """Test silence detection with empty audio chunk."""
        client = VAPIWebSocketClient("ws://example.com/listen")
        
        is_silence = client._detect_silence(b'')
        assert is_silence is True

    def test_should_stop_capture_max_duration(self):
        """Test capture stop condition based on maximum duration."""
        client = VAPIWebSocketClient("ws://example.com/listen", max_audio_duration=1.0)
        
        # Simulate capture start
        import time
        client.capture_start_time = time.time() - 2.0  # 2 seconds ago
        
        should_stop = client._should_stop_capture()
        assert should_stop is True

    def test_should_stop_capture_silence_duration(self):
        """Test capture stop condition based on silence duration."""
        client = VAPIWebSocketClient("ws://example.com/listen", silence_duration=1.0)
        
        # Simulate silence start
        import time
        client.silence_start_time = time.time() - 2.0  # 2 seconds ago
        
        should_stop = client._should_stop_capture()
        assert should_stop is True

    def test_should_stop_capture_continue(self):
        """Test capture continue condition."""
        client = VAPIWebSocketClient("ws://example.com/listen")
        
        # No timers set
        should_stop = client._should_stop_capture()
        assert should_stop is False

    @pytest.mark.asyncio
    async def test_process_audio_message_valid(self):
        """Test processing valid audio message."""
        client = VAPIWebSocketClient("ws://example.com/listen")
        
        # Create test audio data
        audio_data = b'\x00\x00' * 100  # Silent audio
        encoded_audio = base64.b64encode(audio_data).decode()
        
        message = json.dumps({"audio": encoded_audio})
        
        should_continue = await client._process_audio_message(message)
        
        assert should_continue is True
        assert len(client.audio_buffer) == 1
        assert client.audio_buffer[0] == audio_data

    @pytest.mark.asyncio
    async def test_process_audio_message_no_audio(self):
        """Test processing message without audio data."""
        client = VAPIWebSocketClient("ws://example.com/listen")
        
        message = json.dumps({"type": "status", "status": "connected"})
        
        should_continue = await client._process_audio_message(message)
        
        assert should_continue is True
        assert len(client.audio_buffer) == 0

    @pytest.mark.asyncio
    async def test_process_audio_message_invalid_json(self):
        """Test processing invalid JSON message."""
        client = VAPIWebSocketClient("ws://example.com/listen")
        
        message = "invalid json"
        
        should_continue = await client._process_audio_message(message)
        
        assert should_continue is True
        assert len(client.audio_buffer) == 0

    @pytest.mark.asyncio
    async def test_connect_success(self):
        """Test successful WebSocket connection."""
        client = VAPIWebSocketClient("ws://example.com/listen")
        
        mock_websocket = MagicMock()
        
        with patch('websockets.connect', new_callable=AsyncMock) as mock_connect:
            mock_connect.return_value = mock_websocket
            
            await client.connect()
            
            assert client.is_connected is True
            assert client.websocket == mock_websocket
            mock_connect.assert_called_once()

    @pytest.mark.asyncio
    async def test_connect_timeout(self):
        """Test WebSocket connection timeout."""
        client = VAPIWebSocketClient("ws://example.com/listen", connection_timeout=0.1)
        
        with patch('websockets.connect', new_callable=AsyncMock) as mock_connect:
            mock_connect.side_effect = asyncio.TimeoutError()
            
            with pytest.raises(VAPIConnectionError, match="Connection timeout"):
                await client.connect()
            
            assert client.is_connected is False

    @pytest.mark.asyncio
    async def test_disconnect(self):
        """Test WebSocket disconnection."""
        client = VAPIWebSocketClient("ws://example.com/listen")
        
        # Set up connected state
        mock_websocket = MagicMock()
        mock_websocket.close = AsyncMock()
        client.websocket = mock_websocket
        client.is_connected = True
        
        await client.disconnect()
        
        assert client.is_connected is False
        assert client.websocket is None
        mock_websocket.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_capture_audio_not_connected(self):
        """Test audio capture when not connected."""
        client = VAPIWebSocketClient("ws://example.com/listen")
        
        with pytest.raises(VAPIConnectionError, match="Not connected"):
            await client.capture_audio()

    @pytest.mark.asyncio
    async def test_capture_audio_success(self):
        """Test successful audio capture."""
        client = VAPIWebSocketClient("ws://example.com/listen", silence_duration=0.1)
        
        # Create test audio data
        audio_data = b'\x00\x00' * 1000  # Silent audio
        encoded_audio = base64.b64encode(audio_data).decode()
        messages = [json.dumps({"audio": encoded_audio})] * 5
        
        # Mock WebSocket with proper async iterator
        async def mock_aiter(self):
            for message in messages:
                yield message
        
        mock_websocket = MagicMock()
        mock_websocket.__aiter__ = mock_aiter
        
        client.websocket = mock_websocket
        client.is_connected = True
        
        with patch('src.clients.vapi_client.pcm_to_wav') as mock_pcm_to_wav:
            mock_pcm_to_wav.return_value = b'fake_wav_data'
            
            result = await client.capture_audio(min_duration=0.1)
            
            assert result == b'fake_wav_data'
            assert not client.is_capturing
            mock_pcm_to_wav.assert_called_once()

    @pytest.mark.asyncio
    async def test_capture_audio_no_data(self):
        """Test audio capture with no audio data."""
        client = VAPIWebSocketClient("ws://example.com/listen")
        
        # Mock WebSocket with no audio messages
        async def mock_aiter(self):
            return
            yield  # This will never execute
        
        mock_websocket = MagicMock()
        mock_websocket.__aiter__ = mock_aiter
        
        client.websocket = mock_websocket
        client.is_connected = True
        
        with pytest.raises(VAPIAudioError, match="No audio data captured"):
            await client.capture_audio()

    @pytest.mark.asyncio
    async def test_context_manager(self):
        """Test async context manager functionality."""
        mock_websocket = MagicMock()
        mock_websocket.close = AsyncMock()
        
        with patch('websockets.connect', new_callable=AsyncMock) as mock_connect:
            mock_connect.return_value = mock_websocket
            
            async with VAPIWebSocketClient("ws://example.com/listen") as client:
                assert client.is_connected is True
                assert client.websocket == mock_websocket
            
            # Should be disconnected after context exit
            mock_websocket.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_capture_audio_from_vapi_convenience_function(self):
        """Test convenience function for audio capture."""
        mock_websocket = MagicMock()
        mock_websocket.close = AsyncMock()
        
        # Create test audio data
        audio_data = b'\x00\x00' * 1000
        encoded_audio = base64.b64encode(audio_data).decode()
        messages = [json.dumps({"audio": encoded_audio})] * 3
        
        async def mock_aiter(self):
            for message in messages:
                yield message
        
        mock_websocket.__aiter__ = mock_aiter
        
        with patch('websockets.connect', new_callable=AsyncMock) as mock_connect, \
             patch('src.clients.vapi_client.pcm_to_wav') as mock_pcm_to_wav:
            
            mock_connect.return_value = mock_websocket
            mock_pcm_to_wav.return_value = b'fake_wav_data'
            
            result = await capture_audio_from_vapi(
                "ws://example.com/listen",
                min_duration=0.1,
                silence_duration=0.1
            )
            
            assert result == b'fake_wav_data'
            mock_connect.assert_called_once()
            mock_websocket.close.assert_called_once()