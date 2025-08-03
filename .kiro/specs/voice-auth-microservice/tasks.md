# Implementation Plan

- [x] 1. Set up project structure and core configuration
  - Create directory structure for src/, tests/, and configuration files
  - Implement configuration management with environment variables
  - Create requirements.txt with all necessary dependencies
  - Set up basic FastAPI application with health check endpoint
  - _Requirements: 5.2, 5.5, 7.1_

- [x] 2. Implement data models and database layer
  - [x] 2.1 Create Pydantic models for API requests and responses
    - Define EnrollmentRequest, EnrollmentResponse, VerificationRequest, VerificationResponse models
    - Add validation rules and field constraints
    - _Requirements: 2.1, 3.1_
  
  - [x] 2.2 Create internal data models and database entities
    - Implement User and AuthAttempt dataclasses
    - Create database schema SQL scripts
    - _Requirements: 4.2, 4.3_
  
  - [x] 2.3 Implement Supabase client with repository pattern
    - Create SupabaseClient class with connection management
    - Implement UserRepository and AuthAttemptRepository classes
    - Add database operations (create, read, update) with error handling
    - _Requirements: 4.1, 4.4_

- [x] 3. Implement audio processing utilities
  - [x] 3.1 Create audio format conversion functions
    - Implement PCM to WAV conversion utilities
    - Add audio file download functionality with httpx
    - Create ffmpeg integration for format conversion to 16kHz mono
    - _Requirements: 2.2_
  
  - [x] 3.2 Implement WebSocket audio streaming client
    - Create VAPI WebSocket client for live audio capture
    - Implement audio buffering with silence detection
    - Add connection lifecycle management and error handling
    - _Requirements: 3.2, 3.3_

- [-] 4. Integrate SpeechBrain ECAPA model
  - [x] 4.1 Create embedding service with model management
    - Initialize SpeechBrain ECAPA-TDNN model with CPU-only configuration
    - Implement embedding generation function that returns 192-dimensional vectors
    - Add model caching and optimization for Railway deployment
    - _Requirements: 2.3, 5.4, 5.7_
  
  - [x] 4.2 Implement similarity computation and scoring
    - Create cosine similarity calculation function
    - Add threshold-based verification logic with configurable threshold
    - Implement score validation and comparison utilities
    - _Requirements: 3.5, 3.6_

- [x] 5. Implement external service integrations
  - [x] 5.1 Data store API client - REMOVED (pipeline ends at authentication)
    - ~~Create HTTP client for fetching user records from DATA_URL~~
    - ~~Add retry logic and error handling for external API calls~~
    - ~~Implement response parsing and validation~~
    - _Requirements: 3.9, 3.10 - Not applicable (removed per user request)_

- [ ] 6. Implement core business logic services
  - [ ] 6.1 Create authentication service for enrollment workflow
    - Implement enroll_user function that orchestrates audio download, processing, and storage
    - Add validation for enrollment requests and audio files
    - Create error handling for each step of enrollment process
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5_
  
  - [ ] 6.2 Create authentication service for verification workflow
    - Implement verify_password function that handles WebSocket audio capture
    - Add embedding comparison and verification logic
    - Create complete verification flow with proper error handling
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.9, 3.10, 3.11_

- [ ] 7. Implement FastAPI endpoints and middleware
  - [ ] 7.1 Create enrollment endpoint
    - Implement POST /enroll-user endpoint with request validation
    - Add proper error responses for different failure scenarios
    - Integrate with authentication service and return appropriate responses
    - _Requirements: 2.6, 2.7, 2.8_
  
  - [ ] 7.2 Create verification endpoint
    - Implement POST /verify-password endpoint with request validation
    - Add comprehensive error handling and logging
    - Integrate with authentication service and return success/failure responses
    - _Requirements: 3.11_
  
  - [ ] 7.3 Add middleware and application configuration
    - Implement logging middleware with correlation ID support
    - Add CORS middleware and error handling middleware
    - Create graceful shutdown handling for WebSocket connections
    - _Requirements: 1.2, 1.3, 5.6_

- [ ] 8. Implement observability and monitoring
  - [ ] 8.1 Add structured logging with correlation IDs
    - Implement structlog configuration with JSON formatting
    - Add correlation ID extraction from X-Call-ID header
    - Create request/response logging with sanitized data
    - _Requirements: 6.2, 6.3_
  
  - [ ] 8.2 Integrate OpenTelemetry tracing
    - Set up OpenTelemetry SDK with trace export configuration
    - Add custom spans for business operations and external calls
    - Implement metrics collection for performance monitoring
    - _Requirements: 6.2, 6.4_

- [ ] 9. Create deployment configuration
  - [ ] 9.1 Create Docker configuration
    - Write multi-stage Dockerfile optimized for Railway deployment
    - Add .dockerignore file to exclude unnecessary files
    - Test Docker build and container startup locally
    - _Requirements: 5.1_
  
  - [ ] 9.2 Create Railway deployment configuration
    - Write railway.json with service configuration and environment variables
    - Add startup command configuration for uvicorn server
    - Configure health check endpoint and deployment settings
    - _Requirements: 5.3, 5.5, 7.5_



- [ ] 11. Create documentation and deployment guides
  - [ ] 11.1 Write comprehensive README
    - Document setup instructions and environment variable configuration
    - Add curl examples for API endpoints
    - Include troubleshooting guide and common error scenarios
    - _Requirements: 7.2, 7.4_
  
  - [ ] 11.2 Add API documentation and examples
    - Ensure OpenAPI documentation is complete and accurate
    - Add example requests and responses for all endpoints
    - Create deployment guide specific to Railway platform
    - _Requirements: 7.1, 7.3_

- [ ] 12. Final integration and testing
  - [ ] 12.1 Perform end-to-end testing with real services
    - Test complete enrollment flow with actual audio files
    - Verify verification flow with WebSocket audio streaming
    - Test data store API calls
    - _Requirements: All requirements validation_
  
  - [ ] 12.2 Optimize for production deployment
    - Profile application performance and memory usage
    - Optimize model loading and caching for cold starts
    - Verify all error handling and logging works correctly
    - _Requirements: 5.7, 6.4_A