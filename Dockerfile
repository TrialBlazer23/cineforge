###############################
# Builder stage (wheels only) #
###############################
FROM python:3.10.14-slim-bookworm AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Leverage build cache for dependencies
COPY requirements.txt ./
RUN pip install --upgrade pip && \
    pip wheel --no-cache-dir -r requirements.txt -w /wheels

#########################
# Runtime (final image) #
#########################
FROM python:3.10.14-slim-bookworm AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000

WORKDIR /app

# Install only runtime system dependencies
# ffmpeg is required for pydub and video assembly
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
      ffmpeg \
      ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Copy wheels from builder and install
COPY --from=builder /wheels /wheels
COPY requirements.txt ./
RUN pip install --no-cache-dir --no-index --find-links=/wheels -r requirements.txt && \
    rm -rf /wheels

# Create non-root user
RUN useradd --create-home --shell /usr/sbin/nologin appuser

# Copy application code
COPY --chown=appuser:appuser . .

# Expose default API port
EXPOSE 8000

# Drop privileges
USER appuser

# Default command starts the API; workers are started in compose
CMD ["gunicorn", "--bind", ":${PORT}", "--workers", "1", "--threads", "8", "--timeout", "0", "-k", "uvicorn.workers.UvicornWorker", "api:app"]
