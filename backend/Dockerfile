FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install --no-cache-dir emergentintegrations --extra-index-url https://d33sy5i8bnduwe.cloudfront.net/simple/

# Create models directory
RUN mkdir -p /app/models

# Copy application code
COPY . .

# Create non-root user
RUN useradd --create-home --shell /bin/bash kpa
RUN chown -R kpa:kpa /app
USER kpa

# Expose port
EXPOSE 8001

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
  CMD curl -f http://localhost:8001/api/status || exit 1

# Run application
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8001", "--workers", "2"]