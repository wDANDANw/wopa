#!/bin/sh

# entrypoint.sh
set -e  # Exit immediately if any command fails

echo "Current MODE: $MODE"
echo "Current TEST_MODE: $TEST_MODE"

if [ "$MODE" = "test" ]; then
  # We are in testing mode. Decide between unit or integration tests.
  if [ "$TEST_MODE" = "integration" ]; then
    echo "Running integration tests in worker container..."
    pytest --maxfail=1 --disable-warnings -q tests/integration
  else
    echo "Running unit tests in worker container..."
    pytest --maxfail=1 --disable-warnings -q tests/unit
  fi
else
  # Default or MODE=run: Start uvicorn server for normal operation
  echo "Starting worker server in run mode..."
  uvicorn services_server:app --host 0.0.0.0 --port 8001
fi
