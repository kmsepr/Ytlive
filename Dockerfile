FROM python:3.11-slim

# -----------------------------
# Environment
# -----------------------------
ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    DEBIAN_FRONTEND=noninteractive

WORKDIR /app

# -----------------------------
# System dependencies
# -----------------------------
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        ffmpeg \
        curl \
        ca-certificates \
        git \
        tini && \
    rm -rf /var/lib/apt/lists/*

# -----------------------------
# Python dependencies
# -----------------------------
RUN pip install --upgrade pip && \
    pip install flask requests yt-dlp gunicorn

# -----------------------------
# Copy app
# -----------------------------
COPY . /app

# -----------------------------
# Expose
# -----------------------------
EXPOSE 8000

# -----------------------------
# Use tini (VERY IMPORTANT for ffmpeg)
# -----------------------------
ENTRYPOINT ["/usr/bin/tini", "--"]

# -----------------------------
# Gunicorn (stream-friendly)
# -----------------------------
CMD ["gunicorn", \
     "-w", "4", \
     "--threads", "4", \
     "--worker-class", "gthread", \
     "--timeout", "0", \
     "-b", "0.0.0.0:8000", \
     "app:app"]
