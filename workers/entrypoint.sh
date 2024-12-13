#!/bin/sh

###############################################################################
# entrypoint.sh for Worker Module
#
# Purpose:
# This script controls the container's runtime behavior based on environment 
# variables, enabling different modes (run vs. testing) and different test types.
#
# Environment Variables:
# - MODE: Controls whether we run the server or enter testing mode.
#   Possible values:
#     - MODE=run: Start the uvicorn server for normal worker operations.
#     - MODE=test: Enter testing mode (unit or integration tests).
#
# - TEST_MODE: Specifies which type of test to run if MODE=test.
#   Possible values:
#     - TEST_MODE=unit: Run unit tests only, focusing on isolated, mocked scenarios.
#     - TEST_MODE=integration: Run integration tests that connect to real Providers endpoints.
#   If TEST_MODE is not set or unrecognized, default to unit tests.
#
# Examples:
# - MODE=run (no TEST_MODE): Run server via uvicorn.
# - MODE=test and TEST_MODE=unit: Run pytest on `tests/unit` directory.
# - MODE=test and TEST_MODE=integration: Run pytest on `tests/integration` directory.
#
# Maintainability:
# - If more test modes appear later (e.g., performance tests), add another branch.
# - If directories change, update paths accordingly.
# - Logging and echoes help diagnose what mode the container attempted.
#
# Steps Implemented:
# 1. Check MODE.
# 2. If MODE=run: run uvicorn server.
# 3. If MODE=test: check TEST_MODE.
#    - If TEST_MODE=integration: run tests in `tests/integration`
#    - Else (unit or not set): run tests in `tests/unit`
# 4. Set `set -e` to ensure the script fails fast on errors, preventing partial execution.
###############################################################################

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
  uvicorn worker_server:app --host 0.0.0.0 --port 8002
fi
