# Converter Toolkit Pro (Flask, Modular)

REST API lokal, modular per kategori — untuk kebutuhan engineer, programmer,
data analyst, database expert, dan network integration. 81 endpoint, jalan
100% di komputer/server kamu sendiri (tidak ada data yang keluar ke pihak ketiga).

## Struktur Proyek
```
toolkit_pro/
├── START_TOOLKIT.bat              # Launcher satu-klik (Windows)
├── START_TOOLKIT.sh               # Launcher satu-klik (Linux/Mac)
├── app.py                        # Entry point, registrasi semua blueprint + homepage
├── utils.py                      # Helper bersama (lazy import, simpan upload, response)
├── requirements.txt
├── routes/
│   ├── convert_tools.py          # Konversi dokumen lintas format (PDF/DOCX/TXT/MD/YAML/CSV)
│   ├── pdf_tools.py               # Operasi PDF: merge, split, rotate, watermark, encrypt, OCR, dll
│   ├── image_tools.py             # Pemrosesan gambar: convert, resize, crop, exif, base64, dll
│   ├── text_tools.py              # Tools dev: JSON, base64, hash, regex, JWT decode, UUID, dll
│   ├── calculator_tools.py        # Kalkulator: subnet/CIDR, basis angka, satuan, tanggal, cicilan
│   ├── qr_tools.py                # Generate/decode QR code & barcode
│   ├── security_tools.py          # Password generator, hash, enkripsi AES, JWT, checksum file
│   ├── spreadsheet_tools.py       # CSV/Excel/JSON: convert, clean, merge, SQL query, SQL insert
│   └── compress_tools.py          # Kompresi: zip/tar.gz/gzip/bzip2/lzma, minify JSON, CSV<->Parquet
└── templates/index.html          # Homepage: daftar semua endpoint otomatis
```

## Instalasi

```bash
cd toolkit_pro
pip install -r requirements.txt
```

Program sistem tambahan (bukan via pip):
```bash
# Ubuntu / Debian
sudo apt install poppler-utils tesseract-ocr tesseract-ocr-ind libzbar0 qpdf

# macOS (Homebrew)
brew install poppler tesseract tesseract-lang zbar qpdf
```
> Fitur QR/barcode (`qr_tools.py`) butuh `qrcode`, `pyzbar`, `python-barcode` — opsional,
> hanya perlu di-install kalau fitur itu dipakai. Semua fitur lain sudah teruji jalan
> tanpa ketiga paket ini.

## Menjalankan (Satu Klik — Direkomendasikan)

Sudah disediakan launcher otomatis yang akan: membuat virtual environment
(kalau belum ada), install semua dependency (hanya sekali di percobaan
pertama), menjalankan server, dan membuka browser otomatis ke
`http://127.0.0.1:5000`.

**Homepage sekarang berupa UI interaktif** — dikelompokkan per peran:
🔧 Engineer & Programmer, 📊 Data Analyst, 🗄️ Database Expert,
🌐 Network Integration, 📄 Dokumen & File. Tinggal pilih tab sesuai
kebutuhan, isi form (upload file / ketik teks), klik **Jalankan**, hasil
langsung tampil atau muncul tombol download — tidak perlu curl/Postman.
Tab **"Semua Endpoint (Lengkap)"** tetap ada untuk yang mau panggil API
langsung dari skrip/aplikasi sendiri.

**Windows:**
Double-click `START_TOOLKIT.bat` (atau klik kanan → Run).
- Percobaan pertama akan lebih lama karena proses install dependency.
- Percobaan berikutnya jauh lebih cepat (dependency dilewati karena sudah ada penanda `venv\.installed`).
- Supaya bisa diklik dari Desktop: klik kanan `START_TOOLKIT.bat` → **Send to > Desktop (create shortcut)**,
  lalu shortcut itu bisa di-rename dan diganti ikonnya sesuka hati.
- Kalau muncul error "Application Control policy has blocked this file" (kebijakan IT kantor),
  itu bukan bug dari toolkit ini — hubungi admin IT untuk meng-allowlist `python.exe`/`pip.exe`,
  atau jalankan di WSL/laptop pribadi.

**Linux / Mac:**
```bash
chmod +x START_TOOLKIT.sh   # cukup sekali
./START_TOOLKIT.sh
```
Atau double-click dari file manager kalau sudah di-set executable & default app-nya terminal.

Untuk menghentikan server: tutup jendela terminal/cmd tersebut, atau tekan `CTRL+C`.

## Menjalankan Manual (kalau tidak pakai launcher)
```bash
python3 app.py
```
Buka `http://127.0.0.1:5000` — akan tampil daftar semua endpoint per kategori.

## Contoh Pemakaian (curl)

### PDF Tools
```bash
# Merge PDF
curl -F "files=@a.pdf" -F "files=@b.pdf" http://127.0.0.1:5000/api/pdf/merge -o merged.pdf

# Split per halaman
curl -F "file=@dokumen.pdf" http://127.0.0.1:5000/api/pdf/split -o split.zip

# Rotate
curl -F "file=@scan.pdf" -F "degrees=90" http://127.0.0.1:5000/api/pdf/rotate -o rotated.pdf

# Watermark
curl -F "file=@kontrak.pdf" -F "text=DRAFT" http://127.0.0.1:5000/api/pdf/watermark -o wm.pdf

# Kunci / buka kunci
curl -F "file=@rahasia.pdf" -F "password=abc123" http://127.0.0.1:5000/api/pdf/encrypt -o locked.pdf
curl -F "file=@locked.pdf" -F "password=abc123" http://127.0.0.1:5000/api/pdf/decrypt -o unlocked.pdf

# OCR PDF hasil scan
curl -F "file=@scan.pdf" -F "lang=ind+eng" http://127.0.0.1:5000/api/pdf/ocr

# Metadata
curl -F "file=@dokumen.pdf" http://127.0.0.1:5000/api/pdf/metadata
```

### Convert Tools (lintas format)
```bash
curl -F "file=@dokumen.pdf" http://127.0.0.1:5000/api/convert/pdf-to-docx -o hasil.docx
curl -F "file=@dokumen.pdf" -F "format=png" -F "dpi=200" http://127.0.0.1:5000/api/convert/pdf-to-images -o pages.zip
curl -F "files=@foto1.jpg" -F "files=@foto2.jpg" http://127.0.0.1:5000/api/convert/images-to-pdf -o gabung.pdf

curl -X POST http://127.0.0.1:5000/api/convert/markdown-to-html \
  -H "Content-Type: application/json" -d '{"markdown_text": "# Judul\n\n- satu\n- dua"}'

curl -X POST http://127.0.0.1:5000/api/convert/yaml-to-json \
  -H "Content-Type: application/json" -d '{"yaml_text": "name: budi\nage: 30"}'
```

### Image Tools
```bash
curl -F "file=@foto.png" -F "format=jpg" http://127.0.0.1:5000/api/image/convert -o foto.jpg
curl -F "file=@foto.jpg" -F "width=800" http://127.0.0.1:5000/api/image/resize -o kecil.jpg
curl -F "file=@foto.jpg" -F "quality=60" http://127.0.0.1:5000/api/image/compress -o kompres.jpg
curl -F "file=@foto.jpg" http://127.0.0.1:5000/api/image/exif
curl -F "file=@foto.jpg" http://127.0.0.1:5000/api/image/strip-exif -o bersih.jpg
```

### Text / Dev Tools
```bash
curl -X POST http://127.0.0.1:5000/api/text/json-format -H "Content-Type: application/json" \
  -d '{"text": "{\"a\":1}"}'

curl -X POST http://127.0.0.1:5000/api/text/hash -H "Content-Type: application/json" \
  -d '{"text":"hello","algo":"sha256"}'

curl "http://127.0.0.1:5000/api/text/uuid?count=5"

curl -X POST http://127.0.0.1:5000/api/text/jwt-decode -H "Content-Type: application/json" \
  -d '{"token":"eyJhbGciOi..."}'

curl -X POST http://127.0.0.1:5000/api/text/regex-test -H "Content-Type: application/json" \
  -d '{"pattern":"\\d+","text":"abc 123 def 456"}'
```

### Calculator Tools (termasuk Network/Subnet)
```bash
# Subnet calculator - untuk network engineer
curl -X POST http://127.0.0.1:5000/api/calc/subnet -H "Content-Type: application/json" \
  -d '{"cidr":"192.168.1.0/24"}'

# Pecah network jadi subnet lebih kecil
curl -X POST http://127.0.0.1:5000/api/calc/subnet-split -H "Content-Type: application/json" \
  -d '{"cidr":"10.0.0.0/24","new_prefix":26}'

# Cek IP masuk network mana
curl -X POST http://127.0.0.1:5000/api/calc/ip-in-network -H "Content-Type: application/json" \
  -d '{"ip":"192.168.1.50","cidr":"192.168.1.0/24"}'

# Base converter
curl -X POST http://127.0.0.1:5000/api/calc/base-convert -H "Content-Type: application/json" \
  -d '{"value":"255","from_base":10,"to_base":16}'

# Unit converter
curl -X POST http://127.0.0.1:5000/api/calc/unit-convert -H "Content-Type: application/json" \
  -d '{"value":100,"from_unit":"c","to_unit":"f","category":"temperature"}'
```

### QR & Barcode
```bash
curl -X POST http://127.0.0.1:5000/api/qr/generate -H "Content-Type: application/json" \
  -d '{"text":"https://example.com"}' -o qr.png

curl -X POST http://127.0.0.1:5000/api/qr/generate-wifi -H "Content-Type: application/json" \
  -d '{"ssid":"KantorWifi","password":"rahasia123","encryption":"WPA"}' -o wifi.png

curl -F "file=@qr.png" http://127.0.0.1:5000/api/qr/decode
```

### Security Tools
```bash
curl "http://127.0.0.1:5000/api/security/password-generate?length=20&count=3"

curl -X POST http://127.0.0.1:5000/api/security/strength-check -H "Content-Type: application/json" \
  -d '{"password":"MyP@ssw0rd123"}'

curl -X POST http://127.0.0.1:5000/api/security/encrypt -H "Content-Type: application/json" \
  -d '{"text":"data rahasia","password":"kunciku"}'

curl -X POST http://127.0.0.1:5000/api/security/jwt-encode -H "Content-Type: application/json" \
  -d '{"payload":{"user":"budi"},"secret":"rahasia","expires_in_seconds":3600}'

curl -F "file=@installer.exe" http://127.0.0.1:5000/api/security/file-checksum
```

### Spreadsheet Tools (Data Analyst & Database Expert)
```bash
curl -F "file=@data.csv" http://127.0.0.1:5000/api/sheet/csv-to-excel -o data.xlsx

# Jalankan query SQL langsung ke file CSV/Excel (read-only, via SQLite in-memory)
curl -F "file=@data.csv" -F "query=SELECT kota, COUNT(*) as jumlah FROM t GROUP BY kota" \
  -F "table_name=t" http://127.0.0.1:5000/api/sheet/sql-query

# Generate SQL INSERT statements dari CSV/Excel
curl -F "file=@data.csv" -F "table_name=pengguna" http://127.0.0.1:5000/api/sheet/to-sql-insert -o insert.sql

# Bersihkan data (hapus duplikat / kosong)
curl -F "file=@data.csv" -F "drop_duplicates=true" -F "drop_na=true" \
  http://127.0.0.1:5000/api/sheet/clean -o cleaned.xlsx

# Ringkasan statistik
curl -F "file=@data.csv" http://127.0.0.1:5000/api/sheet/summary
```

### Compress Tools (kompresi file & data)
```bash
# Kompres beberapa file jadi 1 zip
curl -F "files=@a.txt" -F "files=@b.csv" http://127.0.0.1:5000/api/compress/zip -o archive.zip

# Lihat isi zip tanpa ekstrak
curl -F "file=@archive.zip" http://127.0.0.1:5000/api/compress/zip-info

# Ekstrak zip (hasil dikembalikan sebagai zip juga)
curl -F "file=@archive.zip" http://127.0.0.1:5000/api/compress/unzip -o extracted.zip

# Arsip tar.gz
curl -F "files=@a.txt" -F "files=@b.csv" http://127.0.0.1:5000/api/compress/tar-gz -o archive.tar.gz
curl -F "file=@archive.tar.gz" http://127.0.0.1:5000/api/compress/untar -o extracted.zip

# Kompres 1 file (gzip/bzip2/lzma) - bandingkan mana yang paling kecil
curl -F "file=@data.log" -F "algo=gzip" http://127.0.0.1:5000/api/compress/file-compress -o data.log.gz
curl -F "file=@data.log.gz" -F "algo=gzip" http://127.0.0.1:5000/api/compress/file-decompress -o data.log

# Kompres teks langsung (mis. sebelum kirim lewat API/network agar payload kecil)
curl -X POST http://127.0.0.1:5000/api/compress/text-compress -H "Content-Type: application/json" \
  -d '{"text":"data yang mau dikirim lewat jaringan...", "algo":"gzip"}'

curl -X POST http://127.0.0.1:5000/api/compress/text-decompress -H "Content-Type: application/json" \
  -d '{"base64":"H4sIAAAAAAAAA...", "algo":"gzip"}'

# Minify JSON (hemat ukuran payload API)
curl -X POST http://127.0.0.1:5000/api/compress/json-minify -H "Content-Type: application/json" \
  -d '{"text": "{\n  \"a\": 1,\n  \"b\": [1,2,3]\n}"}'

# CSV -> Parquet (kompresi kolumnar, jauh lebih kecil untuk data besar) - butuh: pip install pyarrow
curl -F "file=@data.csv" -F "compression=snappy" http://127.0.0.1:5000/api/compress/csv-to-parquet -o data.parquet
curl -F "file=@data.parquet" http://127.0.0.1:5000/api/compress/parquet-to-csv -o data.csv

# Bandingkan rasio kompresi semua algoritma sekaligus -> tahu mana yang paling optimal
curl -F "file=@data.log" http://127.0.0.1:5000/api/compress/compare
```

## Format Response
- Endpoint yang menghasilkan **file** (PDF/gambar/xlsx/zip/sql) → mengembalikan file langsung (`Content-Disposition: attachment`).
- Endpoint yang menghasilkan **data** → JSON dengan format:
  ```json
  { "ok": true, "data": { ... } }
  ```
  atau saat error:
  ```json
  { "ok": false, "error": "pesan error" }
  ```

## Keamanan
- `sql-query` hanya mengizinkan statement `SELECT` (read-only) — mencegah query destruktif.
- `table_name` divalidasi dengan regex untuk mencegah SQL injection lewat nama tabel.
- Semua endpoint yang butuh password (encrypt/decrypt/JWT) memakai algoritma standar
  (Fernet/AES via `cryptography`, PBKDF2 200.000 iterasi).
- Ukuran upload dibatasi 200MB (`MAX_CONTENT_LENGTH` di `app.py`, bisa diubah).
- Aplikasi ini didesain untuk **penggunaan lokal/internal**. Kalau mau diekspos ke
  internet, tambahkan reverse proxy (nginx), HTTPS, rate limiting, dan autentikasi (API key/JWT)
  di depan `app.py` — belum termasuk di versi ini.

## Menambah Endpoint Baru
Setiap kategori adalah Flask Blueprint terpisah di `routes/`. Untuk menambah endpoint baru:
1. Buka file blueprint terkait (misal `routes/pdf_tools.py`).
2. Tambahkan fungsi baru dengan decorator `@pdf_bp.route("/nama-endpoint", methods=["POST"])`.
3. Restart `python3 app.py` — endpoint otomatis muncul di homepage `/`.
