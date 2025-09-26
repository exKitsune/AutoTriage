# Example of secure Docker configuration
# Stage 1: Build
FROM python:3.10-slim-bullseye AS builder

# Create non-root user
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Set working directory
WORKDIR /build

# Copy only necessary files
COPY requirements.txt .

# Install dependencies with version pinning
RUN pip install --no-cache-dir -r requirements.txt

# Stage 2: Runtime
FROM python:3.10-slim-bullseye AS runtime

# Create non-root user
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Set working directory
WORKDIR /app

# Copy only necessary files from builder
COPY --from=builder /usr/local/lib/python3.10/site-packages/ /usr/local/lib/python3.10/site-packages/
COPY app/ .

# Switch to non-root user
USER appuser

# Set secure environment defaults
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/home/appuser/.local/bin:$PATH"

# Expose only necessary port
EXPOSE 8080

# Add health check
HEALTHCHECK --interval=30s --timeout=3s \
    CMD curl -f http://localhost:8080/health || exit 1

# Use exec form of CMD
CMD ["python3", "app.py"]

# Security improvements in this Dockerfile:
# - Multi-stage build to reduce attack surface
# - Specific version tags for base images
# - Non-root user
# - Minimal dependencies
# - No sensitive data in image
# - Health checks
# - No unnecessary ports
# - No unnecessary packages
# - Clean build context
