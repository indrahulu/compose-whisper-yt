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
RUN pip install --default-timeout=300 --retries 5 --no-cache-dir -r requirements.txt

COPY transcribe.py .

ENV WHISPER_MODEL=tiny
ENV WHISPER_LANGUAGE=id
ENV PYTHONUNBUFFERED=1

VOLUME /data

ENTRYPOINT ["python", "transcribe.py"]
