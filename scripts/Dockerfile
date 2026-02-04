FROM python:3.11-slim as python-base

# Install system dependencies
RUN apt-get update && apt-get install -y \
    poppler-utils \
    curl \
    && rm -rf /var/lib/apt/lists/*

FROM python-base as deps

WORKDIR /app

# Install Python dependencies with cache mount for faster rebuilds
COPY requirements.txt ./
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install -r requirements.txt

# Production stage
FROM python-base as production

WORKDIR /app

# Copy installed packages from deps stage
COPY --from=deps /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=deps /usr/local/bin /usr/local/bin

# Copy processing scripts
COPY jd-processing/ ./jd-processing/
COPY resume-processing/ ./resume-processing/
COPY final-ranking/ ./final-ranking/
COPY *.py ./

# Create directories
RUN mkdir -p /app/uploads /app/InputThread/JD

# Run as non-root
RUN useradd -m appuser
RUN chown -R appuser:appuser /app
USER appuser

# Default command - run the BullMQ consumer
CMD ["python", "-u", "bullmq_consumer.py"]
