# whisper-yt

Docker image untuk membuat transkrip teks dari video YouTube menggunakan *yt-dlp* dan *OpenAI Whisper*.

## Sebelum Menggunakan

- Proses build image memakan waktu lama saat menginstall dependencies
- **Sebelum melakukan build**, pastikan tersedia cukup waktu atau jalankan di background
- Proses transkrip memakan waktu lama—tergantung ukuran video dan performa CPU
- Proses transkrip menggunakan resource sistem yang cukup banyak
- **Sebelum menjalankan transkrip**, sesuaikan limit CPU dan memory di `.env`, kemudian pastikan tersedia cukup waktu atau jalankan di background
- Hasil transkrip biasanya masih kasar dan perlu dibersihkan menggunakan AI lain (ChatGPT, Gemini, dll)

---

## Konfigurasi (.env)

```env
# Model Whisper: tiny, base, small, medium, large
WHISPER_MODEL=small
WHISPER_LANGUAGE=id                  # Kosongkan untuk auto-detect

# Kontrol download dan transkripsi
ENABLE_DOWNLOAD=true                 # true: download video, false: skip
ENABLE_TRANSCRIPTION=false           # true: lakukan transkripsi, false: skip
FORCE_DOWNLOAD_MODEL=false           # true: download ulang model

# Docker Compose resource limits
DOCKER_CPU_LIMIT=0.75                # CPU limit (0.5, 1, 2, dst)
DOCKER_MEMORY_LIMIT=6g               # Memory limit (512m, 1g, 2g, dst)
DOCKER_MEMORY_RESERVATION=2g         # Memory minimum yang digaransi
```

**Penjelasan:**

- `ENABLE_DOWNLOAD`: Download video dari YouTube
- `ENABLE_TRANSCRIPTION`: Lakukan transkripsi (download model Whisper jika true)
- `FORCE_DOWNLOAD_MODEL`: Download ulang model meskipun sudah ada di cache
- `DOCKER_CPU_LIMIT`: Batas penggunaan CPU untuk container
- `DOCKER_MEMORY_LIMIT`: Batas maksimal memory untuk container
- `DOCKER_MEMORY_RESERVATION`: Memory minimum yang digaransi untuk container

---

## Setup

**Linux:**

```bash
# Salin file konfigurasi dari contoh
cp .env.example .env

# Sesuaikan konfigurasi di .env
nano .env

# Setup dengan Python (Python harus sudah terinstall)
python -m venv venv
source ./venv/bin/activate
pip install -r requirements.txt

# Setup dengan Docker image (Docker harus sudah terinstall)
docker build -t whisper-yt .

# Setup dengan Docker Compose (Docker harus sudah terinstall)
docker compose build
```

**Windows:**

```ps
# Salin file konfigurasi dari contoh
copy .env.example .env

# Sesuaikan konfigurasi di .env
notepad .env

# Setup dengan Python (Python harus sudah terinstall)
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt

# Setup dengan Docker image (Docker harus sudah terinstall)
docker build -t whisper-yt .

# Setup dengan Docker Compose (Docker harus sudah terinstall)
docker compose build
```

---

## Cara Pakai

- Jika Python sudah terinstall: gunakan Python
- Jika Docker sudah terinstall: gunakan Docker image atau Docker Compose
- Docker image: memungkinkan resource limit custom
- Docker Compose: menggunakan resource limit dari `.env`

### Satu Video dari YouTube

**Python:**
```bash
python ./app/transcribe.py https://www.youtube.com/watch?v=VIDEO_ID
```

**Docker image:**
```bash
# perhatikan bahwa environment dapat disesuaikan dengan menyediakan .env, bila tidak disediakan akan menggunakan default
# perhatikan bahwa current folder di mount ke /data. workdir image adalah /data
docker run --rm --env-file .env -v .:/data whisper-yt https://www.youtube.com/watch?v=VIDEO_ID
```

**Docker Compose:**
```bash
# spec compose sudah menyertakan mount current folder ke /data. workdir image adalah /data
docker compose run --rm app https://www.youtube.com/watch?v=VIDEO_ID
```

### Banyak File Video/Audio

Buat file `videos.txt` berisi URL atau file lokal (satu per baris):

```txt
https://www.youtube.com/watch?v=VIDEO_ID1
video1.mp4
https://www.youtube.com/watch?v=VIDEO_ID2
```

**Python:**
```bash
python ./app/transcribe.py videos.txt
```

**Docker image:**
```bash
# perhatikan bahwa environment dapat disesuaikan dengan menyediakan .env, bila tidak disediakan akan menggunakan default
# perhatikan bahwa current folder di mount ke /data. workdir image adalah /data
docker run --rm --env-file .env -v .:/data whisper-yt videos.txt
```

**Docker Compose:**
```bash
# spec compose sudah menyertakan mount current folder ke /data. workdir image adalah /data
docker compose run --rm app videos.txt
```

**Format yang didukung:** `.mp4`, `.mkv`, `.webm`, `.avi`, `.mp3`, `.m4a`, `.wav`, `.flac`, `.ogg`

**Output:**

Hasil disimpan di folder saat ini sebagai `Judul Video.mp3` dan `Judul Video.txt`.
Audio dan transkrip yang sudah ada tidak akan diproses ulang.

---

## transcribe.py

Cara pakai:
```bash
python ./app/transcribe.py <options> <input>
```

### `input`

| Argumen | Deskripsi |
|---------|-----------|
| `input` | YouTube URL, file video/audio lokal, atau file `.txt` berisi daftar URL/file (satu per baris). Contoh: `https://www.youtube.com/watch?v=VIDEO_ID`, `video.mp4`, atau `videos.txt` |

### `options`

| Argumen | Alias | Default | Deskripsi |
|---------|-------|---------|-----------|
| `--model` | `-m` | `tiny` (atau `WHISPER_MODEL` dari .env) | Model Whisper: `tiny`, `base`, `small`, `medium`, `large`, `large-v2`, `large-v3` |
| `--language` | `-l` | `id` (atau `WHISPER_LANGUAGE` dari .env) | Kode bahasa audio (contoh: `en` untuk Inggris, `id` untuk Indonesia, `ja` untuk Jepang). Kosongkan untuk auto-detect |
| `--output` | `-o` | `.` (folder saat ini) | Folder untuk menyimpan hasil audio dan transkrip |
| `--cache` | `-c` | `<output>/model-cache` | Folder untuk menyimpan model Whisper yang ter-cache. Default: subfolder `model-cache` di dalam folder output |
