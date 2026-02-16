# whisper-yt

Docker image untuk membuat teks transkrip dari video YouTube menggunakan *yt-dlp* dan *OpenAI Whisper*.

## Catatan penting

- Proses build image ini memakan waktu yang cukup lama ketika menginstall requirements.
- **Sebelum melakukan build**, pastikan punya banyak waktu untuk menunggu sampai selesai, atau gunakan perintah untuk menjalankannya di background.
- Proses pengerjaan transkrip oleh image ini memakan waktu yang cukup lama. Tergantung pada ukuran video dan kekuatan cpu yang menjalankannya.
- Proses pengerjaan transkrip oleh image ini juga menggunakan resource yang banyak.
- **Sebelum menjalankan proses transkrip**, sesuaikan dulu limit cpu dan memory di .env. Pastikan punya banyak waktu untuk menunggu sampai selesai, atau gunakan perintah untuk menjalankannya di background.
- Hasil transkrip biasanya sangat mentah dan masih kacau. Gunakan AI lain (ChatGPT, Gemini, dll) untuk merapikan hasil transkrip.

## Setup

```bash
cp .env.example .env
# Sesuaikan konfigurasi di .env
docker compose build
```

## Konfigurasi (.env)

```env
# Model Whisper: tiny, base, small, medium, large
WHISPER_MODEL=small
WHISPER_LANGUAGE=id           # kosongkan untuk auto-detect

# Kontrol download dan transkripsi
ENABLE_DOWNLOAD=true          # true: download video, false: skip
ENABLE_TRANSCRIPTION=false    # true: lakukan transkripsi, false: skip
FORCE_DOWNLOAD_MODEL=false    # true: download ulang model

# Docker resource limits
DOCKER_CPU_LIMIT=0.75         # CPU limit (0.5, 1, 2, dst)
DOCKER_MEMORY_LIMIT=6g        # Memory limit (512m, 1g, 2g, dst)
DOCKER_MEMORY_RESERVATION=2g  # Memory minimum guaranteed
```

**Penjelasan:**
- `ENABLE_DOWNLOAD`: Kontrol download video dari YouTube
- `ENABLE_TRANSCRIPTION`: Kontrol proses transkripsi (akan download model Whisper jika true)
- `FORCE_DOWNLOAD_MODEL`: Paksa download ulang model meskipun sudah ada di cache
- `DOCKER_CPU_LIMIT`: Limit penggunaan CPU untuk container
- `DOCKER_MEMORY_LIMIT`: Limit maksimal memory untuk container
- `DOCKER_MEMORY_RESERVATION`: Memory minimum yang dijamin untuk container

## Cara Pakai

### Satu video dari YouTube:

```bash
docker compose run --rm app "https://www.youtube.com/watch?v=VIDEO_ID"
```

### File video lokal atau banyak video (gunakan file `videos.txt`):

Buat file `videos.txt` berisi URL/file lokal, satu per baris:
```txt
https://www.youtube.com/watch?v=VIDEO_ID1
video1.mp4
https://www.youtube.com/watch?v=VIDEO_ID2
```

Jalankan:
```bash
docker compose run --rm app videos.txt
```

**Format yang didukung:** `.mp4`, `.mkv`, `.webm`, `.avi`, `.mp3`, `.m4a`, `.wav`, `.flac`, `.ogg`

**Output:** Hasil tersimpan di folder saat ini dengan nama `Judul Video.mp3` dan `Judul Video.txt`. Audio dan transkrip yang sudah ada tidak akan diproses ulang.

## Catatan Model Whisper

Model Whisper disimpan di folder `./model-cache`. Model yang sudah ada akan digunakan tanpa download ulang.
