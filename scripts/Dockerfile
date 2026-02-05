FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    poppler-utils \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy processing scripts
COPY common/ ./common/
COPY jd-processing/ ./jd-processing/
COPY resume-processing/ ./resume-processing/
COPY final-ranking/ ./final-ranking/
COPY *.py ./

# Run as non-root
RUN useradd -m appuser
RUN chown -R appuser:appuser /app
USER appuser

# Default command - run the BullMQ consumer
CMD ["python", "-u", "bullmq_consumer.py"]
