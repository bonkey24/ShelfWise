FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    RUNNING_IN_DOCKER=1

WORKDIR /app

# Install system dependencies (libgomp1 required by LightGBM)
RUN apt-get update && \
    apt-get install -y --no-install-recommends libgomp1 && \
    rm -rf /var/lib/apt/lists/*

# Create non-root application user
RUN useradd -m -u 1000 appuser && \
    mkdir -p /app /app/media /app/demo_data /data && \
    chown -R appuser:appuser /app /app/media /app/demo_data /data

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source, demo data, and entrypoint
COPY --chown=appuser:appuser . .
COPY --chown=appuser:appuser demo_data/ /app/demo_data/
COPY --chown=appuser:appuser docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

USER appuser

EXPOSE 8000

ENTRYPOINT ["/usr/local/bin/docker-entrypoint.sh"]

