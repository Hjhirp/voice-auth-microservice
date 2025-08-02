# Requirements Document

## Introduction

This feature implements a production-ready Python voice authentication microservice using FastAPI that provides speaker enrollment and verification capabilities. The service integrates with Supabase for data persistence, SpeechBrain ECAPA for speaker recognition, VAPI for live audio capture, and Duo for multi-factor authentication. The microservice is designed to be deployed in a Kubernetes environment with comprehensive observability and testing.

## Requirements

### Requirement 1

**User Story:** As a system administrator, I want a voice authentication microservice that can enroll users and verify their identity through voice biometrics, so that I can provide secure voice-based authentication for my applications.

#### Acceptance Criteria

1. WHEN the service starts THEN it SHALL initialize FastAPI with health check endpoint at /healthz
2. WHEN the service receives a request THEN it SHALL log with correlation ID from X-Call-ID header
3. WHEN the service shuts down THEN it SHALL gracefully close WebSocket connections and flush telemetry traces
4. IF environment variables are missing THEN the service SHALL fail to start with clear error messages

### Requirement 2

**User Story:** As a dashboard user, I want to enroll users for voice authentication by providing their audio samples, so that they can later be verified through voice biometrics.

#### Acceptance Criteria

1. WHEN POST /enroll-user receives valid JSON with userId, phone, and audioUrl THEN it SHALL download the audio file
2. WHEN audio is downloaded THEN it SHALL convert to 16kHz mono WAV format using ffmpeg
3. WHEN audio is processed THEN it SHALL generate 192-dimensional embedding using SpeechBrain ECAPA-TDNN
4. WHEN embedding is generated THEN it SHALL upsert user record in Supabase with phone, embedding, and enrolled_at timestamp
5. WHEN enrollment succeeds THEN it SHALL respond with {"status": "enrolled", "score": 1.0}
6. IF audio download fails THEN it SHALL respond with 400 error and descriptive message
7. IF audio conversion fails THEN it SHALL respond with 422 error and descriptive message
8. IF database operation fails THEN it SHALL respond with 500 error and log the exception

### Requirement 3

**User Story:** As a VAPI integration, I want to verify user identity through live voice capture and multi-factor authentication, so that I can provide secure access to protected resources.

#### Acceptance Criteria

1. WHEN POST /verify-password receives valid JSON with userId and listenUrl THEN it SHALL open WebSocket connection to listenUrl
2. WHEN WebSocket is connected THEN it SHALL buffer PCM audio data for approximately 3 seconds or until 2 seconds of silence
3. WHEN sufficient audio is captured THEN it SHALL close WebSocket and process the audio buffer
4. WHEN live audio is processed THEN it SHALL generate embedding and fetch stored user embedding from database
5. WHEN embeddings are available THEN it SHALL compute cosine similarity score
6. IF similarity score is below threshold (default 0.82) THEN it SHALL respond immediately with failure JSON
7. IF similarity score meets threshold THEN it SHALL initiate Duo push notification asynchronously
8. WHEN Duo push is sent THEN it SHALL poll for approval with maximum 60 second timeout
9. IF Duo approval succeeds THEN it SHALL fetch user records from DATA_URL/records/{userId}
10. WHEN records are fetched THEN it SHALL respond with success JSON containing records for VAPI to speak
11. IF any step fails THEN it SHALL log the auth attempt in auth_attempts table with success=false

### Requirement 4

**User Story:** As a database administrator, I want user voice data and authentication attempts to be stored securely in Supabase, so that the system can maintain user enrollment state and audit trails.

#### Acceptance Criteria

1. WHEN service initializes THEN it SHALL connect to Supabase using service role key from environment
2. WHEN user enrollment occurs THEN it SHALL store user record with id, phone, embedding (float8[192]), and enrolled_at timestamp
3. WHEN authentication attempt occurs THEN it SHALL log attempt with user_id, success boolean, similarity score, and created_at timestamp
4. WHEN database operations fail THEN it SHALL retry with exponential backoff up to 3 attempts
5. IF connection pool is exhausted THEN it SHALL queue requests and respond with 503 when queue is full

### Requirement 5

**User Story:** As a DevOps engineer, I want the microservice to be containerized with proper configuration management, so that I can deploy it reliably on cloud platforms like Render.

#### Acceptance Criteria

1. WHEN Docker image is built THEN it SHALL use multi-stage build to minimize image size and comply with Render's deployment requirements
2. WHEN container starts THEN it SHALL read configuration from environment variables: SUPABASE_URL, SUPABASE_SERVICE_KEY, DUO_HOST, DUO_IKEY, DUO_SKEY, DATA_URL, VOICE_THRESHOLD, PORT
3. WHEN deployed on Render THEN it SHALL bind to 0.0.0.0 and use PORT environment variable (default 8000)
4. WHEN SpeechBrain models are loaded THEN it SHALL use CPU-only mode for compatibility with Render's infrastructure
5. WHEN deployed THEN it SHALL respond to health checks at /healthz endpoint
6. WHEN service receives SIGTERM THEN it SHALL gracefully shutdown within 30 seconds
7. WHEN deployed on Render THEN it SHALL handle cold starts efficiently by caching model initialization

### Requirement 6

**User Story:** As a developer, I want comprehensive test coverage and observability, so that I can maintain and troubleshoot the service effectively.

#### Acceptance Criteria

1. WHEN tests run THEN they SHALL achieve minimum 90% code coverage
2. WHEN service processes requests THEN it SHALL emit structured logs with correlation IDs
3. WHEN service operates THEN it SHALL export OpenTelemetry traces and metrics
4. WHEN errors occur THEN they SHALL be logged with appropriate severity levels
5. WHEN integration tests run THEN they SHALL use testcontainers for database and external service mocking

### Requirement 7

**User Story:** As an API consumer, I want clear API documentation and examples, so that I can integrate with the voice authentication service effectively.

#### Acceptance Criteria

1. WHEN service starts THEN it SHALL serve OpenAPI documentation at /docs endpoint
2. WHEN README is accessed THEN it SHALL contain setup instructions, environment variable descriptions, and curl examples
3. WHEN deployment guide is needed THEN it SHALL include Render deployment instructions with environment variable configuration
4. WHEN troubleshooting is needed THEN it SHALL provide common error scenarios and solutions
5. WHEN deploying to Render THEN it SHALL include render.yaml configuration file for automated deployments