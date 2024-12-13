.PHONY: run-backend test-unit-backend run-providers test-unit-providers

run-backend:
	docker compose up --build backend -d

test-unit-backend:
	docker compose run --rm -e MODE=unit-test backend






###############################################################################
# run-providers
#
# Purpose:
# Builds and runs the providers subsystem in normal mode along with the required 
# containers like Ollama (local-llm).
#
# Running:
#   make run-providers
#
# Prerequisite:
# If Ollama or other services needed, docker-compose up local-llm or rely on 
# dependencies in docker-compose.
###############################################################################
.PHONY: run-providers
run-providers:
	docker compose up --build providers -d

###############################################################################
# test-providers
#
# Purpose:
# Runs both unit and integration tests for the Providers subsystem.
#
# Steps:
# 1. Unit Tests:
#    - Mocks external dependencies. Ensures internal logic correct.
# 2. Integration Tests:
#    - Requires Ollama running (and possibly emulator/sandbox if provisioning done).
#
# Running:
#   make test-providers
#
# If failures, review logs. Can isolate tests by changing pytest commands.
###############################################################################
.PHONY: test-providers
test-providers:
# First run unit tests
	docker compose run --rm \
		-e MODE=test \
		-e TEST_MODE=unit \
		providers 


###############################################################################
# run-workers
#
# Purpose:
# Builds and runs the worker service in normal mode along with required containers 
# like redis. The worker server runs uvicorn to host endpoints at e.g. http://localhost:8002
#
# Running:
#   make run-workers
#
# After this, you can access /configs, /workers, etc. to verify functionality.
###############################################################################
run-workers:
	docker compose up --build workers

test-workers: test-unit-workers test-integration-workers

###############################################################################
# test-unit-workers
#
# Purpose:
# Runs unit tests for the Worker Module. Uses MODE=test and TEST_MODE=unit to trigger 
# pytest in unit test directories, mocking external calls and verifying internal logic.
#
# Running:
#   make test-unit-workers
#
# If failures occur, check logs in CI output or run locally with docker compose commands.
###############################################################################
test-unit-workers:
	docker compose run --rm \
		-e MODE=test \
		-e TEST_MODE=unit \
		workers

###############################################################################
# test-integration-workers
#
# Purpose:
# Runs integration tests for the Worker Module. Uses MODE=test and TEST_MODE=integration 
# to trigger pytest in integration directories, relying on real Providers endpoints.
#
# Prerequisite:
# Providers subsystem and possibly ollama/emulator must be running. Consider:
#   make run-providers or ensure providers and ollama are up.
#
# Running:
#   make test-integration-workers
#
# If no error scenarios are triggered or environment stable beyond expectation, 
# some tests may xfail. Adjust environment or tests as needed.
###############################################################################
test-integration-workers:
	docker compose run --rm \
		-e MODE=test \
		-e TEST_MODE=integration \
		workers