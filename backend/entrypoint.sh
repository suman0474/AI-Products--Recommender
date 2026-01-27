#!/bin/bash
set -e

# AI Product Recommender - Backend Entrypoint

echo "Starting Backend Service..."

# Ensure we are in the correct directory
cd /app

# Run database migrations or initialization if needed
# (Optional: Add migration commands here if you have them, e.g., flask db upgrade)

# Start Gunicorn with the configuration file
exec gunicorn -c gunicorn.conf.py main:app
