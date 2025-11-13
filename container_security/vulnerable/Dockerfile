FROM ubuntu:latest

RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    curl \
    vim \
    netcat \
    ssh \
    && rm -rf /var/lib/apt/lists/*

ENV DB_PASSWORD="super_secret_password"
ENV AWS_ACCESS_KEY="AKIA1234567890"

COPY .env /app/.env
COPY secrets.json /app/secrets.json

WORKDIR /app

COPY requirements.txt .
RUN pip3 install -r requirements.txt

EXPOSE 22 80 443 5432

CMD ["python3", "app.py"]
