FROM ubuntu:20.04

# Avoid timezone prompt
ENV DEBIAN_FRONTEND=noninteractive

# Install required packages
RUN apt-get update && apt-get install -y \
    curl \
    git \
    unzip \
    xz-utils \
    zip \
    libglu1-mesa \
    imagemagick \
    && rm -rf /var/lib/apt/lists/*

# Create a non-root user
RUN useradd -ms /bin/bash developer
USER developer

# Download Flutter SDK
RUN git clone https://github.com/flutter/flutter.git /home/developer/flutter
ENV PATH="/home/developer/flutter/bin:${PATH}"

# Run flutter doctor
RUN flutter doctor

# Enable web
RUN flutter config --enable-web

# Set up app directory
WORKDIR /home/developer/app

# Create asset directories
RUN mkdir -p assets/images assets/icons web/icons

# Switch to root to use ImageMagick
USER root

# Create placeholder icons
RUN convert -size 192x192 xc:#0175C2 -gravity center -pointsize 24 -fill white -draw "text 0,0 'WOPA'" web/icons/Icon-192.png && \
    convert -size 512x512 xc:#0175C2 -gravity center -pointsize 64 -fill white -draw "text 0,0 'WOPA'" web/icons/Icon-512.png && \
    chown -R developer:developer web/icons

# Switch back to developer user
USER developer

# Copy the app files with correct ownership
COPY --chown=developer:developer lib ./lib
COPY --chown=developer:developer pubspec.yaml ./
COPY --chown=developer:developer web ./web
COPY --chown=developer:developer scripts ./scripts

# Make setup script executable
RUN chmod +x scripts/setup.sh

# Start the development server
CMD ["./scripts/setup.sh"] 