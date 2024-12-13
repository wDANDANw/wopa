###############################################################################
# Dockerfile for Providers Subsystem (Updated)
#
# Purpose:
# This Dockerfile builds an image for the Providers subsystem. It now also installs
# Docker CLI (and if needed docker.io package) so that Terraform’s Docker provider
# can use the host’s Docker daemon when the docker.sock is mounted.
#
# Key Steps:
# 1. Start from python:3.10-slim.
# 2. Install system packages: wget, curl, unzip, adb, gnupg, etc. as before.
# 3. Install Terraform (HashiCorp’s official instructions).
# 4. Install Docker CLI tools (docker.io) so we have `docker` command inside container.
# 5. Copy requirements.txt, install Python deps.
# 6. Copy the providers code.
#
# After building, ensure you run `docker run ... -v /var/run/docker.sock:/var/run/docker.sock`
# and set `DOCKER_HOST=unix:///var/run/docker.sock` inside the container or in Dockerfile if desired.
# This allows Terraform inside the container to connect to the host’s Docker daemon.
###############################################################################

FROM python:3.10-slim

# Install necessary system packages & adb
RUN apt-get update && apt-get install -y \
    wget curl iputils-ping\
    unzip \
    ca-certificates \
    android-tools-adb \
    gnupg software-properties-common

# Install Terraform
RUN wget -O- https://apt.releases.hashicorp.com/gpg | gpg --dearmor | \
    tee /usr/share/keyrings/hashicorp-archive-keyring.gpg > /dev/null && \
    echo "deb [signed-by=/usr/share/keyrings/hashicorp-archive-keyring.gpg] \
    https://apt.releases.hashicorp.com $(lsb_release -cs) main" | \
    tee /etc/apt/sources.list.d/hashicorp.list && \
    apt-get update && apt-get install -y terraform

# Install Docker CLI (docker.io)
RUN apt-get update && apt-get install -y docker.io

# Set working directory inside the container
WORKDIR /providers

# Copy the Python dependencies file (requirements.txt)
COPY requirements.txt /providers/requirements.txt

# Install Python dependencies
RUN pip install -r requirements.txt

# Copy entire Providers codebase
COPY . /providers

# Set environment variables if needed
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/providers

# No default CMD here, rely on entrypoint.sh and MODE.
###############################################################################
# After building this image:
# docker build -t providers:latest .
#
# To run with Docker access:
# docker run -it --rm -v /var/run/docker.sock:/var/run/docker.sock \
#   -e DOCKER_HOST=unix:///var/run/docker.sock providers:latest /bin/bash
#
# Inside container: you can run `docker ps`, `terraform init`, `terraform apply` etc.
###############################################################################
