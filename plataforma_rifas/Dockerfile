# Multi-user Rifa Platform - Dockerfile
# Use Microsoft DevContainers Python image to avoid Docker Hub auth/rate issues
FROM mcr.microsoft.com/devcontainers/python:3.12

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    STREAMLIT_BROWSER_GATHER_USAGE_STATS=false \
    STREAMLIT_SERVER_HEADLESS=true

# Install build deps for some wheels (e.g., bcrypt) if needed
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       build-essential libffi-dev \
       tzdata \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install dependencies first for better layer caching
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY . .

# Expose Streamlit default port
EXPOSE 8501

# Default environment
ENV JSON_MIRROR=false \
    TZ=Etc/UTC

# Healthcheck: Streamlit exposes /healthz
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
  CMD python -c "import urllib.request,sys; \
u=urllib.request.urlopen('http://127.0.0.1:8501/healthz', timeout=3); \
sys.exit(0 if getattr(u,'status',200)==200 else 1)" || exit 1

# Run the Streamlit app
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
