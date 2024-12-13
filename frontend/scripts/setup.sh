#!/bin/bash

# Create symlink for main.dart if it doesn't exist
if [ ! -f lib/main.dart ]; then
    ln -s frontend_main.dart lib/main.dart
fi

# Get dependencies
flutter pub get

# # Run the development server
# flutter run -d web-server --web-port 3000 --web-hostname 0.0.0.0 

# Build and serve in release mode
flutter build web
flutter run -d web-server --web-port 3000 --web-hostname 0.0.0.0 --release 