"""
Tests for the embedding service.
"""

import os
import tempfile
import numpy as np
import pytest
import torch
import torchaudio
from unittest.mock import Mock, patch, MagicMock

from src.services.embedding_service import EmbeddingService, get_embedding_service


class TestEmbeddingService:
    """Test cases for EmbeddingService."""
    
    @pytest.fixture
    def embedding_service(self):
        """Create an embedding service instance for testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            service = EmbeddingService(model_cache_dir=temp_dir)
            yield service
    
    @pytest.fixture
    def mock_model(self):
        """Create a mock SpeechBrain model."""
        mock_model = Mock()
        # Mock embedding output (192-dimensional)
        mock_embedding = torch.randn(1, 192)
        mock_model.encode_batch.return_value = mock_embedding
        return mock_model
    
    @pytest.fixture
    def sample_audio_file(self):
        """Create a temporary audio file for testing."""
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
            # Create a simple sine wave audio (1 second, 16kHz, mono)
            sample_rate = 16000
            duration = 1.0
            frequency = 440.0  # A4 note
            
            t = torch.linspace(0, duration, int(sample_rate * duration))
            waveform = torch.sin(2 * torch.pi * frequency * t).unsqueeze(0)
            
            torchaudio.save(temp_file.name, waveform, sample_rate)
            
            yield temp_file.name
            
            # Cleanup
            if os.path.exists(temp_file.name):
                os.unlink(temp_file.name)
    
    def test_init(self):
        """Test EmbeddingService initialization."""
        with tempfile.TemporaryDirectory() as temp_dir:
            service = EmbeddingService(model_cache_dir=temp_dir)
            
            assert service.model_cache_dir == temp_dir
            assert service.model is None
            assert not service._model_loaded
            assert os.path.exists(temp_dir)
    
    def test_init_default_cache_dir(self):
        """Test EmbeddingService initialization with default cache directory."""
        service = EmbeddingService()
        
        expected_dir = os.path.join(tempfile.gettempdir(), "speechbrain_models")
        assert service.model_cache_dir == expected_dir
        assert os.path.exists(expected_dir)
    
    @patch('src.services.embedding_service.EncoderClassifier')
    def test_load_model_success(self, mock_encoder_class, embedding_service, mock_model):
        """Test successful model loading."""
        mock_encoder_class.from_hparams.return_value = mock_model
        
        embedding_service._load_model()
        
        assert embedding_service._model_loaded
        assert embedding_service.model == mock_model
        
        mock_encoder_class.from_hparams.assert_called_once_with(
            source="speechbrain/spkrec-ecapa-voxceleb",
            savedir=embedding_service.model_cache_dir,
            run_opts={"device": "cpu"}
        )
    
    @patch('src.services.embedding_service.EncoderClassifier')
    def test_load_model_failure(self, mock_encoder_class, embedding_service):
        """Test model loading failure."""
        mock_encoder_class.from_hparams.side_effect = Exception("Model loading failed")
        
        with pytest.raises(RuntimeError, match="Model loading failed"):
            embedding_service._load_model()
        
        assert not embedding_service._model_loaded
        assert embedding_service.model is None
    
    @patch('src.services.embedding_service.EncoderClassifier')
    @patch('src.services.embedding_service.torchaudio.load')
    def test_generate_embedding_success(self, mock_load, mock_encoder_class, 
                                      embedding_service, mock_model, sample_audio_file):
        """Test successful embedding generation."""
        # Setup mocks
        mock_encoder_class.from_hparams.return_value = mock_model
        mock_waveform = torch.randn(1, 16000)  # 1 second of audio
        mock_load.return_value = (mock_waveform, 16000)
        
        # Generate embedding
        embedding = embedding_service.generate_embedding(sample_audio_file)
        
        # Verify results
        assert isinstance(embedding, np.ndarray)
        assert embedding.shape == (192,)
        assert embedding_service._model_loaded
        
        mock_load.assert_called_once_with(sample_audio_file)
        mock_model.encode_batch.assert_called_once()
    
    def test_generate_embedding_file_not_found(self, embedding_service):
        """Test embedding generation with non-existent file."""
        with pytest.raises(FileNotFoundError, match="Audio file not found"):
            embedding_service.generate_embedding("nonexistent.wav")
    
    @patch('src.services.embedding_service.EncoderClassifier')
    @patch('src.services.embedding_service.torchaudio.load')
    def test_generate_embedding_audio_too_short(self, mock_load, mock_encoder_class,
                                              embedding_service, mock_model, sample_audio_file):
        """Test embedding generation with audio that's too short."""
        mock_encoder_class.from_hparams.return_value = mock_model
        # Very short audio (0.1 seconds)
        mock_waveform = torch.randn(1, 1600)
        mock_load.return_value = (mock_waveform, 16000)
        
        with pytest.raises(ValueError, match="Audio file too short"):
            embedding_service.generate_embedding(sample_audio_file)
    
    @patch('src.services.embedding_service.EncoderClassifier')
    @patch('src.services.embedding_service.torchaudio.load')
    def test_generate_embedding_stereo_to_mono(self, mock_load, mock_encoder_class,
                                             embedding_service, mock_model, sample_audio_file):
        """Test embedding generation with stereo audio conversion to mono."""
        mock_encoder_class.from_hparams.return_value = mock_model
        # Stereo audio (2 channels)
        mock_waveform = torch.randn(2, 16000)
        mock_load.return_value = (mock_waveform, 16000)
        
        embedding = embedding_service.generate_embedding(sample_audio_file)
        
        assert isinstance(embedding, np.ndarray)
        assert embedding.shape == (192,)
    
    @patch('src.services.embedding_service.EncoderClassifier')
    @patch('src.services.embedding_service.torchaudio.load')
    def test_generate_embedding_resample(self, mock_load, mock_encoder_class,
                                       embedding_service, mock_model, sample_audio_file):
        """Test embedding generation with audio resampling."""
        mock_encoder_class.from_hparams.return_value = mock_model
        # Audio at different sample rate
        mock_waveform = torch.randn(1, 44100)  # 1 second at 44.1kHz
        mock_load.return_value = (mock_waveform, 44100)
        
        embedding = embedding_service.generate_embedding(sample_audio_file)
        
        assert isinstance(embedding, np.ndarray)
        assert embedding.shape == (192,)
    
    def test_compute_cosine_similarity_success(self, embedding_service):
        """Test successful cosine similarity computation."""
        # Create two similar embeddings
        embedding1 = np.random.randn(192)
        embedding2 = embedding1 + 0.1 * np.random.randn(192)  # Add small noise
        
        similarity = embedding_service.compute_cosine_similarity(embedding1, embedding2)
        
        assert isinstance(similarity, float)
        assert -1.0 <= similarity <= 1.0
        assert similarity > 0.8  # Should be high similarity
    
    def test_compute_cosine_similarity_identical(self, embedding_service):
        """Test cosine similarity with identical embeddings."""
        embedding = np.random.randn(192)
        
        similarity = embedding_service.compute_cosine_similarity(embedding, embedding)
        
        assert abs(similarity - 1.0) < 1e-6  # Should be very close to 1.0
    
    def test_compute_cosine_similarity_orthogonal(self, embedding_service):
        """Test cosine similarity with orthogonal embeddings."""
        embedding1 = np.zeros(192)
        embedding1[0] = 1.0
        embedding2 = np.zeros(192)
        embedding2[1] = 1.0
        
        similarity = embedding_service.compute_cosine_similarity(embedding1, embedding2)
        
        assert abs(similarity) < 1e-6  # Should be very close to 0.0
    
    def test_compute_cosine_similarity_dimension_mismatch(self, embedding_service):
        """Test cosine similarity with mismatched dimensions."""
        embedding1 = np.random.randn(192)
        embedding2 = np.random.randn(128)
        
        with pytest.raises(ValueError, match="Embedding dimensions don't match"):
            embedding_service.compute_cosine_similarity(embedding1, embedding2)
    
    def test_compute_cosine_similarity_wrong_dimension(self, embedding_service):
        """Test cosine similarity with wrong embedding dimension."""
        embedding1 = np.random.randn(128)
        embedding2 = np.random.randn(128)
        
        with pytest.raises(ValueError, match="Invalid embedding dimension"):
            embedding_service.compute_cosine_similarity(embedding1, embedding2)
    
    def test_compute_cosine_similarity_zero_norm(self, embedding_service):
        """Test cosine similarity with zero-norm embedding."""
        embedding1 = np.zeros(192)
        embedding2 = np.random.randn(192)
        
        with pytest.raises(ValueError, match="Cannot compute similarity with zero-norm embedding"):
            embedding_service.compute_cosine_similarity(embedding1, embedding2)
    
    def test_verify_speaker_same_speaker(self, embedding_service):
        """Test speaker verification with same speaker."""
        embedding = np.random.randn(192)
        # Add small noise to simulate same speaker
        embedding_noisy = embedding + 0.05 * np.random.randn(192)
        
        is_same, score = embedding_service.verify_speaker(embedding, embedding_noisy, threshold=0.8)
        
        assert isinstance(is_same, bool)
        assert isinstance(score, float)
        assert is_same  # Should be identified as same speaker
        assert score > 0.8
    
    def test_verify_speaker_different_speaker(self, embedding_service):
        """Test speaker verification with different speakers."""
        embedding1 = np.random.randn(192)
        embedding2 = np.random.randn(192)  # Random, likely different
        
        is_same, score = embedding_service.verify_speaker(embedding1, embedding2, threshold=0.8)
        
        assert isinstance(is_same, bool)
        assert isinstance(score, float)
        # Most likely different speakers (random embeddings)
        # We can't guarantee this, but it's very likely
    
    def test_verify_speaker_custom_threshold(self, embedding_service):
        """Test speaker verification with custom threshold."""
        embedding1 = np.random.randn(192)
        embedding2 = np.random.randn(192)
        
        # Test with very low threshold
        is_same_low, score = embedding_service.verify_speaker(embedding1, embedding2, threshold=0.1)
        
        # Test with very high threshold
        is_same_high, _ = embedding_service.verify_speaker(embedding1, embedding2, threshold=0.99)
        
        # Low threshold should be more permissive
        assert isinstance(is_same_low, bool)
        assert isinstance(is_same_high, bool)
    
    def test_verify_speaker_invalid_threshold(self, embedding_service):
        """Test speaker verification with invalid threshold."""
        embedding1 = np.random.randn(192)
        embedding2 = np.random.randn(192)
        
        with pytest.raises(ValueError, match="Threshold must be between 0.0 and 1.0"):
            embedding_service.verify_speaker(embedding1, embedding2, threshold=1.5)
        
        with pytest.raises(ValueError, match="Threshold must be between 0.0 and 1.0"):
            embedding_service.verify_speaker(embedding1, embedding2, threshold=-0.1)
    
    def test_validate_embedding_valid(self, embedding_service):
        """Test embedding validation with valid embedding."""
        embedding = np.random.randn(192)
        
        assert embedding_service.validate_embedding(embedding)
    
    def test_validate_embedding_wrong_type(self, embedding_service):
        """Test embedding validation with wrong type."""
        embedding = [1, 2, 3]  # List instead of numpy array
        
        assert not embedding_service.validate_embedding(embedding)
    
    def test_validate_embedding_wrong_dimension(self, embedding_service):
        """Test embedding validation with wrong dimensions."""
        embedding = np.random.randn(128)  # Wrong size
        
        assert not embedding_service.validate_embedding(embedding)
    
    def test_validate_embedding_2d_array(self, embedding_service):
        """Test embedding validation with 2D array."""
        embedding = np.random.randn(1, 192)  # 2D instead of 1D
        
        assert not embedding_service.validate_embedding(embedding)
    
    def test_validate_embedding_nan_values(self, embedding_service):
        """Test embedding validation with NaN values."""
        embedding = np.random.randn(192)
        embedding[0] = np.nan
        
        assert not embedding_service.validate_embedding(embedding)
    
    def test_validate_embedding_infinite_values(self, embedding_service):
        """Test embedding validation with infinite values."""
        embedding = np.random.randn(192)
        embedding[0] = np.inf
        
        assert not embedding_service.validate_embedding(embedding)
    
    def test_validate_embedding_all_zeros(self, embedding_service):
        """Test embedding validation with all zeros."""
        embedding = np.zeros(192)
        
        assert not embedding_service.validate_embedding(embedding)
    
    def test_get_model_info_not_loaded(self, embedding_service):
        """Test getting model info when model is not loaded."""
        info = embedding_service.get_model_info()
        
        assert isinstance(info, dict)
        assert info["model_loaded"] is False
        assert info["embedding_dimension"] == 192
        assert info["device"] == "cpu"
        assert info["model_name"] == "speechbrain/spkrec-ecapa-voxceleb"
        assert "model_cache_dir" in info
    
    @patch('src.services.embedding_service.EncoderClassifier')
    def test_get_model_info_loaded(self, mock_encoder_class, embedding_service, mock_model):
        """Test getting model info when model is loaded."""
        mock_encoder_class.from_hparams.return_value = mock_model
        embedding_service._load_model()
        
        info = embedding_service.get_model_info()
        
        assert info["model_loaded"] is True
        assert info["embedding_dimension"] == 192
        assert info["device"] == "cpu"


class TestGlobalEmbeddingService:
    """Test cases for global embedding service functions."""
    
    def test_get_embedding_service_singleton(self):
        """Test that get_embedding_service returns the same instance."""
        service1 = get_embedding_service()
        service2 = get_embedding_service()
        
        assert service1 is service2
        assert isinstance(service1, EmbeddingService)
    
    @patch('src.services.embedding_service._embedding_service', None)
    def test_get_embedding_service_creates_new(self):
        """Test that get_embedding_service creates new instance when needed."""
        service = get_embedding_service()
        
        assert isinstance(service, EmbeddingService)