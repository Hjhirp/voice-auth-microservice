# Voice Authentication Microservice

A production-ready voice authentication service with speaker enrollment and verification capabilities, built with FastAPI and integrated with VAPI for live audio capture.

## Features

- **Audio Processing**: Download and convert audio files to 16kHz mono WAV format
- **VAPI Integration**: WebSocket client for live audio capture with silence detection
- **Voice Authentication**: Speaker enrollment and verification (coming soon)
- **Production Ready**: Structured logging, health checks, and error handling

## API Endpoints

### Health Check
- `GET /healthz` - Service health check

### Audio Processing
- `GET /api/audio/test` - Test audio processing capabilities
- `POST /api/audio/process` - Process audio file from URL
- `GET /api/audio/formats` - Get supported audio formats

### VAPI Integration
- `GET /api/vapi/test` - Test VAPI client availability
- `POST /api/vapi/capture` - Capture audio from VAPI WebSocket
- `GET /api/vapi/config` - Get VAPI configuration options

## Quick Deploy to Render

1. **Fork this repository** to your GitHub account

2. **Connect to Render**:
   - Go to [Render Dashboard](https://dashboard.render.com)
   - Click "New +" → "Web Service"
   - Connect your GitHub repository

3. **Configure the service**:
   - **Name**: `voice-auth-microservice`
   - **Environment**: `Python`
   - **Build Command**: `pip install -r requirements-prod.txt`
   - **Start Command**: `python -m src.main`

4. **Deploy**: Click "Create Web Service"

The service will be available at: `https://voice-auth-microservice.onrender.com`

## Environment Variables

The following environment variables are pre-configured in `render.yaml`:

```bash
PORT=8000
HOST=0.0.0.0
LOG_LEVEL=INFO
VOICE_THRESHOLD=0.82
MAX_AUDIO_DURATION=30
WEBSOCKET_TIMEOUT=65
SUPABASE_URL=https://uwkkunglqsccaskobeva.supabase.co
SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
DATA_URL=https://test-data-api.com
```

## Testing the Deployment

Once deployed, test the endpoints:

### 1. Health Check
```bash
curl https://your-app.onrender.com/healthz
```

### 2. Audio Processing Test
```bash
curl https://your-app.onrender.com/api/audio/test
```

### 3. VAPI Client Test
```bash
curl https://your-app.onrender.com/api/vapi/test
```

### 4. Process Audio File
```bash
curl -X POST https://your-app.onrender.com/api/audio/process \
  -H "Content-Type: application/json" \
  -d '{"audio_url": "https://example.com/audio.mp3"}'
```

### 5. Capture from VAPI (requires valid VAPI listen URL)
```bash
curl -X POST https://your-app.onrender.com/api/vapi/capture \
  -H "Content-Type: application/json" \
  -d '{
    "listen_url": "wss://phone-call-websocket.aws-us-west-2-backend-production2.vapi.ai/call-id/listen",
    "min_duration": 3.0,
    "silence_duration": 2.0
  }'
```

## Local Development

1. **Clone the repository**:
```bash
git clone <your-repo-url>
cd voice-auth-microservice
```

2. **Install dependencies**:
```bash
pip install -r requirements.txt
```

3. **Install ffmpeg** (required for audio processing):
```bash
# macOS
brew install ffmpeg

# Ubuntu/Debian
sudo apt-get install ffmpeg

# Windows
# Download from https://ffmpeg.org/download.html
```

4. **Set up environment variables**:
```bash
cp .env.example .env
# Edit .env with your values
```

5. **Run the service**:
```bash
python -m src.main
```

The service will be available at `http://localhost:8000`

## Architecture

- **FastAPI**: Modern, fast web framework for building APIs
- **Audio Processing**: ffmpeg integration for format conversion
- **WebSocket Client**: Real-time audio capture from VAPI
- **Structured Logging**: JSON-formatted logs with correlation IDs
- **Health Checks**: Built-in health monitoring
- **Error Handling**: Comprehensive error handling and validation

## Audio Processing Features

- **Format Support**: MP3, WAV, M4A, AAC, OGG, FLAC, WMA
- **Output Format**: 16kHz mono WAV (PCM)
- **Silence Detection**: RMS-based silence detection
- **Duration Limits**: Configurable min/max duration
- **Validation**: Audio format validation

## VAPI Integration Features

- **WebSocket Client**: Connects to VAPI listen URLs
- **Live Capture**: Real-time audio streaming
- **Silence Detection**: Automatic capture termination
- **Buffer Management**: Efficient audio buffering
- **Error Recovery**: Connection retry and error handling

## Production Considerations

- **Security**: Environment variables for sensitive data
- **Monitoring**: Structured logging and health checks
- **Performance**: Optimized dependencies and caching
- **Scalability**: Stateless design for horizontal scaling
- **Reliability**: Graceful error handling and timeouts