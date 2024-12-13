#!/bin/sh

# entrypoint.sh

if [ "$MODE" = "unit-test" ]; then
  pytest --maxfail=1 --disable-warnings -q
else
  uvicorn backend_server:create_app --factory --host 0.0.0.0 --port 8000
fi
