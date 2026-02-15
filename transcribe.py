#!/usr/bin/env python3
"""Download audio from a YouTube URL and transcribe it using OpenAI Whisper."""

import argparse
import os
import subprocess
import sys

try:
    import whisper
except ImportError:
    print("Error: openai-whisper not installed", file=sys.stderr)
    sys.exit(1)

# Supported video and audio file extensions
SUPPORTED_EXTENSIONS = {'.mp4', '.mkv', '.webm', '.avi', '.mp3', '.m4a', '.wav', '.flac', '.ogg'}

# Valid Whisper model names
VALID_MODELS = {'tiny', 'base', 'small', 'medium', 'large', 'large-v2', 'large-v3'}


def sanitize_filename(name: str, max_length: int = 200) -> str:
    """Sanitize filename to prevent path traversal and filesystem issues."""
    # Remove/replace invalid characters
    for ch in r'<>:"/\|?*':
        name = name.replace(ch, "")
    # Remove path separators to prevent path traversal
    name = name.replace('/', '').replace('\\', '')
    # Remove leading/trailing dots and spaces
    name = name.strip('. ')
    # Limit filename length
    if len(name) > max_length:
        name = name[:max_length]
    return name or "transcript"


def get_video_title(url: str) -> str:
    """Get the video title from YouTube for use in output filenames."""
    cmd = ["yt-dlp", "--print", "title", "--no-playlist", url]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode == 0 and result.stdout.strip():
        title = result.stdout.strip()
        return sanitize_filename(title)
    return "transcript"


def get_title_from_filename(filepath: str) -> str:
    """Extract clean title from local file path."""
    basename = os.path.basename(filepath)
    title = os.path.splitext(basename)[0]
    return sanitize_filename(title)


def is_video_file(filepath: str) -> bool:
    """Check if file is a supported video/audio file."""
    ext = os.path.splitext(filepath)[1].lower()
    return ext in SUPPORTED_EXTENSIONS


def is_youtube_url(url: str) -> bool:
    """Check if string is a valid YouTube URL."""
    return url.startswith(('http://', 'https://')) and \
           ('youtube.com' in url or 'youtu.be' in url)


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


def transcribe_audio(audio_path: str, model, language: str | None, output_dir: str, title: str) -> bool:
    """Transcribe audio file using Whisper and save the result.

    Skips transcription if output file already exists.
    Returns True if successful, False otherwise.
    """
    txt_path = os.path.join(output_dir, f"{title}.txt")

    if os.path.exists(txt_path):
        print(f"  Transcript already exists, skipping.")
        return True

    # Validate audio file exists
    if not os.path.exists(audio_path):
        print(f"  Error: Audio file not found: {audio_path}", file=sys.stderr)
        return False

    try:
        print(f"  Transcribing...")
        options = {}
        if language:
            options["language"] = language
        result = model.transcribe(audio_path, **options)

        with open(txt_path, "w", encoding="utf-8") as f:
            f.write(result["text"])
        print(f"  Saved: {txt_path}")
        return True
    except Exception as e:
        print(f"  Error during transcription: {e}", file=sys.stderr)
        return False


def process_video(url: str, model, language: str | None, output_dir: str) -> bool:
    """Process a single video: download audio and transcribe.
    
    Returns True if successful, False otherwise.
    """
    if not is_youtube_url(url):
        print(f"  Error: Invalid YouTube URL: {url}", file=sys.stderr)
        return False
    
    title = get_video_title(url)
    print(f"\n[{title}]")
    print(f"  URL: {url}")

    audio_path = download_audio(url, output_dir, title)
    if not audio_path:
        print(f"  Skipping transcription due to download error.")
        return False

    return transcribe_audio(audio_path, model, language, output_dir, title)


def process_local_file(filepath: str, model, language: str | None, output_dir: str) -> bool:
    """Process a local video/audio file: transcribe directly without downloading.
    
    Returns True if successful, False otherwise.
    """
    if not os.path.exists(filepath):
        print(f"  Error: File not found: {filepath}", file=sys.stderr)
        return False

    if not is_video_file(filepath):
        print(f"  Error: Unsupported file type: {filepath}", file=sys.stderr)
        print(f"  Supported extensions: {', '.join(sorted(SUPPORTED_EXTENSIONS))}", file=sys.stderr)
        return False

    title = get_title_from_filename(filepath)
    print(f"\n[{title}]")
    print(f"  Local file: {filepath}")

    return transcribe_audio(filepath, model, language, output_dir, title)


def main():
    parser = argparse.ArgumentParser(description="Transcribe YouTube videos using Whisper.")
    parser.add_argument("input", help="YouTube URL, video file, or text file with URLs/files (one per line)")
    parser.add_argument(
        "-m", "--model",
        default=os.environ.get("WHISPER_MODEL", "tiny"),
        help="Whisper model size (tiny, base, small, medium, large). Default: tiny",
    )
    parser.add_argument(
        "-l", "--language",
        default=os.environ.get("WHISPER_LANGUAGE", "id"),
        help="Language code (e.g. en, id, ja). Default: id",
    )
    parser.add_argument(
        "-o", "--output",
        default="/data",
        help="Output directory. Default: /data",
    )
    args = parser.parse_args()

    # Validate model name
    if args.model not in VALID_MODELS:
        print(f"Error: Invalid model '{args.model}'", file=sys.stderr)
        print(f"Valid models: {', '.join(sorted(VALID_MODELS))}", file=sys.stderr)
        sys.exit(1)

    os.makedirs(args.output, exist_ok=True)

    # Collect items to process (URLs or local files)
    items = []

    # Check if input is a file in output directory
    input_path = os.path.join(args.output, args.input)
    
    if os.path.isfile(args.input):
        # Input is a direct file path
        if args.input.endswith('.txt'):
            # Text file containing list of URLs or files
            try:
                with open(args.input, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith("#"):
                            items.append(line)
            except UnicodeDecodeError:
                print(f"Error: File {args.input} is not UTF-8 encoded", file=sys.stderr)
                sys.exit(1)
            print(f"Found {len(items)} item(s) in {args.input}")
        else:
            # Single local video/audio file
            items.append(args.input)
    elif os.path.isfile(input_path):
        # File exists in output directory
        if input_path.endswith('.txt'):
            # Text file containing list of URLs or files
            try:
                with open(input_path, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith("#"):
                            items.append(line)
            except UnicodeDecodeError:
                print(f"Error: File {args.input} is not UTF-8 encoded", file=sys.stderr)
                sys.exit(1)
            print(f"Found {len(items)} item(s) in {args.input}")
        else:
            # Single local video/audio file
            items.append(input_path)
    elif args.input.startswith(("http://", "https://")):
        # Single URL
        items.append(args.input)
    else:
        print(f"Error: Input is not a valid URL or file: {args.input}", file=sys.stderr)
        sys.exit(1)
    
    # Validate batch is not empty
    if not items:
        print(f"Error: No valid items found in {args.input}", file=sys.stderr)
        sys.exit(1)

    # Load Whisper model once for all items
    print(f"Loading Whisper model: {args.model}")
    try:
        model = whisper.load_model(args.model)
    except Exception as e:
        print(f"Error loading model: {e}", file=sys.stderr)
        sys.exit(1)

    # Process each item
    total = len(items)
    successes = 0
    errors = []
    
    for idx, item in enumerate(items, start=1):
        if total > 1:
            item_display = os.path.basename(item) if not item.startswith("http") else item[:50]
            print(f"\n[Processing {idx}/{total}] {item_display}")
        
        success = False
        if item.startswith(("http://", "https://")):
            # URL
            success = process_video(item, model, args.language, args.output)
        else:
            # Local file - check both absolute and relative to output dir
            if os.path.isfile(item):
                filepath = item
            else:
                filepath = os.path.join(args.output, item)
            
            if os.path.isfile(filepath):
                success = process_local_file(filepath, model, args.language, args.output)
            else:
                print(f"  Error: File not found: {item}", file=sys.stderr)
                errors.append((item, "File not found"))
        
        if success:
            successes += 1
        elif not any(err[0] == item for err in errors):
            errors.append((item, "Processing failed"))

    # Summary
    print(f"\nCompleted: {successes}/{total} successful")
    if errors:
        print(f"Failed: {len(errors)} items")
        for item, error in errors:
            print(f"  - {os.path.basename(item) if not item.startswith('http') else item[:50]}: {error}")


if __name__ == "__main__":
    main()
