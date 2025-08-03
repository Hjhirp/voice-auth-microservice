"""Client modules for external service integrations."""

from src.clients.supabase_client import (
    SupabaseClient,
    UserRepository,
    AuthAttemptRepository,
    DatabaseManager
)

from src.clients.vapi_client import (
    VAPIWebSocketClient,
    VAPIConnectionError,
    VAPIAudioError,
    capture_audio_from_vapi
)

__all__ = [
    "SupabaseClient",
    "UserRepository", 
    "AuthAttemptRepository",
    "DatabaseManager",
    "VAPIWebSocketClient",
    "VAPIConnectionError",
    "VAPIAudioError",
    "capture_audio_from_vapi"
]