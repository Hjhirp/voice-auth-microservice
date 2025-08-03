# Multi-stage build for optimized deployment
# Stage 1: Build stage
FROM python:3.11-slim as builder

WORKDIR /app

RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    build-essential \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

COPY requirements-railway.txt requirements.txt
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir --user -r requirements.txt

# Stage 2: Runtime stage
FROM python:3.11-slim as runtime

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH=/home/app/.local/bin:$PATH \
    PYTHONPATH=/app \
    PORT=8000

RUN apt-get update && apt-get install -y \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

RUN useradd --create-home --shell /bin/bash app

WORKDIR /app

COPY --chown=app:app . .
RUN chmod +x /app/start_app.sh

RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements-railway.txt && \
    pip install --no-cache-dir -e .

USER app

RUN mkdir -p /home/app/.cache/speechbrain

EXPOSE $PORT

# Start the application with uvicorn
CMD ["/app/start_app.sh"]