# Basset Hound OSINT Platform
# Multi-stage Dockerfile for optimized production builds

# =============================================================================
# Stage 1: Builder
# =============================================================================
FROM python:3.12-slim AS builder

# Set environment variables for Python
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /build

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --prefix=/install --no-warn-script-location -r requirements.txt

# =============================================================================
# Stage 2: Production
# =============================================================================
FROM python:3.12-slim AS production

# Labels and metadata
LABEL org.opencontainers.image.title="Basset Hound OSINT Platform" \
      org.opencontainers.image.description="Open Source Intelligence (OSINT) investigation and analysis platform" \
      org.opencontainers.image.vendor="Basset Hound Project" \
      org.opencontainers.image.version="1.0.0" \
      org.opencontainers.image.licenses="MIT" \
      org.opencontainers.image.source="https://github.com/basset-hound/basset-hound" \
      maintainer="Basset Hound Team"

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    APP_HOME=/app \
    APP_USER=basset \
    APP_GROUP=basset

WORKDIR ${APP_HOME}

# Install runtime dependencies only
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    libmagic1 \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Create non-root user for security
RUN groupadd --gid 1000 ${APP_GROUP} \
    && useradd --uid 1000 --gid ${APP_GROUP} --shell /bin/bash --create-home ${APP_USER}

# Copy installed Python packages from builder stage
COPY --from=builder /install /usr/local

# Copy application code
COPY --chown=${APP_USER}:${APP_GROUP} . .

# Create necessary directories and set permissions
RUN mkdir -p /app/logs /app/data /app/uploads \
    && chown -R ${APP_USER}:${APP_GROUP} /app

# Switch to non-root user
USER ${APP_USER}

# Expose ports
# Port 8000: FastAPI (primary)
# Port 5000: Flask (legacy)
EXPOSE 8000 5000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl --fail http://localhost:8000/health || exit 1

# Default command - run FastAPI with uvicorn
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
