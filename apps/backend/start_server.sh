#!/bin/bash
# Development server startup script

# Change to the script directory
cd "$(dirname "$0")"

# Enable debug mode with debugpy if the DEBUG environment variable is set
if [ "${DEBUG:-0}" = "1" ]; then
  echo "Starting backend server in debug mode (debugpy enabled)..."
  exec poetry run python -m debugpy --listen 0.0.0.0:5678 -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
elif [ "${DEBUG_DIRECT:-0}" = "1" ]; then
  echo "Starting backend server with direct debug imports..."
  exec poetry run python -c "import debugpy; debugpy.listen(('0.0.0.0', 5678)); print('Waiting for debugger attach...'); debugpy.wait_for_client(); print('Debugger attached!'); import uvicorn; uvicorn.run('main:app', host='0.0.0.0', port=8000, reload=True)"
else
  # Start uvicorn server (development mode with hot reload)
  echo "Starting backend server (development mode)..."
  exec poetry run python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
fi
