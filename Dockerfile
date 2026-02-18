FROM python:3.11-slim

# Install system dependencies for yt-dlp and whisper
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    git \
    curl \
    unzip \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Install Deno (required by yt-dlp for YouTube bot protection bypass)
RUN curl -fsSL https://deno.land/install.sh | sh -s -- -y
ENV PATH="/root/.deno/bin:${PATH}"

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY app/transcribe.py .

ENV WHISPER_MODEL=tiny
ENV WHISPER_LANGUAGE=id
ENV ENABLE_DOWNLOAD=true
ENV ENABLE_TRANSCRIPTION=false
ENV FORCE_DOWNLOAD_MODEL=false
ENV CHUNK_DURATION=3600
ENV CHUNK_THRESHOLD=7200
ENV PYTHONUNBUFFERED=1

WORKDIR /data
VOLUME /data

ENTRYPOINT ["python", "/app/transcribe.py"]
