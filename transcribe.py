#!/usr/bin/env python3
"""Download audio from a YouTube URL and transcribe it using OpenAI Whisper."""

import argparse
import os
import subprocess
import sys
import whisper


def download_audio(url: str, output_dir: str) -> str:
    """Download audio from a YouTube URL using yt-dlp."""
    output_path = os.path.join(output_dir, "%(title)s.%(ext)s")
    cmd = [
        "yt-dlp",
        "--extract-audio",
        "--audio-format", "mp3",
        "--audio-quality", "0",
        "-o", output_path,
        url,
    ]
    print(f"Downloading audio from: {url}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"yt-dlp error:\n{result.stderr}", file=sys.stderr)
        sys.exit(1)

    # Find the downloaded file
    for line in result.stdout.splitlines():
        if "[ExtractAudio] Destination:" in line:
            return line.split("Destination: ", 1)[1].strip()
        if "[download] " in line and " has already been downloaded" in line:
            path = line.split("[download] ", 1)[1].split(" has already")[0].strip()
            # yt-dlp may report the original format; find the mp3 version
            base, _ = os.path.splitext(path)
            mp3_path = base + ".mp3"
            if os.path.exists(mp3_path):
                return mp3_path
            return path

    # Fallback: find the most recent mp3 in the output directory
    mp3_files = [
        os.path.join(output_dir, f)
        for f in os.listdir(output_dir)
        if f.endswith(".mp3")
    ]
    if mp3_files:
        return max(mp3_files, key=os.path.getmtime)

    print("Could not find downloaded audio file.", file=sys.stderr)
    sys.exit(1)


def transcribe(audio_path: str, model_name: str, language: str | None, output_dir: str) -> None:
    """Transcribe audio file using Whisper and save the result."""
    print(f"Loading Whisper model: {model_name}")
    model = whisper.load_model(model_name)

    print(f"Transcribing: {audio_path}")
    options = {}
    if language:
        options["language"] = language
    result = model.transcribe(audio_path, **options)

    base_name = os.path.splitext(os.path.basename(audio_path))[0]

    # Save plain text
    txt_path = os.path.join(output_dir, f"{base_name}.txt")
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write(result["text"])
    print(f"Transcript saved: {txt_path}")

    # Save SRT subtitles
    srt_path = os.path.join(output_dir, f"{base_name}.srt")
    with open(srt_path, "w", encoding="utf-8") as f:
        for i, seg in enumerate(result["segments"], start=1):
            start = format_timestamp(seg["start"])
            end = format_timestamp(seg["end"])
            text = seg["text"].strip()
            f.write(f"{i}\n{start} --> {end}\n{text}\n\n")
    print(f"SRT saved: {srt_path}")


def format_timestamp(seconds: float) -> str:
    """Convert seconds to SRT timestamp format HH:MM:SS,mmm."""
    hrs = int(seconds // 3600)
    mins = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds % 1) * 1000)
    return f"{hrs:02d}:{mins:02d}:{secs:02d},{millis:03d}"


def main():
    parser = argparse.ArgumentParser(description="Transcribe a YouTube video using Whisper.")
    parser.add_argument("url", help="YouTube video URL")
    parser.add_argument(
        "-m", "--model",
        default=os.environ.get("WHISPER_MODEL", "base"),
        help="Whisper model size (tiny, base, small, medium, large). Default: base",
    )
    parser.add_argument(
        "-l", "--language",
        default=os.environ.get("WHISPER_LANGUAGE"),
        help="Language code (e.g. en, id, ja). Default: auto-detect",
    )
    parser.add_argument(
        "-o", "--output",
        default="/output",
        help="Output directory. Default: /output",
    )
    args = parser.parse_args()

    os.makedirs(args.output, exist_ok=True)

    audio_path = download_audio(args.url, args.output)
    transcribe(audio_path, args.model, args.language, args.output)
    print("Done!")


if __name__ == "__main__":
    main()
