FROM ubuntu:latest

RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    curl \
    vim \
    netcat-openbsd \
    ssh \
    gcc \
    libc6-dev \
    zlib1g-dev \
    libjpeg-dev \
    && rm -rf /var/lib/apt/lists/*

ENV DB_PASSWORD="super_secret_password"
ENV AWS_ACCESS_KEY="AKIA1234567890"

WORKDIR /app

COPY requirements.txt .
RUN pip3 install --break-system-packages --ignore-installed -r requirements.txt

COPY app.py .

EXPOSE 22 80 443 5432

CMD ["python3", "app.py"]

