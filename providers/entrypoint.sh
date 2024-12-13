#!/bin/sh

###############################################################################
# entrypoint.sh for Providers Subsystem
#
# Purpose:
# This script controls the container's runtime behavior for the Providers 
# subsystem based on environment variables, enabling running in server mode 
# (production) or in testing mode (unit/integration).
#
# Environment Variables:
# - MODE:
#   - MODE=run: Start the uvicorn server for normal provider operations.
#   - MODE=test: Enter testing mode.
#
# - TEST_MODE (only relevant if MODE=test):
#   - TEST_MODE=unit: Run unit tests focusing on isolated logic with mocks.
#   - TEST_MODE=integration: Run integration tests that connect to real external 
#     services (LLM, sandbox, emulator).
#   - If TEST_MODE is not set or unrecognized, default to unit tests.
#
# Examples:
# - MODE=run (no TEST_MODE): Run uvicorn to start provider server.
# - MODE=test and TEST_MODE=unit: Run pytest on `providers/unit_tests/`.
# - MODE=test and TEST_MODE=integration: Run pytest on `providers/integration_tests/`.
#
# Steps Implemented:
# 1. Check MODE.
#    - If MODE=run: run uvicorn server.
#    - If MODE=test: check TEST_MODE.
#       - If TEST_MODE=integration: run integration tests.
#       - Else: run unit tests by default.
# 2. Use set -e to fail fast on errors.
#
# Maintainability:
# - If directories change, update paths here.
# - If new test types are added, add another branch.
# - Echo statements for diagnosing selected modes.
###############################################################################

set -e

echo "Current MODE: $MODE"
echo "Current TEST_MODE: $TEST_MODE"

if [ "$MODE" = "test" ]; then
  if [ "$TEST_MODE" = "integration" ]; then
    echo "Integration test mode detected."
    echo "Starting Providers server in background for integration tests..."
    # Start uvicorn in the background and immediately print confirmation

    # Now trying to use docker compose to start the server before running tests
    # uvicorn provider_server:app --host 0.0.0.0 --port 8001 &
    # SERVER_PID=$!
    # echo "Uvicorn started in background with PID $SERVER_PID."

    # echo "Waiting 5 seconds for server startup..."
    # sleep 5
    # echo "Sleep finished. Server should be ready now."

    echo "Running integration tests for Providers..."
    # Use -vv to show test discovery and ensure we see output
    pytest --maxfail=1 --disable-warnings -q -vv tests/integration
    TEST_EXIT_CODE=$?

    echo "Integration tests finished with code $TEST_EXIT_CODE."
    echo "Stopping background uvicorn server..."
    kill $SERVER_PID || true

    exit $TEST_EXIT_CODE

  else
    echo "Running unit tests for Providers..."
    pytest --maxfail=1 --disable-warnings -q -vv tests/unit
  fi

else
  echo "Starting Providers server in run mode..."
  uvicorn provider_server:app --host 0.0.0.0 --port 8003
fi