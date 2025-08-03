#!/bin/bash
# Local dev script for Voice Authentication Microservice
# Usage: ./run_local.sh

set -e

# Load environment variables from .env if present
if [ -f .env ]; then
  export $(grep -v '^#' .env | xargs)
fi

# Check for ffmpeg
if ! command -v ffmpeg &> /dev/null; then
  echo "ffmpeg is not installed. Please install it first."
  exit 1
fi

# Start FastAPI backend
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!
echo "Started FastAPI backend (PID $BACKEND_PID) on http://localhost:8000"

# Wait a bit for backend to start
sleep 3

# Start Streamlit dashboard
streamlit run streamlit_dashboard.py &
FRONTEND_PID=$!
echo "Started Streamlit dashboard (PID $FRONTEND_PID) on http://localhost:8501"

echo "Press Ctrl+C to stop both services."

# Wait for both to exit
wait $BACKEND_PID $FRONTEND_PID
