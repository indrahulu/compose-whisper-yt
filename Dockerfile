FROM python:3.11-slim

# Install system dependencies for yt-dlp and whisper
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY transcribe.py .

ENV WHISPER_MODEL=small
ENV WHISPER_LANGUAGE=id

VOLUME /data

ENTRYPOINT ["python", "transcribe.py"]
