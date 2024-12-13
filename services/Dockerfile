###############################################################################
# Dockerfile for Services
#
# Purpose:
# This Dockerfile defines how to build an image for the Worker Module of WOPA.
# It sets up a Python 3.10 environment, installs all required Python 
# dependencies from requirements.txt, and copies the worker codebase into 
# the image. The Worker Module is responsible for processing various tasks 
# using text, link, and visual verification Services, and can integrate with 
# Providers subsystem endpoints (mocked at unit test level, real in integration).
#
# This Dockerfile does not specify a CMD directly because we use environment 
# variables (like MODE=run or MODE=unit-test) combined with `entrypoint.sh` 
# and docker-compose commands to determine what the container should do 
# (run uvicorn server or run pytest).
#
# Design Steps:
# 1. Start from a lightweight Python 3.10 base image to keep image small and 
#    reduce attack surface.
# 2. Set the working directory to /Services to align with our directory structure.
# 3. Copy requirements.txt and run `pip install` to build a cached layer 
#    so that if only code changes but not dependencies, build times are shorter.
# 4. Copy the entire Services/ code to /Services in the image.
# 5. Do not specify CMD or ENTRYPOINT here since we rely on docker-compose 
#    and the `entrypoint.sh` script to decide whether to run unit tests or 
#    start the server.
#
# Maintainability:
# - If Python version changes, update the FROM line.
# - If dependencies change, modify requirements.txt and rebuild the image.
# - If code layout changes, adjust COPY instructions accordingly.
#
# No pinned versions in requirements.txt are used, per project instructions, 
# to avoid compatibility issues.
###############################################################################

FROM python:3.10-slim

# Set working directory inside the container
WORKDIR /services

# Copy requirements.txt to leverage layer caching when only code changes
COPY requirements.txt /services/requirements.txt

# Install Python dependencies without specifying versions
RUN pip install --no-cache-dir -r requirements.txt

# Copy the entire worker codebase into the image
COPY . /services

# We set PYTHONUNBUFFERED=1 so Python output is not buffered, making logs appear instantly.
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/services

# No ENTRYPOINT or CMD here, since docker-compose sets the command at runtime.
# For example:
# - MODE=run means `entrypoint.sh` will start uvicorn
# - MODE=unit-test means `entrypoint.sh` runs pytest
#
# If you want a default CMD for local testing, you could uncomment the following:
# CMD ["./entrypoint.sh"]
#
# But we trust docker-compose with MODE environment to handle that.

###############################################################################
# Once this image is built, `make run-Services` will run the server in normal mode,
# and `make test-unit-Services` will run unit tests inside the container.
#
# When integration tests begin, this same image is used, but run against real 
# Providers endpoints rather than mocks, once MODE=integration or other logic 
# is provided.
###############################################################################