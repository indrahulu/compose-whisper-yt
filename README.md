# whisper-yt

Docker image untuk membuat teks transkrip dari video YouTube menggunakan *yt-dlp* dan *OpenAI Whisper*. Image akan mendownload video dari youtube menjadi file video, mengkonversi file video menjadi file audio, lalu membuat teks transkrip dari file audio.

## Catatan penting

- Proses build image ini akan memakan waktu yang cukup lama ketika menginstall requirements.
- Proses yang dikerjakan oleh image ini dapat memakan waktu yang lama (tergantung kekuatan komputer yang menjalankannya), dan akan menggunakan resource cpu dan memory yang besar (walau bisa dikendalikan dengan resource limiting di compose, sesuaikan dulu sebelum mulai).
- Sebelum melakukan build atau menggunakan image untuk transkrip, pastikan punya banyak waktu untuk menunggu sampai selesai, atau gunakan perintah untuk menjalankannya di background.
- Hasil transkrip biasanya sangat mentah dan masih kacau. Gunakan AI lain (ChatGPT, Gemini, dll) untuk merapikan hasil transkrip.

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
# Letakkan file video di folder tempat image dijalankan
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
WHISPER_MODEL=small           # tiny, base, small, medium, large
WHISPER_LANGUAGE=id           # kosongkan untuk auto-detect

# Kontrol download dan transkripsi
ENABLE_DOWNLOAD=true          # true: download video, false: skip download
ENABLE_TRANSCRIPTION=false    # true: lakukan transkripsi, false: skip transkripsi

# Force download model (untuk troubleshooting)
FORCE_DOWNLOAD_MODEL=false    # true: download ulang model meskipun sudah ada
```

### Penjelasan Konfigurasi:

- **ENABLE_DOWNLOAD** (default: `true`):
  - `true`: Aplikasi akan mendownload video dari YouTube
  - `false`: Aplikasi tidak mendownload video (dan tidak melakukan transcribe)

- **ENABLE_TRANSCRIPTION** (default: `false`):
  - `true`: Aplikasi akan mendownload model Whisper dan melakukan transkripsi
  - `false`: Aplikasi tidak mendownload model dan tidak melakukan transkripsi

- **FORCE_DOWNLOAD_MODEL** (default: `false`):
  - `true`: Paksa download ulang model meskipun sudah ada di cache
  - `false`: Gunakan model yang sudah ada di cache (lebih cepat)

### Catatan Model Whisper:

Model Whisper disimpan secara persistent di folder `./model-cache`. Whisper secara otomatis mendeteksi jika model sudah ada di cache dan akan langsung menggunakannya tanpa download ulang. Untuk menghapus cache model:

```bash
rm -rf ./model-cache
```

### Contoh Skenario:

1. **Hanya download tanpa transkripsi**:
   ```env
   ENABLE_DOWNLOAD=true
   ENABLE_TRANSCRIPTION=false
   ```

2. **Download dan transkripsi**:
   ```env
   ENABLE_DOWNLOAD=true
   ENABLE_TRANSCRIPTION=true
   ```

3. **Tidak melakukan apapun** (keduanya disabled):
   ```env
   ENABLE_DOWNLOAD=false
   ENABLE_TRANSCRIPTION=false
   ```
