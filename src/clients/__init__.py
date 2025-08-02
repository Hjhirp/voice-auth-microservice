"""Client modules for external service integrations."""

from .supabase_client import (
    SupabaseClient,
    UserRepository,
    AuthAttemptRepository,
    DatabaseManager
)

from .vapi_client import (
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