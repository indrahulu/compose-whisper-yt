# whisper-yt

Docker image untuk membuat transkrip dari video YouTube. Menggunakan [yt-dlp](https://github.com/yt-dlp/yt-dlp) untuk download audio dan [OpenAI Whisper](https://github.com/openai/whisper) untuk transkripsi.

## Build

```bash
docker compose build
```

## Cara Pakai

```bash
docker compose run --rm whisper-yt "https://www.youtube.com/watch?v=VIDEO_ID"
```

Hasil transkrip tersimpan di folder `./output/`.

### Pilih Model Whisper

Semakin besar model, semakin akurat tapi lebih lambat.

| Model | Parameter | Catatan |
|-------|-----------|---------|
| `tiny` | 39M | Paling cepat, akurasi rendah |
| `base` | 74M | Default |
| `small` | 244M | Keseimbangan kecepatan & akurasi |
| `medium` | 769M | Akurasi bagus |
| `large` | 1550M | Paling akurat, paling lambat |

```bash
docker compose run --rm -e WHISPER_MODEL=small whisper-yt "URL"
```

### Tentukan Bahasa

Secara default Whisper mendeteksi bahasa otomatis. Untuk menentukan secara manual:

```bash
docker compose run --rm -e WHISPER_LANGUAGE=id whisper-yt "URL"
```

Contoh kode bahasa: `id` (Indonesia), `en` (English), `ja` (Japanese).

### Tanpa Docker Compose

```bash
docker build -t whisper-yt .
docker run --rm -v ./output:/output whisper-yt "https://www.youtube.com/watch?v=VIDEO_ID"
```

## Output

Setiap video menghasilkan 2 file di folder `./output/`:

- **`.txt`** — teks transkrip lengkap
- **`.srt`** — subtitle dengan timestamp (bisa dipakai di video player)
