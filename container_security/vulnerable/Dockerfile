# Example of vulnerable Docker configuration
FROM ubuntu:latest

# [Vulnerability 1] No specific user - will run as root
# [Vulnerability 2] Installing unnecessary packages
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    curl \
    vim \
    netcat \
    ssh \
    && rm -rf /var/lib/apt/lists/*

# [Vulnerability 3] Hardcoded credentials in image
ENV DB_PASSWORD="super_secret_password"
ENV AWS_ACCESS_KEY="AKIA1234567890"

# [Vulnerability 4] Copying sensitive files
COPY .env /app/.env
COPY secrets.json /app/secrets.json

WORKDIR /app

# [Vulnerability 5] Installing dependencies without version pinning
COPY requirements.txt .
RUN pip3 install -r requirements.txt

# [Vulnerability 6] Exposing unnecessary ports
EXPOSE 22 80 443 5432

# [Vulnerability 7] Running with elevated privileges
CMD ["python3", "app.py"]

# Additional vulnerabilities in this Dockerfile:
# - No health checks
# - Latest tag used for base image
# - No multi-stage build
# - Sensitive files copied into image
# - No cleanup of package manager caches
# - No image scanning during build
