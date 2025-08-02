"""Supabase client for database operations."""

import asyncio
import logging
from datetime import datetime
from typing import List, Optional
from uuid import UUID

import numpy as np
from supabase import create_client, Client
from postgrest.exceptions import APIError

from ..config import settings
from ..models.internal_models import User, AuthAttempt

logger = logging.getLogger(__name__)


class SupabaseClient:
    """Client for Supabase database operations."""
    
    def __init__(self):
        """Initialize Supabase client with configuration."""
        self._client: Optional[Client] = None
        self._url = settings.supabase_url
        self._key = settings.supabase_anon_key
    
    @property
    def client(self) -> Client:
        """Get or create Supabase client instance."""
        if self._client is None:
            self._client = create_client(self._url, self._key)
        return self._client
    
    async def health_check(self) -> bool:
        """Check if database connection is healthy."""
        try:
            # Simple query to test connection
            result = self.client.table("users").select("count", count="exact").limit(0).execute()
            return True
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return False


class UserRepository:
    """Repository for user database operations."""
    
    def __init__(self, supabase_client: SupabaseClient):
        """Initialize repository with Supabase client."""
        self.client = supabase_client
    
    async def create_or_update_user(self, user: User) -> User:
        """Create a new user or update existing user (upsert operation)."""
        try:
            # Convert numpy array to list for JSON serialization
            embedding_list = user.embedding.tolist()
            
            user_data = {
                "id": str(user.id),
                "phone": user.phone,
                "embedding": embedding_list,
                "enrolled_at": user.enrolled_at.isoformat()
            }
            
            # Use upsert to handle both create and update cases
            result = self.client.client.table("users").upsert(
                user_data,
                on_conflict="id"
            ).execute()
            
            if not result.data:
                raise ValueError("Failed to create/update user")
            
            logger.info(f"Successfully upserted user {user.id}")
            return user
            
        except APIError as e:
            logger.error(f"Database error creating/updating user {user.id}: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error creating/updating user {user.id}: {e}")
            raise
    
    async def get_user_by_id(self, user_id: UUID) -> Optional[User]:
        """Retrieve user by ID."""
        try:
            result = self.client.client.table("users").select("*").eq("id", str(user_id)).execute()
            
            if not result.data:
                return None
            
            user_data = result.data[0]
            
            # Convert embedding list back to numpy array
            embedding = np.array(user_data["embedding"], dtype=np.float64)
            
            return User(
                id=UUID(user_data["id"]),
                phone=user_data["phone"],
                embedding=embedding,
                enrolled_at=datetime.fromisoformat(user_data["enrolled_at"].replace('Z', '+00:00'))
            )
            
        except APIError as e:
            logger.error(f"Database error retrieving user {user_id}: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error retrieving user {user_id}: {e}")
            raise
    
    async def get_user_by_phone(self, phone: str) -> Optional[User]:
        """Retrieve user by phone number."""
        try:
            result = self.client.client.table("users").select("*").eq("phone", phone).execute()
            
            if not result.data:
                return None
            
            user_data = result.data[0]
            
            # Convert embedding list back to numpy array
            embedding = np.array(user_data["embedding"], dtype=np.float64)
            
            return User(
                id=UUID(user_data["id"]),
                phone=user_data["phone"],
                embedding=embedding,
                enrolled_at=datetime.fromisoformat(user_data["enrolled_at"].replace('Z', '+00:00'))
            )
            
        except APIError as e:
            logger.error(f"Database error retrieving user by phone {phone}: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error retrieving user by phone {phone}: {e}")
            raise
    
    async def delete_user(self, user_id: UUID) -> bool:
        """Delete user by ID."""
        try:
            result = self.client.client.table("users").delete().eq("id", str(user_id)).execute()
            
            success = len(result.data) > 0
            if success:
                logger.info(f"Successfully deleted user {user_id}")
            else:
                logger.warning(f"User {user_id} not found for deletion")
            
            return success
            
        except APIError as e:
            logger.error(f"Database error deleting user {user_id}: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error deleting user {user_id}: {e}")
            raise


class AuthAttemptRepository:
    """Repository for authentication attempt database operations."""
    
    def __init__(self, supabase_client: SupabaseClient):
        """Initialize repository with Supabase client."""
        self.client = supabase_client
    
    async def create_auth_attempt(self, auth_attempt: AuthAttempt) -> AuthAttempt:
        """Create a new authentication attempt record."""
        try:
            attempt_data = {
                "user_id": str(auth_attempt.user_id),
                "success": auth_attempt.success,
                "score": auth_attempt.score,
                "created_at": auth_attempt.created_at.isoformat()
            }
            
            result = self.client.client.table("auth_attempts").insert(attempt_data).execute()
            
            if not result.data:
                raise ValueError("Failed to create auth attempt")
            
            # Update the auth_attempt with the generated ID
            created_data = result.data[0]
            auth_attempt.id = created_data["id"]
            
            logger.info(f"Successfully created auth attempt {auth_attempt.id} for user {auth_attempt.user_id}")
            return auth_attempt
            
        except APIError as e:
            logger.error(f"Database error creating auth attempt for user {auth_attempt.user_id}: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error creating auth attempt for user {auth_attempt.user_id}: {e}")
            raise
    
    async def get_auth_attempts_by_user(self, user_id: UUID, limit: int = 100) -> List[AuthAttempt]:
        """Retrieve authentication attempts for a user."""
        try:
            result = (
                self.client.client.table("auth_attempts")
                .select("*")
                .eq("user_id", str(user_id))
                .order("created_at", desc=True)
                .limit(limit)
                .execute()
            )
            
            attempts = []
            for attempt_data in result.data:
                attempts.append(AuthAttempt(
                    id=attempt_data["id"],
                    user_id=UUID(attempt_data["user_id"]),
                    success=attempt_data["success"],
                    score=attempt_data["score"],
                    created_at=datetime.fromisoformat(attempt_data["created_at"].replace('Z', '+00:00'))
                ))
            
            return attempts
            
        except APIError as e:
            logger.error(f"Database error retrieving auth attempts for user {user_id}: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error retrieving auth attempts for user {user_id}: {e}")
            raise
    
    async def get_recent_failed_attempts(self, user_id: UUID, minutes: int = 60) -> int:
        """Get count of recent failed authentication attempts for a user."""
        try:
            # Calculate timestamp for X minutes ago
            from datetime import timedelta
            cutoff_time = datetime.utcnow() - timedelta(minutes=minutes)
            
            result = (
                self.client.client.table("auth_attempts")
                .select("count", count="exact")
                .eq("user_id", str(user_id))
                .eq("success", False)
                .gte("created_at", cutoff_time.isoformat())
                .execute()
            )
            
            return result.count or 0
            
        except APIError as e:
            logger.error(f"Database error counting failed attempts for user {user_id}: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error counting failed attempts for user {user_id}: {e}")
            raise


class DatabaseManager:
    """High-level database manager that coordinates repositories."""
    
    def __init__(self):
        """Initialize database manager with client and repositories."""
        self.client = SupabaseClient()
        self.users = UserRepository(self.client)
        self.auth_attempts = AuthAttemptRepository(self.client)
    
    async def health_check(self) -> bool:
        """Check overall database health."""
        return await self.client.health_check()
    
    async def retry_operation(self, operation, max_retries: int = 3, base_delay: float = 1.0):
        """Retry database operations with exponential backoff."""
        last_exception = None
        
        for attempt in range(max_retries):
            try:
                return await operation()
            except Exception as e:
                last_exception = e
                if attempt < max_retries - 1:
                    delay = base_delay * (2 ** attempt)
                    logger.warning(f"Database operation failed (attempt {attempt + 1}/{max_retries}), retrying in {delay}s: {e}")
                    await asyncio.sleep(delay)
                else:
                    logger.error(f"Database operation failed after {max_retries} attempts: {e}")
        
        raise last_exception