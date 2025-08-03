# Voice Authentication Microservice

A production-ready Python microservice for voice-based user authentication using SpeechBrain ECAPA-TDNN speaker recognition, FastAPI, and real-time audio processing.

## Features

- **Voice Enrollment**: Register users with voice samples via audio URL download
- **Real-time Verification**: Authenticate users through live WebSocket audio capture from VAPI
- **Speaker Recognition**: 192-dimensional embeddings using SpeechBrain ECAPA-TDNN model
- **Production Ready**: Comprehensive error handling, logging, metrics, and tracing
- **Scalable**: Containerized deployment with Railway/Docker support
- **Secure**: Rate limiting, CORS, security headers, and correlation ID tracking

## Quick Start

### Prerequisites

- Python 3.11+
- ffmpeg (for audio processing)
- Supabase database (for user storage)

### Local Development

1. **Clone and setup environment:**
```bash
git clone <repository-url>
cd voice-auth-microservice
conda env create -f environment.yml
conda activate voice-auth-microservice
```

2. **Configure environment variables:**
```bash
export SUPABASE_URL="your-supabase-url"
export SUPABASE_ANON_KEY="your-supabase-anon-key"
export VOICE_THRESHOLD="0.82"
export LOG_LEVEL="INFO"
export PORT="8000"
```

3. **Run the service:**
```bash
python -m src.main
```

4. **Access the API:**
- API Documentation: http://localhost:8000/docs
- Health Check: http://localhost:8000/healthz
- Metrics: http://localhost:8000/metrics

## API Endpoints

### POST /api/v1/enroll-user

Enroll a user for voice authentication.

**Request:**
```json
{
  "userId": "123e4567-e89b-12d3-a456-426614174000",
  "phone": "+1234567890",
  "audioUrl": "https://example.com/audio.wav"
}
```

**Success Response (200):**
```json
{
  "status": "enrolled",
  "score": 1.0
}
```

**cURL Example:**
```bash
curl -X POST "http://localhost:8000/api/v1/enroll-user" \
  -H "Content-Type: application/json" \
  -H "X-Call-ID: req-12345" \
  -d '{
    "userId": "123e4567-e89b-12d3-a456-426614174000",
    "phone": "+1234567890",
    "audioUrl": "https://example.com/sample-voice.wav"
  }'
```

### POST /api/v1/verify-password

Verify user identity through voice authentication.

**Request:**
```json
{
  "userId": "123e4567-e89b-12d3-a456-426614174000",
  "listenUrl": "wss://api.vapi.ai/call/listen/abc123"
}
```

**Success Response (200):**
```json
{
  "success": true,
  "message": "Voice verification successful",
  "records": null,
  "score": 0.89
}
```

**cURL Example:**
```bash
curl -X POST "http://localhost:8000/api/v1/verify-password" \
  -H "Content-Type: application/json" \
  -H "X-Call-ID: req-67890" \
  -d '{
    "userId": "123e4567-e89b-12d3-a456-426614174000",
    "listenUrl": "wss://api.vapi.ai/call/listen/abc123"
  }'
```

### GET /api/v1/users/{user_id}/auth-history

Get authentication history for a user.

**Success Response (200):**
```json
{
  "user_id": "123e4567-e89b-12d3-a456-426614174000",
  "attempts": [
    {
      "id": 1,
      "success": true,
      "score": 0.89,
      "created_at": "2024-01-15T10:30:00Z"
    }
  ],
  "correlation_id": "req-67890"
}
```

## Environment Variables

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `SUPABASE_URL` | Supabase project URL | - | Yes |
| `SUPABASE_ANON_KEY` | Supabase anonymous key | - | Yes |
| `VOICE_THRESHOLD` | Voice similarity threshold (0.0-1.0) | 0.82 | No |
| `MAX_AUDIO_DURATION` | Maximum audio capture duration (seconds) | 30 | No |
| `WEBSOCKET_TIMEOUT` | WebSocket connection timeout (seconds) | 65 | No |
| `LOG_LEVEL` | Logging level (DEBUG/INFO/WARNING/ERROR) | INFO | No |
| `PORT` | Service port | 8000 | No |
| `HOST` | Service host | 0.0.0.0 | No |

## Database Schema

The service requires the following Supabase tables:

### users table
```sql
CREATE TABLE users (
    id UUID PRIMARY KEY,
    phone VARCHAR(20) NOT NULL,
    embedding FLOAT8[192] NOT NULL,
    enrolled_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

### auth_attempts table
```sql
CREATE TABLE auth_attempts (
    id SERIAL PRIMARY KEY,
    user_id UUID REFERENCES users(id),
    success BOOLEAN NOT NULL,
    score FLOAT8,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

## Railway Deployment

### Automatic Deployment

1. **Connect Railway to your repository**
2. **Set environment variables in Railway dashboard:**
   - `SUPABASE_URL`
   - `SUPABASE_ANON_KEY`
   - `VOICE_THRESHOLD` (optional)
   - `LOG_LEVEL` (optional)

3. **Deploy:** Railway will automatically build and deploy using the included `railway.json` configuration.

### Manual Deployment

```bash
# Install Railway CLI
npm install -g @railway/cli

# Login to Railway
railway login

# Link to your project
railway link

# Set environment variables
railway variables set SUPABASE_URL=your-url
railway variables set SUPABASE_ANON_KEY=your-key

# Deploy
railway up
```

## Docker Deployment

### Build and Run Locally

```bash
# Build the Docker image
docker build -t voice-auth-microservice .

# Run the container
docker run -p 8000:8000 \
  -e SUPABASE_URL=your-url \
  -e SUPABASE_ANON_KEY=your-key \
  voice-auth-microservice
```

### Docker Compose

```yaml
version: '3.8'
services:
  voice-auth:
    build: .
    ports:
      - "8000:8000"
    environment:
      - SUPABASE_URL=your-url
      - SUPABASE_ANON_KEY=your-key
      - VOICE_THRESHOLD=0.82
      - LOG_LEVEL=INFO
    restart: unless-stopped
```

## Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   VAPI Client   │────│  FastAPI Service │────│   Supabase DB   │
│  (WebSocket)    │    │                  │    │                 │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                              │
                              │
                       ┌──────────────────┐
                       │   SpeechBrain    │
                       │   ECAPA-TDNN     │
                       └──────────────────┘
```

### Components

- **FastAPI Application**: REST API with WebSocket support
- **SpeechBrain ECAPA-TDNN**: Speaker recognition model for embedding generation
- **Supabase**: PostgreSQL database for user and authentication data
- **VAPI Integration**: Real-time audio capture via WebSocket
- **Audio Processing**: ffmpeg for format conversion and preprocessing

## Monitoring & Observability

### Health Checks
- **Service Health**: `GET /healthz`
- **Component Health**: `GET /api/v1/health`
- **Metrics**: `GET /metrics`

### Structured Logging
All logs include correlation IDs and structured data:
```json
{
  "timestamp": "2024-01-15T10:30:00Z",
  "level": "INFO",
  "logger": "voice-auth",
  "correlation_id": "req-12345",
  "message": "Enrollment completed successfully",
  "user_id": "123e4567-e89b-12d3-a456-426614174000",
  "processing_time": 2.45
}
```

### OpenTelemetry Tracing
- Automatic instrumentation for FastAPI and HTTP clients
- Custom spans for business operations
- Metrics collection for performance monitoring

## Error Handling

### Common Error Responses

**400 Bad Request - Invalid Audio URL:**
```json
{
  "error": "AudioDownloadError",
  "message": "Failed to download audio: HTTP error 404",
  "correlation_id": "req-12345",
  "timestamp": "2024-01-15T10:30:00Z"
}
```

**422 Unprocessable Entity - Audio Processing Failed:**
```json
{
  "error": "AudioProcessingError",
  "message": "Failed to process audio: Audio file too short",
  "correlation_id": "req-12345",
  "timestamp": "2024-01-15T10:30:00Z"
}
```

**404 Not Found - User Not Enrolled:**
```json
{
  "error": "UserNotFoundError",
  "message": "User not enrolled for voice authentication",
  "correlation_id": "req-12345",
  "timestamp": "2024-01-15T10:30:00Z"
}
```

**500 Internal Server Error:**
```json
{
  "error": "InternalServerError",
  "message": "An unexpected error occurred",
  "correlation_id": "req-12345",
  "timestamp": "2024-01-15T10:30:00Z"
}
```

## Troubleshooting

### Common Issues

**1. Model Loading Failed**
```
ERROR: Failed to load SpeechBrain model
```
- **Solution**: Ensure sufficient memory (>2GB) and stable internet connection for model download
- **Railway**: Use a plan with adequate memory allocation

**2. Audio Download Timeout**
```
ERROR: Timeout downloading audio from URL
```
- **Solution**: Check audio URL accessibility and increase timeout if needed
- **Check**: Ensure audio files are publicly accessible

**3. WebSocket Connection Failed**
```
ERROR: Failed to connect to VAPI WebSocket
```
- **Solution**: Verify VAPI listenUrl format and network connectivity
- **Format**: Must use `wss://` protocol

**4. Database Connection Error**
```
ERROR: Database health check failed
```
- **Solution**: Verify Supabase URL and keys, check network connectivity
- **Check**: Ensure Supabase project is active and accessible

**5. Memory Issues on Railway**
```
ERROR: Process killed (OOM)
```
- **Solution**: Upgrade to higher memory plan or optimize model caching
- **Optimization**: Set `SPEECHBRAIN_CACHE_DIR` to persistent storage

### Debug Mode

Enable debug logging for troubleshooting:
```bash
export LOG_LEVEL=DEBUG
```

### Performance Optimization

**Cold Start Optimization:**
- SpeechBrain models are cached after first load
- Use Railway persistent storage for model cache
- Consider model preloading in container image

**Memory Usage:**
- CPU-only mode for Railway compatibility
- Single worker process to minimize memory footprint
- Efficient audio processing with temporary file cleanup

## Development

### Testing

```bash
# Run unit tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=src --cov-report=html

# Run specific test file
pytest tests/test_auth_service.py -v
```

### Code Quality

```bash
# Format code
black src/ tests/

# Sort imports
isort src/ tests/

# Lint code
flake8 src/ tests/

# Type checking
mypy src/
```

## Security

- **Rate Limiting**: 100 requests per minute per IP
- **CORS**: Configurable allowed origins
- **Security Headers**: XSS protection, content type options, frame options
- **Input Validation**: Pydantic models with strict validation
- **Error Sanitization**: No sensitive data in error responses
- **Non-root Container**: Runs as unprivileged user in Docker

## License

MIT

## Support

For issues and questions:
1. Check the troubleshooting section above
2. Review logs with correlation IDs
3. Open an issue in the repository
4. Contact the development team

---

**Production Checklist:**
- [ ] Environment variables configured
- [ ] Database tables created
- [ ] Health checks responding
- [ ] Logs structured and accessible
- [ ] Metrics collection enabled
- [ ] Error handling tested
- [ ] Performance validated
- [ ] Security headers verified

---

## Streamlit Dashboard (Frontend)

A modern dashboard for user enrollment, management, and analytics.

### Local Development

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. Run the dashboard:
   ```bash
   streamlit run streamlit_dashboard.py
   ```

### Deploying on Render (No Docker)
- **Build Command:** `pip install -r requirements.txt`
- **Start Command:** `streamlit run streamlit_dashboard.py --server.port $PORT --server.address 0.0.0.0`
- Set environment variables in the Render dashboard (copy from `.env`).

### Deploying on Render (With Docker)
- Use the provided `Dockerfile` and `render.yaml`.

### Environment Variables
- `API_BASE_URL` (for the dashboard, defaults to your Render backend)
- All backend variables (see above)

---

## Project Structure
```
├── src/                  # FastAPI backend code
├── streamlit_dashboard.py # Streamlit frontend
├── requirements.txt      # Python dependencies
├── requirements-railway.txt # (alt) Python dependencies for cloud
├── Dockerfile            # (optional) For Docker deployment
├── render.yaml           # (optional) For Render Docker deployment
├── .env                  # Environment variables
```