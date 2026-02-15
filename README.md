# whisper-yt

Docker image untuk membuat transkrip dari video YouTube menggunakan [yt-dlp](https://github.com/yt-dlp/yt-dlp) dan [OpenAI Whisper](https://github.com/openai/whisper).

## Setup

```bash
cp .env.example .env
docker compose build
```

## Cara Pakai

### Satu video dari YouTube:

```bash
docker compose run --rm app "https://www.youtube.com/watch?v=VIDEO_ID"
```

### Banyak video dari YouTube (buat file `videos.txt` berisi URL, satu per baris):

```bash
docker compose run --rm app videos.txt
```

### File video lokal:

```bash
# Letakkan file video di folder saat ini
docker compose run --rm app "video.mp4"
```

### Campuran URL dan file lokal (dalam `videos.txt`):

```txt
https://www.youtube.com/watch?v=VIDEO_ID1
video1.mp4
https://www.youtube.com/watch?v=VIDEO_ID2
video2.mkv
```

```bash
docker compose run --rm app videos.txt
```

### Format file yang didukung:

`.mp4`, `.mkv`, `.webm`, `.avi`, `.mp3`, `.m4a`, `.wav`, `.flac`, `.ogg`

### Output:

Hasil tersimpan di folder tempat perintah dijalankan:

```
./Judul Video.mp3
./Judul Video.txt
```

Audio dan transkrip yang sudah ada tidak akan diproses ulang.

## Konfigurasi (.env)

```env
WHISPER_MODEL=small    # tiny, base, small, medium, large
WHISPER_LANGUAGE=id    # kosongkan untuk auto-detect
```
