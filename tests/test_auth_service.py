"""
Tests for the authentication service.
"""

import pytest
import tempfile
import numpy as np
from datetime import datetime
from uuid import UUID, uuid4
from unittest.mock import Mock, patch, AsyncMock, MagicMock

from src.services.auth_service import (
    AuthenticationService,
    EnrollmentError,
    VerificationError,
    get_auth_service
)
from src.models.internal_models import User, AuthAttempt
from src.utils.audio_utils import AudioDownloadError, AudioProcessingError


class TestAuthenticationService:
    """Test cases for AuthenticationService."""
    
    @pytest.fixture
    def mock_db_manager(self):
        """Create a mock database manager."""
        db_manager = Mock()
        db_manager.users = Mock()
        db_manager.auth_attempts = Mock()
        return db_manager
    
    @pytest.fixture
    def mock_embedding_service(self):
        """Create a mock embedding service."""
        embedding_service = Mock()
        # Mock a valid 192-dimensional embedding
        mock_embedding = np.random.randn(192)
        embedding_service.generate_embedding.return_value = mock_embedding
        embedding_service.validate_embedding.return_value = True
        embedding_service.verify_speaker.return_value = (True, 0.95)
        return embedding_service
    
    @pytest.fixture
    def auth_service(self, mock_db_manager, mock_embedding_service):
        """Create an authentication service instance for testing."""
        service = AuthenticationService(db_manager=mock_db_manager)
        # Replace the embedding service with our mock
        service.embedding_service = mock_embedding_service
        return service
    
    @pytest.fixture
    def sample_user_id(self):
        """Generate a sample user ID."""
        return uuid4()
    
    @pytest.fixture
    def sample_phone(self):
        """Sample phone number."""
        return "+1234567890"
    
    @pytest.fixture
    def sample_audio_url(self):
        """Sample audio URL."""
        return "https://example.com/audio.wav"
    
    @pytest.fixture
    def sample_listen_url(self):
        """Sample WebSocket listen URL."""
        return "wss://example.com/listen"
    
    @pytest.fixture
    def sample_user(self, sample_user_id, sample_phone):
        """Create a sample user with embedding."""
        return User(
            id=sample_user_id,
            phone=sample_phone,
            embedding=np.random.randn(192),
            enrolled_at=datetime.utcnow()
        )

    class TestEnrollment:
        """Tests for user enrollment workflow."""
        
        @patch('src.services.auth_service.process_audio_for_enrollment')
        @patch('src.services.auth_service.get_audio_duration')
        @pytest.mark.asyncio
        async def test_enroll_user_success(
            self, 
            mock_get_duration,
            mock_process_audio,
            auth_service, 
            sample_user_id, 
            sample_phone, 
            sample_audio_url
        ):
            """Test successful user enrollment."""
            # Setup mocks
            mock_audio_data = b'fake_wav_data' * 1000
            mock_process_audio.return_value = mock_audio_data
            mock_get_duration.return_value = 5.0  # 5 seconds of audio
            auth_service.db.users.create_or_update_user = AsyncMock()
            
            # Execute enrollment
            status, score = await auth_service.enroll_user(sample_user_id, sample_phone, sample_audio_url)
            
            # Verify results
            assert status == "enrolled"
            assert score == 1.0
            
            # Verify mocks were called correctly
            mock_process_audio.assert_called_once_with(sample_audio_url)
            auth_service.embedding_service.generate_embedding.assert_called_once()
            auth_service.embedding_service.validate_embedding.assert_called_once()
            auth_service.db.users.create_or_update_user.assert_called_once()
        
        @patch('src.services.auth_service.process_audio_for_enrollment')
        @pytest.mark.asyncio
        async def test_enroll_user_audio_download_error(
            self, 
            mock_process_audio, 
            auth_service, 
            sample_user_id, 
            sample_phone, 
            sample_audio_url
        ):
            """Test enrollment failure due to audio download error."""
            mock_process_audio.side_effect = AudioDownloadError("Download failed")
            
            with pytest.raises(EnrollmentError, match="Failed to download audio"):
                await auth_service.enroll_user(sample_user_id, sample_phone, sample_audio_url)
        
        @patch('src.services.auth_service.process_audio_for_enrollment')
        @pytest.mark.asyncio
        async def test_enroll_user_audio_processing_error(
            self, 
            mock_process_audio, 
            auth_service, 
            sample_user_id, 
            sample_phone, 
            sample_audio_url
        ):
            """Test enrollment failure due to audio processing error."""
            mock_process_audio.side_effect = AudioProcessingError("Processing failed")
            
            with pytest.raises(EnrollmentError, match="Failed to process audio"):
                await auth_service.enroll_user(sample_user_id, sample_phone, sample_audio_url)
        
        @patch('src.services.auth_service.process_audio_for_enrollment')
        @patch('src.services.auth_service.get_audio_duration')
        @pytest.mark.asyncio
        async def test_enroll_user_audio_too_short(
            self, 
            mock_get_duration,
            mock_process_audio, 
            auth_service, 
            sample_user_id, 
            sample_phone, 
            sample_audio_url
        ):
            """Test enrollment failure due to audio being too short."""
            mock_process_audio.return_value = b'short_audio'
            mock_get_duration.return_value = 1.5  # Too short
            
            with pytest.raises(EnrollmentError, match="Audio too short for enrollment"):
                await auth_service.enroll_user(sample_user_id, sample_phone, sample_audio_url)
        
        @patch('src.services.auth_service.process_audio_for_enrollment')
        @patch('src.services.auth_service.get_audio_duration')
        @pytest.mark.asyncio
        async def test_enroll_user_embedding_generation_error(
            self,
            mock_get_duration,
            mock_process_audio,
            auth_service,
            sample_user_id,
            sample_phone,
            sample_audio_url
        ):
            """Test enrollment failure due to embedding generation error."""
            mock_process_audio.return_value = b'fake_audio'
            mock_get_duration.return_value = 5.0
            
            auth_service.embedding_service.generate_embedding.side_effect = Exception("Embedding failed")
            
            with pytest.raises(EnrollmentError, match="Failed to generate voice embedding"):
                await auth_service.enroll_user(sample_user_id, sample_phone, sample_audio_url)
        
        @patch('src.services.auth_service.process_audio_for_enrollment')
        @patch('src.services.auth_service.get_audio_duration')
        @pytest.mark.asyncio
        async def test_enroll_user_database_error(
            self,
            mock_get_duration,
            mock_process_audio,
            auth_service,
            sample_user_id,
            sample_phone,
            sample_audio_url
        ):
            """Test enrollment failure due to database error."""
            mock_process_audio.return_value = b'fake_audio'
            mock_get_duration.return_value = 5.0
            
            auth_service.db.users.create_or_update_user = AsyncMock(side_effect=Exception("DB error"))
            
            with pytest.raises(EnrollmentError, match="Failed to store user enrollment"):
                await auth_service.enroll_user(sample_user_id, sample_phone, sample_audio_url)

    class TestVerification:
        """Tests for user verification workflow."""
        
        @patch('src.services.auth_service.capture_audio_from_vapi')
        @patch('src.services.auth_service.get_audio_duration')
        @pytest.mark.asyncio
        async def test_verify_user_success(
            self,
            mock_get_duration,
            mock_capture_audio,
            auth_service,
            sample_user,
            sample_listen_url
        ):
            """Test successful user verification."""
            # Setup mocks
            mock_capture_audio.return_value = b'captured_audio'
            mock_get_duration.return_value = 3.5
            
            auth_service.db.users.get_user_by_id = AsyncMock(return_value=sample_user)
            auth_service._log_auth_attempt = AsyncMock()
            
            # Execute verification
            success, message, score = await auth_service.verify_user(sample_user.id, sample_listen_url)
            
            # Verify results
            assert success is True
            assert "successful" in message.lower()
            assert score == 0.95
            
            # Verify mocks were called
            auth_service.db.users.get_user_by_id.assert_called_once_with(sample_user.id)
            mock_capture_audio.assert_called_once()
            auth_service.embedding_service.generate_embedding.assert_called_once()
            auth_service.embedding_service.verify_speaker.assert_called_once()
            auth_service._log_auth_attempt.assert_called_once_with(sample_user.id, True, 0.95)
        
        @pytest.mark.asyncio
        async def test_verify_user_not_enrolled(
            self, 
            auth_service, 
            sample_user_id, 
            sample_listen_url
        ):
            """Test verification failure when user is not enrolled."""
            auth_service.db.users.get_user_by_id = AsyncMock(return_value=None)
            auth_service._log_auth_attempt = AsyncMock()
            
            success, message, score = await auth_service.verify_user(sample_user_id, sample_listen_url)
            
            assert success is False
            assert "not enrolled" in message.lower()
            assert score is None
            auth_service._log_auth_attempt.assert_called_once_with(sample_user_id, False, 0.0)
        
        @patch('src.services.auth_service.capture_audio_from_vapi')
        @pytest.mark.asyncio
        async def test_verify_user_vapi_connection_error(
            self,
            mock_capture_audio,
            auth_service,
            sample_user,
            sample_listen_url
        ):
            """Test verification failure due to VAPI connection error."""
            from src.clients.vapi_client import VAPIConnectionError
            
            auth_service.db.users.get_user_by_id = AsyncMock(return_value=sample_user)
            auth_service._log_auth_attempt = AsyncMock()
            mock_capture_audio.side_effect = VAPIConnectionError("Connection failed")
            
            with pytest.raises(VerificationError, match="Failed to connect to audio stream"):
                await auth_service.verify_user(sample_user.id, sample_listen_url)
        
        @patch('src.services.auth_service.capture_audio_from_vapi')
        @patch('src.services.auth_service.get_audio_duration')
        @pytest.mark.asyncio
        async def test_verify_user_audio_too_short(
            self,
            mock_get_duration,
            mock_capture_audio,
            auth_service,
            sample_user,
            sample_listen_url
        ):
            """Test verification failure due to captured audio being too short."""
            auth_service.db.users.get_user_by_id = AsyncMock(return_value=sample_user)
            auth_service._log_auth_attempt = AsyncMock()
            mock_capture_audio.return_value = b'short_audio'
            mock_get_duration.return_value = 0.5  # Too short
            
            success, message, score = await auth_service.verify_user(sample_user.id, sample_listen_url)
            
            assert success is False
            assert "too short" in message.lower()
            assert score is None
        
        @patch('src.services.auth_service.capture_audio_from_vapi')
        @patch('src.services.auth_service.get_audio_duration')
        @pytest.mark.asyncio
        async def test_verify_user_similarity_below_threshold(
            self,
            mock_get_duration,
            mock_capture_audio,
            auth_service,
            sample_user,
            sample_listen_url
        ):
            """Test verification failure due to similarity below threshold."""
            mock_capture_audio.return_value = b'captured_audio'
            mock_get_duration.return_value = 3.5
            
            # Override the mock to return below threshold
            auth_service.embedding_service.verify_speaker.return_value = (False, 0.75)  # Below threshold
            
            auth_service.db.users.get_user_by_id = AsyncMock(return_value=sample_user)
            auth_service._log_auth_attempt = AsyncMock()
            
            success, message, score = await auth_service.verify_user(sample_user.id, sample_listen_url)
            
            assert success is False
            assert "failed" in message.lower()
            assert score == 0.75
            auth_service._log_auth_attempt.assert_called_once_with(sample_user.id, False, 0.75)

    class TestUtilityMethods:
        """Tests for utility methods."""
        
        @pytest.mark.asyncio
        async def test_log_auth_attempt_success(self, auth_service, sample_user_id):
            """Test successful auth attempt logging."""
            auth_service.db.auth_attempts.create_auth_attempt = AsyncMock()
            
            await auth_service._log_auth_attempt(sample_user_id, True, 0.95)
            
            auth_service.db.auth_attempts.create_auth_attempt.assert_called_once()
            call_args = auth_service.db.auth_attempts.create_auth_attempt.call_args[0][0]
            assert call_args.user_id == sample_user_id
            assert call_args.success is True
            assert call_args.score == 0.95
        
        @pytest.mark.asyncio
        async def test_log_auth_attempt_failure(self, auth_service, sample_user_id):
            """Test auth attempt logging handles database errors gracefully."""
            auth_service.db.auth_attempts.create_auth_attempt = AsyncMock(side_effect=Exception("DB error"))
            
            # Should not raise exception
            await auth_service._log_auth_attempt(sample_user_id, False, 0.5)
        
        @pytest.mark.asyncio
        async def test_get_user_auth_history(self, auth_service, sample_user_id):
            """Test getting user authentication history."""
            mock_attempts = [
                AuthAttempt(user_id=sample_user_id, success=True, score=0.95, created_at=datetime.utcnow()),
                AuthAttempt(user_id=sample_user_id, success=False, score=0.75, created_at=datetime.utcnow())
            ]
            auth_service.db.auth_attempts.get_auth_attempts_by_user = AsyncMock(return_value=mock_attempts)
            
            result = await auth_service.get_user_auth_history(sample_user_id, limit=10)
            
            assert len(result) == 2
            assert result[0].success is True
            assert result[1].success is False
            auth_service.db.auth_attempts.get_auth_attempts_by_user.assert_called_once_with(sample_user_id, 10)
        
        @pytest.mark.asyncio
        async def test_check_recent_failures(self, auth_service, sample_user_id):
            """Test checking recent failed attempts."""
            auth_service.db.auth_attempts.get_recent_failed_attempts = AsyncMock(return_value=3)
            
            count = await auth_service.check_recent_failures(sample_user_id, minutes=60)
            
            assert count == 3
            auth_service.db.auth_attempts.get_recent_failed_attempts.assert_called_once_with(sample_user_id, 60)
        
        @pytest.mark.asyncio
        async def test_check_recent_failures_error_handling(self, auth_service, sample_user_id):
            """Test that check_recent_failures handles errors gracefully."""
            auth_service.db.auth_attempts.get_recent_failed_attempts = AsyncMock(side_effect=Exception("DB error"))
            
            count = await auth_service.check_recent_failures(sample_user_id)
            
            assert count == 0  # Should return 0 on error


class TestGlobalAuthService:
    """Test cases for global auth service functions."""
    
    def test_get_auth_service_singleton(self):
        """Test that get_auth_service returns the same instance."""
        service1 = get_auth_service()
        service2 = get_auth_service()
        
        assert service1 is service2
        assert isinstance(service1, AuthenticationService)
    
    @patch('src.services.auth_service._auth_service', None)
    def test_get_auth_service_creates_new(self):
        """Test that get_auth_service creates new instance when needed."""
        service = get_auth_service()
        
        assert isinstance(service, AuthenticationService)


class TestIntegration:
    """Integration tests for complete workflows."""
    
    @patch('src.services.auth_service.process_audio_for_enrollment')
    @patch('src.services.auth_service.capture_audio_from_vapi')
    @patch('src.services.auth_service.get_audio_duration')
    @pytest.mark.asyncio
    async def test_complete_enrollment_verification_workflow(
        self,
        mock_get_duration,
        mock_capture_audio,
        mock_process_audio
    ):
        """Test complete workflow: enrollment followed by verification."""
        # Setup
        mock_db_manager = Mock()
        mock_db_manager.users = Mock()
        mock_db_manager.auth_attempts = Mock()
        auth_service = AuthenticationService(db_manager=mock_db_manager)
        user_id = uuid4()
        phone = "+1234567890"
        audio_url = "https://example.com/audio.wav"
        listen_url = "wss://example.com/listen"
        
        # Mock embedding service
        mock_embedding_service = Mock()
        stored_embedding = np.random.randn(192)
        live_embedding = stored_embedding + 0.01 * np.random.randn(192)  # Very similar
        
        mock_embedding_service.generate_embedding.side_effect = [stored_embedding, live_embedding]
        mock_embedding_service.validate_embedding.return_value = True
        mock_embedding_service.verify_speaker.return_value = (True, 0.95)
        auth_service.embedding_service = mock_embedding_service
        
        # Mock other services
        mock_process_audio.return_value = b'processed_audio'
        mock_capture_audio.return_value = b'captured_audio'
        mock_get_duration.return_value = 5.0
        
        # Mock database
        stored_user = None
        auth_service.db.users.create_or_update_user = AsyncMock(
            side_effect=lambda user: setattr(auth_service, '_stored_user', user)
        )
        auth_service.db.users.get_user_by_id = AsyncMock(
            side_effect=lambda user_id: getattr(auth_service, '_stored_user', None)
        )
        auth_service.db.auth_attempts.create_auth_attempt = AsyncMock()
        
        # Step 1: Enrollment
        status, score = await auth_service.enroll_user(user_id, phone, audio_url)
        assert status == "enrolled"
        assert score == 1.0
        
        # Step 2: Verification
        success, message, similarity_score = await auth_service.verify_user(user_id, listen_url)
        assert success is True
        assert similarity_score == 0.95
        
        # Verify all components were called
        assert mock_embedding_service.generate_embedding.call_count == 2
        assert mock_embedding_service.verify_speaker.call_count == 1
        auth_service.db.users.create_or_update_user.assert_called_once()
        auth_service.db.users.get_user_by_id.assert_called_once()