# whisper-yt

Docker image untuk membuat transkrip dari video YouTube menggunakan [yt-dlp](https://github.com/yt-dlp/yt-dlp) dan [OpenAI Whisper](https://github.com/openai/whisper).

## Setup

```bash
cp .env.example .env
docker compose build
```

## Cara Pakai

Satu video:

```bash
docker compose run --rm app "https://www.youtube.com/watch?v=VIDEO_ID"
```

Banyak video (buat file `videos.txt` berisi URL, satu per baris):

```bash
docker compose run --rm app videos.txt
```

Hasil tersimpan di folder tempat perintah dijalankan:

```
./Judul Video.mp3
./Judul Video.txt
./Judul Video.srt
```

Audio dan transkrip yang sudah ada tidak akan diproses ulang.

## Konfigurasi (.env)

```env
WHISPER_MODEL=small    # tiny, base, small, medium, large
WHISPER_LANGUAGE=id    # kosongkan untuk auto-detect
```
