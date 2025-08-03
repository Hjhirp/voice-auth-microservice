"""
Authentication service for voice enrollment and verification workflows.

This module provides the core business logic for:
- User voice enrollment with audio processing and embedding generation
- Voice verification with live audio capture and similarity scoring
- Integration with database storage and external services
"""

import logging
import tempfile
from datetime import datetime
from typing import Optional, Tuple

from src.clients.supabase_client import DatabaseManager
from src.clients.vapi_client import capture_audio_from_vapi, VAPIConnectionError, VAPIAudioError
from src.models.internal_models import User, AuthAttempt
from src.services.embedding_service import get_embedding_service
from src.utils.audio_utils import (
    process_audio_for_enrollment,
    AudioDownloadError,
    AudioProcessingError,
    get_audio_duration
)
from src.config import settings

logger = logging.getLogger(__name__)


class AuthenticationError(Exception):
    """Base exception for authentication service errors."""
    pass


class EnrollmentError(AuthenticationError):
    """Raised when user enrollment fails."""
    pass


class VerificationError(AuthenticationError):
    """Raised when user verification fails."""
    pass


class AuthenticationService:
    """
    Core authentication service handling enrollment and verification workflows.
    
    Orchestrates audio processing, embedding generation, database operations,
    and external service integrations for voice authentication.
    """
    
    def __init__(self, db_manager: Optional[DatabaseManager] = None):
        """
        Initialize authentication service.
        
        Args:
            db_manager: Database manager instance. If None, creates a new one.
        """
        self.db = db_manager or DatabaseManager()
        self.embedding_service = get_embedding_service()
        self.voice_threshold = getattr(settings, 'voice_threshold', 0.82)
        
        logger.info(f"Authentication service initialized with voice threshold: {self.voice_threshold}")
    
    async def enroll_user(self, phone: str, audio_url: str) -> Tuple[str, float]:
        """
        Enroll a user for voice authentication.
        
        Complete enrollment workflow:
        1. Download and process audio from URL
        2. Generate voice embedding using SpeechBrain ECAPA
        3. Store user record in database
        4. Return enrollment status
        
        Args:
            phone: User's phone number (unique identifier)
            audio_url: URL to download enrollment audio
            
        Returns:
            Tuple of (status_message, confidence_score)
            
        Raises:
            EnrollmentError: If any step of enrollment fails
        """
        try:
            logger.info(f"Starting enrollment for user phone: {phone}")
            
            # Step 1: Download and process audio
            try:
                processed_audio = await process_audio_for_enrollment(audio_url)
                logger.info(f"Audio processing completed: {len(processed_audio)} bytes")
                
                # Validate audio duration (should be at least 3 seconds for good enrollment)
                duration = get_audio_duration(processed_audio)
                if duration < 3.0:
                    raise EnrollmentError(f"Audio too short for enrollment: {duration:.1f}s (minimum 3s required)")
                    
                logger.info(f"Audio duration: {duration:.1f}s")
                
            except AudioDownloadError as e:
                logger.error(f"Audio download failed for user {phone}: {e}")
                raise EnrollmentError(f"Failed to download audio: {e}")
            except AudioProcessingError as e:
                logger.error(f"Audio processing failed for user {phone}: {e}")
                raise EnrollmentError(f"Failed to process audio: {e}")
            
            # Step 2: Generate voice embedding
            try:
                # Save processed audio to temporary file for embedding generation
                with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
                    temp_file.write(processed_audio)
                    temp_audio_path = temp_file.name
                
                # Generate embedding
                embedding = self.embedding_service.generate_embedding(temp_audio_path)
                logger.info(f"Generated embedding for user {phone}: shape {embedding.shape}")
                
                # Validate embedding
                if not self.embedding_service.validate_embedding(embedding):
                    raise EnrollmentError("Generated embedding failed validation")
                
            except Exception as e:
                logger.error(f"Embedding generation failed for user {phone}: {e}")
                raise EnrollmentError(f"Failed to generate voice embedding: {e}")
            finally:
                # Cleanup temporary file
                try:
                    import os
                    if 'temp_audio_path' in locals():
                        os.unlink(temp_audio_path)
                except Exception as cleanup_error:
                    logger.warning(f"Failed to cleanup temporary file: {cleanup_error}")
            
            # Step 3: Store user record in database
            try:
                user = User(
                    phone=phone,
                    embedding=embedding,
                    enrolled_at=datetime.utcnow()
                )
                
                await self.db.users.create_or_update_user(user)
                logger.info(f"Successfully enrolled user {phone} in database")
                
            except Exception as e:
                logger.error(f"Database operation failed for user {phone}: {e}")
                raise EnrollmentError(f"Failed to store user enrollment: {e}")
            
            logger.info(f"Enrollment completed successfully for user {phone}")
            return "enrolled", 1.0
            
        except EnrollmentError:
            # Re-raise enrollment errors as-is
            raise
        except Exception as e:
            logger.error(f"Unexpected error during enrollment for user {phone}: {e}")
            raise EnrollmentError(f"Enrollment failed: {e}")
    
    async def verify_user(self, phone: str, listen_url: str) -> Tuple[bool, str, Optional[float]]:
        """
        Verify user identity through voice authentication.
        
        Complete verification workflow:
        1. Fetch stored user embedding from database
        2. Capture live audio from VAPI WebSocket
        3. Generate embedding from captured audio
        4. Compare embeddings and compute similarity score
        5. Log authentication attempt
        6. Return verification result
        
        Args:
            phone: User's phone number (unique identifier)
            listen_url: WebSocket URL for live audio capture
            
        Returns:
            Tuple of (success, message, similarity_score)
            
        Raises:
            VerificationError: If verification process fails
        """
        similarity_score = None
        auth_success = False
        
        try:
            logger.info(f"Starting verification for user {phone}")
            
            # Step 1: Fetch stored user embedding
            try:
                stored_user = await self.db.users.get_user_by_phone(phone)
                if not stored_user:
                    logger.warning(f"User {phone} not found in database")
                    await self._log_auth_attempt(phone, False, 0.0)
                    return False, "User not enrolled for voice authentication", None
                
                logger.info(f"Retrieved stored embedding for user {phone}")
                
            except Exception as e:
                logger.error(f"Database error retrieving user {phone}: {e}")
                raise VerificationError(f"Failed to retrieve user data: {e}")
            
            # Step 2: Capture live audio from VAPI
            try:
                logger.info(f"Capturing live audio from VAPI: {listen_url}")
                captured_audio = await capture_audio_from_vapi(
                    listen_url=listen_url,
                    min_duration=3.0,  # Minimum 3 seconds of audio
                    silence_threshold=0.01,  # RMS threshold for silence
                    silence_duration=2.0,  # 2 seconds of silence to stop
                    max_duration=30.0,  # Maximum 30 seconds
                    connection_timeout=10.0  # 10 second connection timeout
                )
                
                # Validate captured audio duration
                duration = get_audio_duration(captured_audio)
                if duration < 1.0:
                    logger.warning(f"Captured audio too short: {duration:.1f}s")
                    await self._log_auth_attempt(phone, False, 0.0)
                    return False, "Captured audio too short for verification", None
                
                logger.info(f"Captured audio: {len(captured_audio)} bytes, {duration:.1f}s duration")
                
            except VAPIConnectionError as e:
                logger.error(f"VAPI connection failed for user {phone}: {e}")
                await self._log_auth_attempt(phone, False, 0.0)
                raise VerificationError(f"Failed to connect to audio stream: {e}")
            except VAPIAudioError as e:
                logger.error(f"VAPI audio capture failed for user {phone}: {e}")
                await self._log_auth_attempt(phone, False, 0.0)
                raise VerificationError(f"Failed to capture audio: {e}")
            
            # Step 3: Generate embedding from captured audio
            try:
                # Save captured audio to temporary file
                with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
                    temp_file.write(captured_audio)
                    temp_audio_path = temp_file.name
                
                # Generate embedding from captured audio
                live_embedding = self.embedding_service.generate_embedding(temp_audio_path)
                logger.info(f"Generated live embedding for user {phone}: shape {live_embedding.shape}")
                
                # Validate embedding
                if not self.embedding_service.validate_embedding(live_embedding):
                    logger.error(f"Live embedding validation failed for user {phone}")
                    await self._log_auth_attempt(phone, False, 0.0)
                    return False, "Failed to process captured audio", None
                
            except Exception as e:
                logger.error(f"Live embedding generation failed for user {phone}: {e}")
                await self._log_auth_attempt(phone, False, 0.0)
                raise VerificationError(f"Failed to process captured audio: {e}")
            finally:
                # Cleanup temporary file
                try:
                    import os
                    if 'temp_audio_path' in locals():
                        os.unlink(temp_audio_path)
                except Exception as cleanup_error:
                    logger.warning(f"Failed to cleanup temporary file: {cleanup_error}")
            
            # Step 4: Compare embeddings and compute similarity
            try:
                is_match, similarity_score = self.embedding_service.verify_speaker(
                    stored_user.embedding,
                    live_embedding,
                    threshold=self.voice_threshold
                )
                
                logger.info(f"Voice comparison for user {phone}: similarity={similarity_score:.4f}, threshold={self.voice_threshold}, match={is_match}")
                
                if is_match:
                    auth_success = True
                    message = "Voice verification successful"
                    logger.info(f"Voice verification successful for user {phone}")
                else:
                    message = f"Voice verification failed: similarity {similarity_score:.3f} below threshold {self.voice_threshold}"
                    logger.info(f"Voice verification failed for user {phone}: {message}")
                
            except Exception as e:
                logger.error(f"Similarity computation failed for user {phone}: {e}")
                await self._log_auth_attempt(phone, False, 0.0)
                raise VerificationError(f"Failed to compare voice samples: {e}")
            
            # Step 5: Log authentication attempt
            try:
                await self._log_auth_attempt(phone, auth_success, similarity_score)
            except Exception as e:
                logger.warning(f"Failed to log auth attempt for user {phone}: {e}")
                # Don't fail verification just because logging failed
            
            return auth_success, message, similarity_score
            
        except VerificationError:
            # Re-raise verification errors as-is
            raise
        except Exception as e:
            logger.error(f"Unexpected error during verification for user {phone}: {e}")
            # Try to log failed attempt
            try:
                await self._log_auth_attempt(phone, False, similarity_score or 0.0)
            except Exception as log_error:
                logger.warning(f"Failed to log failed auth attempt: {log_error}")
            raise VerificationError(f"Verification failed: {e}")
    
    async def _log_auth_attempt(self, phone: str, success: bool, score: float) -> None:
        """
        Log authentication attempt to database.
        
        Args:
            phone: User's phone number
            success: Whether authentication was successful
            score: Similarity score from voice comparison
        """
        try:
            auth_attempt = AuthAttempt(
                phone=phone,
                success=success,
                score=score,
                created_at=datetime.utcnow()
            )
            
            await self.db.auth_attempts.create_auth_attempt(auth_attempt)
            logger.debug(f"Logged auth attempt for user {phone}: success={success}, score={score:.4f}")
            
        except Exception as e:
            logger.error(f"Failed to log auth attempt for user {phone}: {e}")
            # Don't re-raise since this is just logging
    
    async def get_user_auth_history(self, phone: str, limit: int = 10) -> list:
        """
        Get recent authentication attempts for a user.
        
        Args:
            phone: User's phone number
            limit: Maximum number of attempts to return
            
        Returns:
            List of recent authentication attempts
        """
        try:
            attempts = await self.db.auth_attempts.get_auth_attempts_by_phone(phone, limit)
            logger.info(f"Retrieved {len(attempts)} auth attempts for user {phone}")
            return attempts
        except Exception as e:
            logger.error(f"Failed to get auth history for user {phone}: {e}")
            raise AuthenticationError(f"Failed to retrieve authentication history: {e}")
    
    async def check_recent_failures(self, phone: str, minutes: int = 60) -> int:
        """
        Check for recent failed authentication attempts.
        
        Args:
            phone: User's phone number to check
            minutes: Time window in minutes to check
            
        Returns:
            Number of recent failed attempts
        """
        try:
            failure_count = await self.db.auth_attempts.get_recent_failed_attempts(phone, minutes)
            logger.debug(f"User {phone} has {failure_count} failed attempts in last {minutes} minutes")
            return failure_count
        except Exception as e:
            logger.error(f"Failed to check recent failures for user {phone}: {e}")
            return 0  # Return 0 on error to avoid blocking authentication


# Global service instance
_auth_service: Optional[AuthenticationService] = None


def get_auth_service() -> AuthenticationService:
    """
    Get the global authentication service instance.
    
    Returns:
        AuthenticationService: The global authentication service instance
    """
    global _auth_service
    if _auth_service is None:
        _auth_service = AuthenticationService()
    return _auth_service