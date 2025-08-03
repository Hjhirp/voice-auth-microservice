#!/bin/bash
cd /app
export PYTHONPATH=/app:$PYTHONPATH
exec uvicorn src.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 1 --no-access-log
