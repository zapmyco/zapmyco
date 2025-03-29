#!/bin/bash
# Simplified startup script

# Change to the script directory
cd "$(dirname "$0")"

# Start uvicorn server (development mode with hot reload)
echo "Starting backend server (development mode)..."
exec poetry run python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
