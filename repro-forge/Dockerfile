# Builder stage
FROM python:3.12-slim AS builder

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY pyproject.toml .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -e ".[all]" && \
    pip install --no-cache-dir uvicorn[standard]


# Runtime stage
FROM python:3.12-slim AS runtime

LABEL org.opencontainers.image.title="ReproForge"
LABEL org.opencontainers.image.description="Automated Paper Reading & Reproduction for CS Research"
LABEL org.opencontainers.image.source="https://github.com/selfrestart/26Summer/tree/main/repro-forge"
LABEL org.opencontainers.image.licenses="Apache-2.0"

WORKDIR /app

# Install minimal system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code
COPY repro_forge/ ./repro_forge/
COPY examples/ ./examples/

# Create non-root user
RUN useradd --create-home --shell /bin/bash reproforge
RUN mkdir -p /app/data /app/outputs /app/mlruns && \
    chown -R reproforge:reproforge /app
USER reproforge

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

ENTRYPOINT ["uvicorn", "repro_forge.api.app:app", "--host", "0.0.0.0", "--port", "8000"]
