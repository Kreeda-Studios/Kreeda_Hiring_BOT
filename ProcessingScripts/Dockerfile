# ============================================
# HR Bot - Processing Scripts Production Dockerfile
# Optimized build for Python Resume Worker
# ============================================

FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    tesseract-ocr-eng \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Set Python environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONOPTIMIZE=1
ENV PYTHONPATH=/app

# Copy requirements file
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt && \
    rm -rf /root/.cache/pip

# Copy application code
COPY . .

# Create non-root user for security
RUN useradd -m -u 1001 worker && \
    chown -R worker:worker /app

# Switch to non-root user
USER worker

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import redis; r=redis.Redis(host='hrbot-redis', port=6379); r.ping()" || exit 1

# Run the worker
CMD ["python", "main.py"]
