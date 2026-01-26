#!/bin/bash
set -e

# Initialize database
echo "Initializing database..."
python init_db.py

# Start Gunicorn
echo "Starting Application Server..."
exec gunicorn -c gunicorn.conf.py main:app
