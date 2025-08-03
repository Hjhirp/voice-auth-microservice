"""Internal data models for the voice authentication microservice."""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

import numpy as np


@dataclass
class User:
    """Internal user model for voice authentication."""
    
    phone: str  # Primary key - unique phone number
    embedding: np.ndarray  # 192-dimensional speaker embedding
    enrolled_at: datetime
    
    def __post_init__(self):
        """Validate embedding dimensions after initialization."""
        if self.embedding.shape != (192,):
            raise ValueError(f"Embedding must be 192-dimensional, got {self.embedding.shape}")


@dataclass
class AuthAttempt:
    """Internal model for authentication attempt logging."""
    
    phone: str  # Phone number of the user attempting authentication
    success: bool
    score: Optional[float]
    created_at: datetime
    id: Optional[int] = None  # Database-generated ID
    
    def __post_init__(self):
        """Validate score range after initialization."""
        if self.score is not None and not (0.0 <= self.score <= 1.0):
            raise ValueError(f"Score must be between 0.0 and 1.0, got {self.score}")