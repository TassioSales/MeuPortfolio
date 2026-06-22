FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p /root/.nexus /root/nexus_workspace

ENV PYTHONUNBUFFERED=1
ENV TERM=xterm-256color

CMD ["python", "main.py"]
