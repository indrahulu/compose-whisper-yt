#!/usr/bin/env python3
"""Download audio from a YouTube URL and transcribe it using OpenAI Whisper."""

import argparse
import os
import subprocess
import sys
import warnings
import shutil
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Suppress FP16 warning on CPU
warnings.filterwarnings("ignore", message="FP16 is not supported on CPU; using FP32 instead")

try:
    import whisper
except ImportError:
    print("Error: openai-whisper not installed", file=sys.stderr)
    sys.exit(1)

# Supported video and audio file extensions
SUPPORTED_EXTENSIONS = {'.mp4', '.mkv', '.webm', '.avi', '.mp3', '.m4a', '.wav', '.flac', '.ogg'}

# Valid Whisper model names
VALID_MODELS = {'tiny', 'base', 'small', 'medium', 'large', 'large-v2', 'large-v3'}

# Chunking defaults (in seconds)
DEFAULT_CHUNK_DURATION = 3600   # 60 minutes
DEFAULT_CHUNK_THRESHOLD = 7200  # 120 minutes


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
    print(f"  Downloading audio...", flush=True)
    result = subprocess.run(cmd)
    if result.returncode != 0:
        print("  yt-dlp failed. See error above.", file=sys.stderr)
        return ""

    if not os.path.exists(audio_path):
        print(f"  Expected file not found: {audio_path}", file=sys.stderr)
        return ""

    print(f"  Audio downloaded.")
    return audio_path


def get_audio_duration(audio_path: str) -> float:
    """Return audio duration in seconds using ffprobe. Returns 0 on failure."""
    cmd = [
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        audio_path,
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        return float(result.stdout.strip())
    except (ValueError, Exception):
        return 0.0


def split_audio(audio_path: str, chunk_duration: int, tmp_dir: str) -> list[str]:
    """Split audio into chunks of chunk_duration seconds using ffmpeg.

    Returns sorted list of chunk file paths.
    """
    os.makedirs(tmp_dir, exist_ok=True)
    output_pattern = os.path.join(tmp_dir, "chunk_%03d.mp3")
    cmd = [
        "ffmpeg", "-y", "-i", audio_path,
        "-f", "segment",
        "-segment_time", str(chunk_duration),
        "-c", "copy",
        output_pattern,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"  Error splitting audio: {result.stderr}", file=sys.stderr)
        return []
    chunks = sorted(
        str(p) for p in Path(tmp_dir).glob("chunk_*.mp3")
    )
    return chunks


def transcribe_audio(audio_path: str, model, language: str | None, output_dir: str, title: str, chunk_duration: int = DEFAULT_CHUNK_DURATION, chunk_threshold: int = DEFAULT_CHUNK_THRESHOLD) -> bool:
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

    options = {
        "verbose": True,
    }
    if language:
        options["language"] = language

    try:
        print(f"  Transcribing...", flush=True)
        duration = get_audio_duration(audio_path)

        if duration > chunk_threshold:
            # --- Chunked transcription ---
            minutes = int(duration // 60)
            print(f"  Audio duration: {minutes} min — splitting into {chunk_duration // 60}-minute chunks...", flush=True)
            tmp_dir = os.path.join(output_dir, f".chunks_{title}")
            chunks = split_audio(audio_path, chunk_duration, tmp_dir)
            if not chunks:
                print(f"  Error: Failed to split audio.", file=sys.stderr)
                return False

            print(f"  Total chunks: {len(chunks)}", flush=True)
            texts = []
            try:
                for i, chunk_path in enumerate(chunks, start=1):
                    print(f"  Chunk {i}/{len(chunks)}: {os.path.basename(chunk_path)}", flush=True)
                    result = model.transcribe(chunk_path, **options)
                    texts.append(result["text"].strip())
            finally:
                # Always clean up temp chunks
                shutil.rmtree(tmp_dir, ignore_errors=True)

            full_text = " ".join(texts)
        else:
            # --- Normal transcription ---
            result = model.transcribe(audio_path, **options)
            full_text = result["text"]

        with open(txt_path, "w", encoding="utf-8") as f:
            f.write(full_text)
        print(f"  Saved: {txt_path}")
        return True
    except Exception as e:
        print(f"  Error during transcription: {e}", file=sys.stderr)
        return False


def cleanup_video_files(output_dir: str, title: str) -> None:
    """Delete any video files matching the title (keeping only audio)."""
    video_extensions = {'.mp4', '.mkv', '.webm', '.avi', '.mov', '.flv', '.wmv', '.m4v'}
    for ext in video_extensions:
        video_path = os.path.join(output_dir, f"{title}{ext}")
        if os.path.exists(video_path):
            try:
                os.remove(video_path)
                print(f"  Deleted video file: {video_path}")
            except OSError as e:
                print(f"  Warning: Could not delete {video_path}: {e}", file=sys.stderr)


def process_video(url: str, model, language: str | None, output_dir: str, enable_download: bool = True, enable_transcription: bool = True, chunk_duration: int = DEFAULT_CHUNK_DURATION, chunk_threshold: int = DEFAULT_CHUNK_THRESHOLD) -> bool:
    """Process a single video: download audio and transcribe.
    
    Returns True if successful, False otherwise.
    """
    if not is_youtube_url(url):
        print(f"  Error: Invalid YouTube URL: {url}", file=sys.stderr)
        return False
    
    title = get_video_title(url)
    print(f"\n[{title}]")
    print(f"  URL: {url}")

    # Check if download is enabled
    if not enable_download:
        print(f"  Download disabled (ENABLE_DOWNLOAD=false), skipping.")
        return False

    audio_path = download_audio(url, output_dir, title)
    if not audio_path:
        print(f"  Skipping transcription due to download error.")
        return False

    # Delete any video files after audio extraction
    cleanup_video_files(output_dir, title)

    # Check if transcription is enabled
    if not enable_transcription:
        print(f"  Transcription disabled (ENABLE_TRANSCRIPTION=false), skipping.")
        return True

    return transcribe_audio(audio_path, model, language, output_dir, title, chunk_duration, chunk_threshold)


def process_local_file(filepath: str, model, language: str | None, output_dir: str, enable_transcription: bool = True, chunk_duration: int = DEFAULT_CHUNK_DURATION, chunk_threshold: int = DEFAULT_CHUNK_THRESHOLD) -> bool:
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

    # Check if transcription is enabled
    if not enable_transcription:
        print(f"  Transcription disabled (ENABLE_TRANSCRIPTION=false), skipping.")
        return False

    return transcribe_audio(filepath, model, language, output_dir, title, chunk_duration, chunk_threshold)


def str_to_bool(value: str) -> bool:
    """Convert string to boolean."""
    return value.lower() in ('true', '1', 'yes', 'on')


def main():
    parser = argparse.ArgumentParser(description="Transcribe YouTube videos using Whisper.")
    parser.add_argument("input", nargs='?', default=None, help="YouTube URL, video file, or text file with URLs/files (one per line)")
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
        default=".",
        help="Output directory. Default: current directory",
    )
    parser.add_argument(
        "-c", "--cache",
        default=None,
        help="Model cache directory. Default: <output>/model-cache",
    )
    args = parser.parse_args()

    # Show help if no input provided
    if args.input is None:
        parser.print_help()
        sys.exit(0)
    
    # Create output directory
    try:
        os.makedirs(args.output, exist_ok=True)
    except OSError as e:
        print(f"Error: Failed to create output directory '{args.output}': {e}", file=sys.stderr)
        sys.exit(1)
    
    # Set cache directory with priority: argument > default (output/model-cache)
    if args.cache is not None:
        model_cache_dir = args.cache
    else:
        model_cache_dir = os.path.join(args.output, "model-cache")
    
    # Create cache directory
    try:
        os.makedirs(model_cache_dir, exist_ok=True)
    except OSError as e:
        print(f"Error: Failed to create cache directory '{model_cache_dir}': {e}", file=sys.stderr)
        sys.exit(1)

    # Read configuration from environment variables
    enable_download = str_to_bool(os.environ.get("ENABLE_DOWNLOAD", "true"))
    enable_transcription = str_to_bool(os.environ.get("ENABLE_TRANSCRIPTION", "false"))
    force_download_model = str_to_bool(os.environ.get("FORCE_DOWNLOAD_MODEL", "false"))
    chunk_duration = int(os.environ.get("CHUNK_DURATION", str(DEFAULT_CHUNK_DURATION)))
    chunk_threshold = int(os.environ.get("CHUNK_THRESHOLD", str(DEFAULT_CHUNK_THRESHOLD)))

    # Print all configuration
    print("=== Configuration ===", flush=True)
    print(f"  Model: {args.model}", flush=True)
    print(f"  Language: {args.language}", flush=True)
    print(f"  Output directory: {args.output}", flush=True)
    print(f"  Cache directory: {model_cache_dir}", flush=True)
    print(f"  ENABLE_DOWNLOAD: {enable_download}", flush=True)
    print(f"  ENABLE_TRANSCRIPTION: {enable_transcription}", flush=True)
    print(f"  FORCE_DOWNLOAD_MODEL: {force_download_model}", flush=True)
    print(f"  CHUNK_DURATION: {chunk_duration // 60} min", flush=True)
    print(f"  CHUNK_THRESHOLD: {chunk_threshold // 60} min", flush=True)
    print("=" * 22, flush=True)
    
    if not enable_download and not enable_transcription:
        print("\nWarning: Both download and transcription are disabled. No action will be performed.")

    # Validate model name
    if args.model not in VALID_MODELS:
        print(f"Error: Invalid model '{args.model}'", file=sys.stderr)
        print(f"Valid models: {', '.join(sorted(VALID_MODELS))}", file=sys.stderr)
        sys.exit(1)

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

    # Load Whisper model only if transcription is enabled
    model = None
    if enable_transcription:
        cache_dir = Path(model_cache_dir)
        
        # Set environment variable for torch to use our cache directory
        os.environ["TORCH_HOME"] = model_cache_dir
        
        # Force re-download model if requested
        if force_download_model:
            model_file = cache_dir / f"{args.model}.pt"
            if model_file.exists():
                print(f"Force downloading model (removing cached: {model_file})", flush=True)
                model_file.unlink()
        try:
            print(f"Loading Whisper model: {args.model}", flush=True)
            model = whisper.load_model(args.model, download_root=model_cache_dir)
        except Exception as e:
            print(f"Error loading model: {e}", file=sys.stderr)
            sys.exit(1)
    else:
        print(f"Skipping model loading (ENABLE_TRANSCRIPTION=false)")

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
            success = process_video(item, model, args.language, args.output, enable_download, enable_transcription, chunk_duration, chunk_threshold)
        else:
            # Local file - check both absolute and relative to output dir
            if os.path.isfile(item):
                filepath = item
            else:
                filepath = os.path.join(args.output, item)
            
            if os.path.isfile(filepath):
                success = process_local_file(filepath, model, args.language, args.output, enable_transcription, chunk_duration, chunk_threshold)
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
