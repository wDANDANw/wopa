###############################################################################
# Dockerfile for Backend
#
# Purpose:
# This Dockerfile builds an image for the backend service. It installs Python 
# dependencies from requirements.txt, copies the backend code, and sets a 
# working environment. The actual command to run (uvicorn or pytest) is 
# chosen at runtime via docker-compose and the MODE environment variable.
#
# Design & Steps:
# 1. Start from a Python base image (e.g., python:3.10-slim).
# 2. Set a working directory /app
# 3. Copy requirements.txt and run pip install.
# 4. Copy backend code into /app
# 5. By default, we can define an entrypoint or leave it blank since docker-compose 
#    sets the command.
#
# Maintainability:
# - If dependencies change, update requirements.txt and rebuild.
# - If Python version changes, update FROM line.
###############################################################################

FROM python:3.10-slim

# Set working directory
WORKDIR /backend

# Copy requirements.txt
COPY requirements.txt /backend/requirements.txt

# Install dependencies without specifying versions (as requested)
RUN pip install -r requirements.txt

# Copy the backend code
# We assume current Docker build context is `./backend` as set in docker-compose.yml.
# So, copying `.` copies all backend files into /app.
COPY . /backend

# Optionally set environment variables if needed (e.g., PYTHONUNBUFFERED=1).
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/backend

# We do not define CMD or ENTRYPOINT here because docker-compose will supply 
# the command depending on MODE. If we wanted a default, we could do:
# CMD ["uvicorn", "backend_server:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]
# But since we rely on docker-compose, we skip this.

###############################################################################
# After building this image:
# - "make run-backend" runs the container with uvicorn if MODE=run
# - "make test-unit-backend" runs pytest if MODE=unit-test
#
# If we add more build steps or dependencies, update accordingly.
###############################################################################
