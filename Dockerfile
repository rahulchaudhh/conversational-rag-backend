# ============================================================
# Stage 1 — Build dependencies
# ============================================================
FROM python:3.12-slim AS builder

WORKDIR /build

# Install system libs needed to compile psycopg2-binary, etc.
RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc libpq-dev && \
    rm -rf /var/lib/apt/lists/*

# Copy requirements first (layer caching)
COPY requirements.txt .

# Install CPU-only PyTorch FIRST, then the rest of the deps
RUN pip install --no-cache-dir \
        torch --index-url https://download.pytorch.org/whl/cpu && \
    pip install --no-cache-dir -r requirements.txt

# ============================================================
# Stage 2 — Production image
# ============================================================
FROM python:3.12-slim AS production

# Runtime lib for psycopg2
RUN apt-get update && \
    apt-get install -y --no-install-recommends libpq5 curl && \
    rm -rf /var/lib/apt/lists/*

# Create a non-root user
RUN groupadd -r appuser && useradd -r -g appuser -d /app -s /sbin/nologin appuser

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application source code
COPY app/ ./app/
COPY frontend/ ./frontend/
COPY requirements.txt .

# Pre-download the embedding model at build time so the container
# starts instantly and doesn't need internet access on first request.
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('BAAI/bge-small-en-v1.5')"

# Set model cache inside container
ENV HF_HOME=/app/.cache/huggingface
ENV TRANSFORMERS_CACHE=/app/.cache/huggingface

# Move the downloaded model to the app cache dir
RUN mkdir -p /app/.cache/huggingface && \
    cp -r /root/.cache/huggingface/* /app/.cache/huggingface/ 2>/dev/null || true && \
    rm -rf /root/.cache/huggingface

# Give ownership to non-root user
RUN chown -R appuser:appuser /app

USER appuser

# Expose the API port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Start the server
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
