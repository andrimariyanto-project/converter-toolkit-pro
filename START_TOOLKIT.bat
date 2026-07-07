@echo off
title Converter Toolkit Pro - Launcher
color 0B
cd /d "%~dp0"

echo =====================================================
echo   CONVERTER TOOLKIT PRO - Starting...
echo =====================================================
echo.

REM --- 1. Cek Python terinstall ---
where python >nul 2>nul
if errorlevel 1 (
    echo [x] Python tidak ditemukan di PATH.
    echo     Install Python dari https://python.org lalu coba lagi.
    pause
    exit /b 1
)

REM --- 2. Buat virtual environment kalau belum ada ---
if not exist "venv\" (
    echo [*] Membuat virtual environment pertama kali...
    python -m venv venv
    if errorlevel 1 (
        echo [x] Gagal membuat venv. Coba jalankan sebagai Administrator.
        pause
        exit /b 1
    )
)

REM --- 3. Aktifkan venv ---
call "venv\Scripts\activate.bat"
if errorlevel 1 (
    echo [x] Gagal mengaktifkan venv.
    pause
    exit /b 1
)

REM --- 4. Install dependency hanya sekali (pakai file penanda .installed) ---
if not exist "venv\.installed" (
    echo [*] Instalasi pertama kali, install dependency ... ini bisa beberapa menit.
    python -m pip install --upgrade pip >nul 2>nul
    python -m pip install -r requirements.txt
    if errorlevel 1 (
        echo [x] Gagal install dependency. Cek koneksi internet / kebijakan IT ^(Application Control^).
        echo     Coba jalankan manual: python -m pip install -r requirements.txt
        pause
        exit /b 1
    )
    echo done > "venv\.installed"
    echo [OK] Dependency berhasil diinstall.
) else (
    echo [OK] Dependency sudah terinstall sebelumnya, lewati instalasi.
)

echo.
echo [*] Menjalankan server di http://127.0.0.1:5000 ...
echo     Jangan tutup jendela ini selama toolkit digunakan.
echo.

REM --- 5. Jalankan server Flask di jendela ini, buka browser setelah 2 detik ---
start "" /min cmd /c "timeout /t 2 >nul && start http://127.0.0.1:5000"
python app.py

pause
