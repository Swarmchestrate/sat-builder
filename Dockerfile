# Dockerfile for SAT Builder
# Swarmchestrate Application Template Builder
# Python 3.12 FastAPI application with Puccini TOSCA processor

FROM python:3.12-slim

# Metadata labels
LABEL maintainer="University of Westminster"
LABEL description="Swarmchestrate Application Template Builder - RESTful API for generating TOSCA templates"
LABEL version="1.0.0"

# Set working directory
WORKDIR /sat-builder

# Set environment variables
# Prevents Python from writing pyc files and buffering stdout/stderr
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies
# wget: for downloading Puccini
# ca-certificates: for SSL/TLS verification
RUN apt-get update && apt-get install -y --no-install-recommends \
    wget \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Install Puccini TOSCA processor
# Puccini is used for TOSCA validation and processing
ARG PUCCINI_DEB=go-puccini_0.22.7-SNAPSHOT-3e85b40_linux_amd64.deb
RUN wget https://github.com/Swarmchestrate/tosca/releases/download/v0.2.4/${PUCCINI_DEB} \
    && (dpkg -i ${PUCCINI_DEB} || (apt-get update && apt-get install -f -y)) \
    && rm -f ${PUCCINI_DEB} \
    && rm -rf /var/lib/apt/lists/*

# Copy and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy example environment as container default configuration
COPY env.template ./.env

# Copy application code and required resources
COPY configs ./configs
COPY src ./src
COPY templates ./templates

# Create logs directory for application logs
RUN mkdir -p logs

# Expose API port
EXPOSE 8000

# Health check endpoint
# Verifies the API is responding correctly
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

# Run the application
# Starts the application package
CMD ["python", "-m", "src"]