"""
Embedding service for generating speaker embeddings using SpeechBrain ECAPA-TDNN model.
"""

import logging
import os
import tempfile
from pathlib import Path
from typing import Optional

import numpy as np
import torch
import torchaudio
from speechbrain.inference import EncoderClassifier

logger = logging.getLogger(__name__)


class EmbeddingService:
    """Service for generating speaker embeddings using SpeechBrain ECAPA-TDNN model."""
    
    def __init__(self, model_cache_dir: Optional[str] = None):
        """
        Initialize the embedding service.
        
        Args:
            model_cache_dir: Directory to cache the model files. If None, uses system temp dir.
        """
        self.model_cache_dir = model_cache_dir or os.path.join(tempfile.gettempdir(), "speechbrain_models")
        self.model: Optional[EncoderClassifier] = None
        self._model_loaded = False
        
        # Ensure CPU-only mode for Render deployment
        torch.set_num_threads(1)
        if torch.cuda.is_available():
            logger.warning("CUDA detected but forcing CPU-only mode for deployment compatibility")
        
        # Create cache directory
        Path(self.model_cache_dir).mkdir(parents=True, exist_ok=True)
        
    def _load_model(self) -> None:
        """Load the SpeechBrain ECAPA-TDNN model with CPU-only configuration."""
        if self._model_loaded:
            return
            
        try:
            logger.info("Loading SpeechBrain ECAPA-TDNN model...")
            
            # Load the pre-trained ECAPA-TDNN model for speaker verification
            # Using CPU-only mode and caching for Render deployment
            self.model = EncoderClassifier.from_hparams(
                source="speechbrain/spkrec-ecapa-voxceleb",
                savedir=self.model_cache_dir,
                run_opts={"device": "cpu"}  # Force CPU-only mode
            )
            
            self._model_loaded = True
            logger.info("SpeechBrain ECAPA-TDNN model loaded successfully")
            
        except Exception as e:
            logger.error(f"Failed to load SpeechBrain model: {e}")
            raise RuntimeError(f"Model loading failed: {e}")
    
    def generate_embedding(self, audio_path: str) -> np.ndarray:
        """
        Generate a 192-dimensional speaker embedding from an audio file.
        
        Args:
            audio_path: Path to the audio file (WAV format, 16kHz mono recommended)
            
        Returns:
            numpy.ndarray: 192-dimensional speaker embedding vector
            
        Raises:
            RuntimeError: If model loading or embedding generation fails
            FileNotFoundError: If audio file doesn't exist
            ValueError: If audio file is invalid or too short
        """
        if not os.path.exists(audio_path):
            raise FileNotFoundError(f"Audio file not found: {audio_path}")
        
        # Ensure model is loaded
        self._load_model()
        
        try:
            logger.debug(f"Generating embedding for audio file: {audio_path}")
            
            # Load and preprocess audio
            waveform, sample_rate = torchaudio.load(audio_path)
            
            # Validate audio
            if waveform.shape[1] < sample_rate * 0.5:  # Less than 0.5 seconds
                raise ValueError("Audio file too short (minimum 0.5 seconds required)")
            
            # Convert to mono if stereo
            if waveform.shape[0] > 1:
                waveform = torch.mean(waveform, dim=0, keepdim=True)
            
            # Resample to 16kHz if needed (ECAPA model expects 16kHz)
            if sample_rate != 16000:
                resampler = torchaudio.transforms.Resample(sample_rate, 16000)
                waveform = resampler(waveform)
            
            # Generate embedding using the model
            with torch.no_grad():
                embeddings = self.model.encode_batch(waveform.unsqueeze(0))
                embedding = embeddings.squeeze().cpu().numpy()
            
            # Verify embedding dimensions (should be 192 for ECAPA-TDNN)
            if embedding.shape[0] != 192:
                raise RuntimeError(f"Unexpected embedding dimension: {embedding.shape[0]}, expected 192")
            
            logger.debug(f"Generated embedding with shape: {embedding.shape}")
            return embedding
            
        except ValueError as e:
            # Re-raise ValueError as-is (for validation errors like audio too short)
            raise e
        except Exception as e:
            logger.error(f"Failed to generate embedding for {audio_path}: {e}")
            raise RuntimeError(f"Embedding generation failed: {e}")
    
    def compute_cosine_similarity(self, embedding1: np.ndarray, embedding2: np.ndarray) -> float:
        """
        Compute cosine similarity between two embeddings.
        
        Args:
            embedding1: First embedding vector
            embedding2: Second embedding vector
            
        Returns:
            float: Cosine similarity score between -1 and 1
            
        Raises:
            ValueError: If embeddings have different dimensions or are invalid
        """
        if embedding1.shape != embedding2.shape:
            raise ValueError(f"Embedding dimensions don't match: {embedding1.shape} vs {embedding2.shape}")
        
        if embedding1.shape[0] != 192:
            raise ValueError(f"Invalid embedding dimension: {embedding1.shape[0]}, expected 192")
        
        try:
            # Normalize embeddings
            norm1 = np.linalg.norm(embedding1)
            norm2 = np.linalg.norm(embedding2)
            
            if norm1 == 0 or norm2 == 0:
                raise ValueError("Cannot compute similarity with zero-norm embedding")
            
            # Compute cosine similarity
            similarity = np.dot(embedding1, embedding2) / (norm1 * norm2)
            
            # Ensure result is in valid range [-1, 1]
            similarity = np.clip(similarity, -1.0, 1.0)
            
            logger.debug(f"Computed cosine similarity: {similarity}")
            return float(similarity)
            
        except ValueError as e:
            # Re-raise ValueError as-is (for validation errors)
            raise e
        except Exception as e:
            logger.error(f"Failed to compute cosine similarity: {e}")
            raise RuntimeError(f"Similarity computation failed: {e}")
    
    def verify_speaker(self, embedding1: np.ndarray, embedding2: np.ndarray, threshold: float = 0.82) -> tuple[bool, float]:
        """
        Verify if two embeddings belong to the same speaker.
        
        Args:
            embedding1: First speaker embedding
            embedding2: Second speaker embedding  
            threshold: Similarity threshold for verification (default: 0.82)
            
        Returns:
            tuple: (is_same_speaker: bool, similarity_score: float)
            
        Raises:
            ValueError: If threshold is not in valid range or embeddings are invalid
        """
        if not 0.0 <= threshold <= 1.0:
            raise ValueError(f"Threshold must be between 0.0 and 1.0, got: {threshold}")
        
        similarity = self.compute_cosine_similarity(embedding1, embedding2)
        is_same_speaker = similarity >= threshold
        
        logger.debug(f"Speaker verification: similarity={similarity:.4f}, threshold={threshold}, match={is_same_speaker}")
        
        return is_same_speaker, similarity
    
    def validate_embedding(self, embedding: np.ndarray) -> bool:
        """
        Validate that an embedding has the correct format and dimensions.
        
        Args:
            embedding: Embedding vector to validate
            
        Returns:
            bool: True if embedding is valid, False otherwise
        """
        try:
            # Check if it's a numpy array
            if not isinstance(embedding, np.ndarray):
                return False
            
            # Check dimensions
            if embedding.ndim != 1 or embedding.shape[0] != 192:
                return False
            
            # Check for NaN or infinite values
            if not np.isfinite(embedding).all():
                return False
            
            # Check if embedding is not all zeros
            if np.allclose(embedding, 0):
                return False
            
            return True
            
        except Exception:
            return False
    
    def get_model_info(self) -> dict:
        """
        Get information about the loaded model.
        
        Returns:
            dict: Model information including status and configuration
        """
        return {
            "model_loaded": self._model_loaded,
            "model_cache_dir": self.model_cache_dir,
            "embedding_dimension": 192,
            "device": "cpu",
            "model_name": "speechbrain/spkrec-ecapa-voxceleb"
        }


# Global instance for reuse across requests
_embedding_service: Optional[EmbeddingService] = None


def get_embedding_service() -> EmbeddingService:
    """
    Get the global embedding service instance.
    
    Returns:
        EmbeddingService: The global embedding service instance
    """
    global _embedding_service
    if _embedding_service is None:
        _embedding_service = EmbeddingService()
    return _embedding_service