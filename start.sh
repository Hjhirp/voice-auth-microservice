#!/bin/bash

# Start script for Render deployment
set -e

echo "Starting Voice Authentication Microservice..."

# Install system dependencies if needed
if command -v apt-get >/dev/null 2>&1; then
    echo "Installing system dependencies..."
    apt-get update && apt-get install -y ffmpeg
fi

# Start the application
exec python -m src.main