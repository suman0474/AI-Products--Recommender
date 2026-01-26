# Docker Deployment Guide - AI Product Recommender (AIPR)

## Overview

This project is containerized with Docker for easy deployment. It consists of:
- **Frontend**: React/Vite application served by Nginx (174MB)
- **Backend**: Flask/Python API with Gunicorn (2.29GB - includes AI/ML dependencies)
- **ChromaDB**: Optional vector database for RAG workflows

## Quick Start

### Prerequisites
- Docker Engine 20.10+ 
- Docker Compose v2+
- At least 4GB RAM for backend container

### 1. Configure Environment Variables

```bash
# Copy the environment template
copy .env.docker.example .env

# Edit .env and fill in required values:
# - SECRET_KEY: Generate a secure random string
# - GOOGLE_API_KEY: Required for AI features
# - Other optional keys as needed
```

### 2. Build and Run

```bash
# Build and start all services
docker compose up -d --build

# Start with ChromaDB (optional)
docker compose --profile chromadb up -d --build
```

### 3. Verify Deployment

```bash
# Check running containers
docker compose ps

# View logs
docker compose logs -f

# Test health endpoints
curl http://localhost/health          # Frontend
curl http://localhost:5000/health     # Backend
```

## Services

### Frontend (aipr-frontend)
- **Port**: 80
- **Technology**: React + Vite + Nginx
- **Image Size**: ~174MB

### Backend (aipr-backend)
- **Port**: 5000
- **Technology**: Flask + Gunicorn + LangChain
- **Image Size**: ~2.29GB (due to AI/ML libraries)

### ChromaDB (optional)
- **Port**: 8000
- **Technology**: ChromaDB vector store
- **Profile**: `chromadb` (use `--profile chromadb` to include)

## Docker Commands Reference

```bash
# Build images only
docker compose build

# Build specific service
docker compose build backend
docker compose build frontend

# Start services (detached)
docker compose up -d

# Stop services
docker compose down

# Stop and remove volumes (data will be lost)
docker compose down -v

# View logs
docker compose logs -f backend
docker compose logs -f frontend

# Restart a service
docker compose restart backend

# Scale services (not applicable for this setup)
docker compose up -d --scale backend=2
```

## Production Deployment Notes

### Security Considerations
1. Always change `SECRET_KEY` in production
2. Use HTTPS (configure SSL in Nginx or use a reverse proxy)
3. Restrict exposed ports using firewalls
4. Use Docker secrets for sensitive environment variables

### Performance Tuning

**Backend (Gunicorn)**:
```yaml
environment:
  - GUNICORN_WORKERS=4        # 2x CPU cores + 1
  - GUNICORN_THREADS=4        # Good for I/O-bound workloads
  - GUNICORN_TIMEOUT=3600     # 1 hour for long AI operations
```

**Frontend (Nginx)**:
- Static assets are cached for 1 year
- Gzip compression enabled
- HTTP/1.1 keep-alive for API proxying

### Health Checks
Both services include health checks:
- Frontend: `GET /health` → returns "healthy"
- Backend: `GET /health` → returns JSON with status

### Persistent Data
The following volumes persist data:
- `aipr-backend-data`: Application data
- `aipr-backend-vector-store`: FAISS/vector embeddings
- `aipr-flask-sessions`: User sessions
- `aipr-backend-instance`: SQLite databases
- `aipr-chromadb-data`: ChromaDB data (if enabled)

## Troubleshooting

### Container won't start
```bash
# Check logs for errors
docker compose logs backend

# Check container status
docker compose ps
```

### API connection errors
1. Ensure backend is healthy: `docker compose ps`
2. Check if port 5000 is accessible
3. Verify CORS settings in backend

### Out of memory
The backend container requires ~2GB RAM. Increase Docker memory limit if needed.

### Build failures
```bash
# Clean up and rebuild
docker compose down --rmi all
docker compose build --no-cache
```

## Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│                 │     │                 │     │                 │
│    Frontend     │────►│    Backend      │────►│   ChromaDB      │
│  (Nginx:80)     │     │ (Gunicorn:5000) │     │   (8000)        │
│                 │ API │                 │ VDB │                 │
└─────────────────┘     └─────────────────┘     └─────────────────┘
         │                      │
         │                      │
         ▼                      ▼
    Static Files         Flask Sessions
    (React Build)        SQLite DBs
                        Vector Stores
                        Azure Blob/Cosmos
```

## File Structure

```
AIPR/
├── docker-compose.yml          # Main orchestration file
├── .env.docker.example         # Environment template
├── .env                        # Your environment config (create this)
│
├── backend/
│   ├── Dockerfile              # Backend container definition
│   ├── .dockerignore           # Excluded from build context
│   ├── requirements.txt        # Python dependencies
│   ├── gunicorn.conf.py        # Production server config
│   └── main.py                 # Flask application
│
└── EnGenie/
    ├── Dockerfile              # Frontend container definition
    ├── .dockerignore           # Excluded from build context
    ├── nginx.conf              # Nginx configuration
    ├── package.json            # Node dependencies
    └── dist/                   # Built React app (created during build)
```
