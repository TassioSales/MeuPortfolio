FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy pipeline as a package so relative imports work
COPY . ./pipeline/

ENV PYTHONUNBUFFERED=1
ENV DB_PATH=/data/panorama.db

CMD ["python", "-m", "pipeline.scheduler"]
