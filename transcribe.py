#!/usr/bin/env python3
"""Download audio from a YouTube URL and transcribe it using OpenAI Whisper."""

import argparse
import os
import subprocess
import sys


def get_video_title(url: str) -> str:
    """Get the video title from YouTube for use in output filenames."""
    cmd = ["yt-dlp", "--print", "title", "--no-playlist", url]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode == 0 and result.stdout.strip():
        title = result.stdout.strip()
        for ch in r'<>:"/\|?*':
            title = title.replace(ch, "")
        return title.strip() or "transcript"
    return "transcript"


def download_audio(url: str, output_dir: str, title: str) -> str:
    """Download audio from a YouTube URL using yt-dlp.

    Skips download if the audio file already exists.
    """
    audio_path = os.path.join(output_dir, f"{title}.mp3")

    if os.path.exists(audio_path):
        print(f"  Audio already exists, skipping download.")
        return audio_path

    output_template = os.path.join(output_dir, f"{title}.%(ext)s")
    cmd = [
        "yt-dlp",
        "--extract-audio",
        "--audio-format", "mp3",
        "--audio-quality", "0",
        "-o", output_template,
        "--no-playlist",
        url,
    ]
    print(f"  Downloading audio...")
    result = subprocess.run(cmd)
    if result.returncode != 0:
        print("  yt-dlp failed. See error above.", file=sys.stderr)
        return ""

    if not os.path.exists(audio_path):
        print(f"  Expected file not found: {audio_path}", file=sys.stderr)
        return ""

    print(f"  Audio downloaded.")
    return audio_path


def transcribe_audio(audio_path: str, model_name: str, language: str | None, output_dir: str, title: str) -> None:
    """Transcribe audio file using Whisper and save the result.

    Skips transcription if output files already exist.
    """
    import whisper

    txt_path = os.path.join(output_dir, f"{title}.txt")
    srt_path = os.path.join(output_dir, f"{title}.srt")

    if os.path.exists(txt_path) and os.path.exists(srt_path):
        print(f"  Transcript already exists, skipping.")
        return

    print(f"  Loading Whisper model: {model_name}")
    model = whisper.load_model(model_name)

    print(f"  Transcribing...")
    options = {}
    if language:
        options["language"] = language
    result = model.transcribe(audio_path, **options)

    with open(txt_path, "w", encoding="utf-8") as f:
        f.write(result["text"])
    print(f"  Saved: {txt_path}")

    with open(srt_path, "w", encoding="utf-8") as f:
        for i, seg in enumerate(result["segments"], start=1):
            start = format_timestamp(seg["start"])
            end = format_timestamp(seg["end"])
            text = seg["text"].strip()
            f.write(f"{i}\n{start} --> {end}\n{text}\n\n")
    print(f"  Saved: {srt_path}")


def format_timestamp(seconds: float) -> str:
    """Convert seconds to SRT timestamp format HH:MM:SS,mmm."""
    hrs = int(seconds // 3600)
    mins = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds % 1) * 1000)
    return f"{hrs:02d}:{mins:02d}:{secs:02d},{millis:03d}"


def process_video(url: str, model: str, language: str | None, output_dir: str) -> None:
    """Process a single video: download audio and transcribe."""
    title = get_video_title(url)
    print(f"\n[{title}]")
    print(f"  URL: {url}")

    audio_path = download_audio(url, output_dir, title)
    if not audio_path:
        print(f"  Skipping transcription due to download error.")
        return

    transcribe_audio(audio_path, model, language, output_dir, title)


def main():
    parser = argparse.ArgumentParser(description="Transcribe YouTube videos using Whisper.")
    parser.add_argument("input", help="YouTube URL or path to a text file with URLs (one per line)")
    parser.add_argument(
        "-m", "--model",
        default=os.environ.get("WHISPER_MODEL", "small"),
        help="Whisper model size (tiny, base, small, medium, large). Default: small",
    )
    parser.add_argument(
        "-l", "--language",
        default=os.environ.get("WHISPER_LANGUAGE") or None,
        help="Language code (e.g. en, id, ja). Default: auto-detect",
    )
    parser.add_argument(
        "-o", "--output",
        default="/data",
        help="Output directory. Default: /data",
    )
    args = parser.parse_args()

    os.makedirs(args.output, exist_ok=True)

    # Determine if input is a file or a URL
    input_path = os.path.join(args.output, args.input)
    if os.path.isfile(input_path):
        with open(input_path, "r", encoding="utf-8") as f:
            urls = [line.strip() for line in f if line.strip() and not line.startswith("#")]
        print(f"Found {len(urls)} URL(s) in {args.input}")
    elif args.input.startswith("http"):
        urls = [args.input]
    else:
        print(f"Input is not a valid URL or file: {args.input}", file=sys.stderr)
        sys.exit(1)

    for url in urls:
        process_video(url, args.model, args.language, args.output)

    print("\nAll done!")


if __name__ == "__main__":
    main()
