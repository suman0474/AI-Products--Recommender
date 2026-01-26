# ============================================================================
# AI Product Recommender - Backend Dockerfile
# ============================================================================
# Multi-stage build for optimized Python/Flask production container

# Stage 1: Builder - Install dependencies in a separate stage
FROM python:3.11-slim-bookworm AS builder

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    libffi-dev \
    libmagic1 \
    libmagic-dev \
    libpq-dev \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy and install requirements
COPY requirements.txt .
RUN pip install --upgrade pip setuptools wheel && \
    pip install -r requirements.txt

# ============================================================================
# Stage 2: Production - Lean runtime image
# ============================================================================
FROM python:3.11-slim-bookworm AS production

# Labels
LABEL maintainer="AI Product Recommender Team" \
    version="1.0.0" \
    description="Backend API for AI Product Recommender"

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONFAULTHANDLER=1 \
    # Flask settings
    FLASK_ENV=production \
    FLASK_APP=main.py \
    # Gunicorn settings
    GUNICORN_BIND=0.0.0.0:5000 \
    GUNICORN_WORKERS=2 \
    GUNICORN_THREADS=4 \
    GUNICORN_TIMEOUT=3600 \
    GUNICORN_LOG_LEVEL=info \
    # Python path
    PATH="/opt/venv/bin:$PATH"

# Install runtime dependencies only
RUN apt-get update && apt-get install -y --no-install-recommends \
    libmagic1 \
    libpq5 \
    curl \
    # Required for PDF processing
    poppler-utils \
    # Required for some image processing
    libgl1-mesa-glx \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Create non-root user for security
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Set working directory
WORKDIR /app

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv

# Copy application source code
COPY --chown=appuser:appuser . .

# Create necessary directories
RUN mkdir -p /app/flask_session /app/instance /app/logs /tmp/flask_session && \
    chown -R appuser:appuser /app /tmp/flask_session

# Create data directories for vector stores and caches
RUN mkdir -p /app/vector_store_data /app/chroma_data && \
    chown -R appuser:appuser /app/vector_store_data /app/chroma_data

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 5000

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:5000/health || exit 1

# Start command - Use gunicorn for production
# Start command - Use entrypoint script
COPY --chown=appuser:appuser entrypoint.sh .
RUN chmod +x entrypoint.sh
ENTRYPOINT ["./entrypoint.sh"]
