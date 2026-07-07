#!/usr/bin/env bash
# Converter Toolkit Pro - Launcher satu klik (Linux/Mac)
set -e
cd "$(dirname "$0")"

echo "====================================================="
echo "  CONVERTER TOOLKIT PRO - Starting..."
echo "====================================================="
echo

# 1. Cek python3 tersedia
if ! command -v python3 &> /dev/null; then
    echo "[x] python3 tidak ditemukan. Install Python 3 terlebih dahulu."
    read -p "Tekan ENTER untuk keluar..."
    exit 1
fi

# 2. Buat virtual environment kalau belum ada
if [ ! -d "venv" ]; then
    echo "[*] Membuat virtual environment pertama kali..."
    python3 -m venv venv
fi

# 3. Aktifkan venv
source venv/bin/activate

# 4. Install dependency hanya sekali
if [ ! -f "venv/.installed" ]; then
    echo "[*] Instalasi pertama kali, install dependency ... ini bisa beberapa menit."
    python -m pip install --upgrade pip -q
    python -m pip install -r requirements.txt
    touch venv/.installed
    echo "[OK] Dependency berhasil diinstall."
else
    echo "[OK] Dependency sudah terinstall sebelumnya, lewati instalasi."
fi

echo
echo "[*] Menjalankan server di http://127.0.0.1:5000 ..."
echo "    Tekan CTRL+C untuk menghentikan."
echo

# 5. Buka browser otomatis setelah 2 detik (di background), lalu jalankan server
(
  sleep 2
  if command -v xdg-open &> /dev/null; then
    xdg-open http://127.0.0.1:5000
  elif command -v open &> /dev/null; then
    open http://127.0.0.1:5000
  fi
) &

python app.py
