"""
Tests for audio processing utilities.
"""

import pytest
import struct
from unittest.mock import AsyncMock, patch, MagicMock

from src.utils.audio_utils import (
    AudioDownloadError,
    AudioProcessingError,
    download_audio_file,
    pcm_to_wav,
    validate_audio_format,
    get_audio_duration,
    convert_to_16khz_mono,
    process_audio_for_enrollment,
)


class TestAudioUtils:
    """Test cases for audio utility functions."""

    def test_pcm_to_wav_conversion(self):
        """Test PCM to WAV conversion with valid data."""
        # Create sample PCM data (1 second of silence at 16kHz, 16-bit mono)
        sample_rate = 16000
        duration = 1.0
        samples = int(sample_rate * duration)
        pcm_data = b'\x00\x00' * samples  # 16-bit silence
        
        wav_data = pcm_to_wav(pcm_data, sample_rate=sample_rate)
        
        # Verify WAV header
        assert wav_data[:4] == b'RIFF'
        assert wav_data[8:12] == b'WAVE'
        assert len(wav_data) == len(pcm_data) + 44  # PCM data + 44 byte header
        
        # Verify format parameters in header
        channels = struct.unpack('<H', wav_data[22:24])[0]
        rate = struct.unpack('<I', wav_data[24:28])[0]
        bits_per_sample = struct.unpack('<H', wav_data[34:36])[0]
        
        assert channels == 1
        assert rate == sample_rate
        assert bits_per_sample == 16

    def test_pcm_to_wav_empty_data(self):
        """Test PCM to WAV conversion with empty data."""
        with pytest.raises(AudioProcessingError, match="PCM data is empty"):
            pcm_to_wav(b'')

    def test_validate_audio_format_valid_wav(self):
        """Test audio format validation with valid 16kHz mono WAV."""
        # Create valid WAV data
        pcm_data = b'\x00\x00' * 1000  # Some sample data
        wav_data = pcm_to_wav(pcm_data, sample_rate=16000, channels=1)
        
        is_valid, description = validate_audio_format(wav_data)
        
        assert is_valid is True
        assert "Valid 16kHz mono WAV format" in description

    def test_validate_audio_format_invalid_channels(self):
        """Test audio format validation with stereo audio."""
        # Create stereo WAV data
        pcm_data = b'\x00\x00' * 1000
        wav_data = pcm_to_wav(pcm_data, sample_rate=16000, channels=2)
        
        is_valid, description = validate_audio_format(wav_data)
        
        assert is_valid is False
        assert "Expected mono (1 channel), got 2 channels" in description

    def test_validate_audio_format_invalid_sample_rate(self):
        """Test audio format validation with wrong sample rate."""
        # Create 44.1kHz WAV data
        pcm_data = b'\x00\x00' * 1000
        wav_data = pcm_to_wav(pcm_data, sample_rate=44100, channels=1)
        
        is_valid, description = validate_audio_format(wav_data)
        
        assert is_valid is False
        assert "Expected 16kHz sample rate, got 44100Hz" in description

    def test_validate_audio_format_too_short(self):
        """Test audio format validation with data too short for header."""
        short_data = b'RIFF'  # Too short for full WAV header
        
        is_valid, description = validate_audio_format(short_data)
        
        assert is_valid is False
        assert "Audio data too short" in description

    def test_get_audio_duration(self):
        """Test audio duration calculation."""
        # Create 2 seconds of audio at 16kHz, 16-bit mono
        sample_rate = 16000
        duration = 2.0
        samples = int(sample_rate * duration)
        pcm_data = b'\x00\x00' * samples
        wav_data = pcm_to_wav(pcm_data, sample_rate=sample_rate)
        
        calculated_duration = get_audio_duration(wav_data)
        
        # Should be close to 2.0 seconds (allow small floating point error)
        assert abs(calculated_duration - duration) < 0.01

    @pytest.mark.asyncio
    async def test_download_audio_file_success(self):
        """Test successful audio file download."""
        mock_response = MagicMock()
        mock_response.content = b'fake_audio_data'
        mock_response.raise_for_status = MagicMock()
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)
            
            result = await download_audio_file("https://example.com/audio.wav")
            
            assert result == b'fake_audio_data'

    @pytest.mark.asyncio
    async def test_download_audio_file_empty_response(self):
        """Test audio file download with empty response."""
        mock_response = MagicMock()
        mock_response.content = b''
        mock_response.raise_for_status = MagicMock()
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)
            
            with pytest.raises(AudioDownloadError, match="Downloaded audio file is empty"):
                await download_audio_file("https://example.com/audio.wav")

    @pytest.mark.asyncio
    async def test_download_audio_file_http_error(self):
        """Test audio file download with HTTP error."""
        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                side_effect=Exception("HTTP 404")
            )
            
            with pytest.raises(AudioDownloadError, match="Failed to download audio"):
                await download_audio_file("https://example.com/audio.wav")

    @pytest.mark.asyncio
    async def test_convert_to_16khz_mono_success(self):
        """Test successful audio conversion using ffmpeg."""
        input_data = b'fake_input_audio'
        expected_output = b'fake_converted_audio'
        
        with patch('ffmpeg.input') as mock_input, \
             patch('ffmpeg.output') as mock_output, \
             patch('ffmpeg.run') as mock_run, \
             patch('tempfile.NamedTemporaryFile') as mock_temp:
            
            # Mock temporary files
            mock_input_file = MagicMock()
            mock_output_file = MagicMock()
            mock_output_file.read.return_value = expected_output
            
            mock_temp.return_value.__enter__.side_effect = [mock_input_file, mock_output_file]
            
            result = await convert_to_16khz_mono(input_data)
            
            assert result == expected_output
            mock_input_file.write.assert_called_once_with(input_data)
            mock_run.assert_called_once()

    @pytest.mark.asyncio
    async def test_convert_to_16khz_mono_empty_input(self):
        """Test audio conversion with empty input."""
        with pytest.raises(AudioProcessingError, match="Audio data is empty"):
            await convert_to_16khz_mono(b'')

    @pytest.mark.asyncio
    async def test_process_audio_for_enrollment_success(self):
        """Test complete audio processing pipeline."""
        audio_url = "https://example.com/audio.wav"
        downloaded_data = b'fake_downloaded_audio'
        processed_data = pcm_to_wav(b'\x00\x00' * 1000, sample_rate=16000)  # Valid 16kHz mono WAV
        
        with patch('src.utils.audio_utils.download_audio_file', new_callable=AsyncMock) as mock_download, \
             patch('src.utils.audio_utils.convert_to_16khz_mono', new_callable=AsyncMock) as mock_convert:
            
            mock_download.return_value = downloaded_data
            mock_convert.return_value = processed_data
            
            result = await process_audio_for_enrollment(audio_url)
            
            assert result == processed_data
            mock_download.assert_called_once_with(audio_url)
            mock_convert.assert_called_once_with(downloaded_data)

    @pytest.mark.asyncio
    async def test_process_audio_for_enrollment_invalid_output(self):
        """Test audio processing pipeline with invalid output format."""
        audio_url = "https://example.com/audio.wav"
        downloaded_data = b'fake_downloaded_audio'
        # Create invalid WAV (wrong sample rate)
        invalid_wav = pcm_to_wav(b'\x00\x00' * 1000, sample_rate=44100)
        
        with patch('src.utils.audio_utils.download_audio_file', new_callable=AsyncMock) as mock_download, \
             patch('src.utils.audio_utils.convert_to_16khz_mono', new_callable=AsyncMock) as mock_convert:
            
            mock_download.return_value = downloaded_data
            mock_convert.return_value = invalid_wav
            
            with pytest.raises(AudioProcessingError, match="Processed audio validation failed"):
                await process_audio_for_enrollment(audio_url)