@echo off
REM Jalankan file ini di Windows (double-click atau lewat Command Prompt) di
REM dalam folder project ini. Butuh Python terinstall SEKALI di komputer yang
REM dipakai buat nge-build (https://www.python.org/downloads/, centang "Add
REM python.exe to PATH" pas install). Hasil akhirnya di folder
REM dist\bigseller-uploader\ - folder itu bisa di-copy ke PC Windows LAIN yang
REM sama sekali belum pernah install Python/Playwright, tetap bisa jalan.

setlocal
cd /d "%~dp0"

where python >nul 2>nul
if errorlevel 1 (
  echo [ERROR] Python belum ketemu di PATH.
  echo Install dulu dari https://www.python.org/downloads/ lalu WAJIB centang "Add python.exe to PATH" pas install.
  pause
  exit /b 1
)

echo === Bikin virtual environment build_venv ===
python -m venv build_venv
call build_venv\Scripts\activate.bat

echo === Install project + PyInstaller ===
pip install -e .
pip install pyinstaller

echo === Download Chromium buat di-bundle ke exe ===
set PLAYWRIGHT_BROWSERS_PATH=0
python -m playwright install chromium

for /f "delims=" %%i in ('python -c "import playwright,os;print(os.path.dirname(playwright.__file__))"') do set PW_PKG_DIR=%%i
for /f "delims=" %%i in ('python -c "import glob,os;m=glob.glob(os.path.join(r'%PW_PKG_DIR%','**','.local-browsers'),recursive=True);print(m[0] if m else '')"') do set PW_BROWSERS_DIR=%%i

if "%PW_BROWSERS_DIR%"=="" (
  echo [ERROR] Gagal nemuin folder Chromium hasil download. Cek koneksi internet lalu jalankan ulang file ini.
  pause
  exit /b 1
)

echo === Build exe (bisa beberapa menit) ===
pyinstaller run_ui.py --name bigseller-uploader --onedir --noconfirm ^
  --add-data "bigseller_auto_uploader\templates;bigseller_auto_uploader\templates" ^
  --add-data "%PW_BROWSERS_DIR%;playwright\driver\package\.local-browsers" ^
  --collect-all playwright

echo === Siapin folder pendukung (.env, data, jobs) ===
copy /Y .env.example dist\bigseller-uploader\.env.example >nul
mkdir dist\bigseller-uploader\data\images 2>nul
mkdir dist\bigseller-uploader\jobs\pending 2>nul
mkdir dist\bigseller-uploader\jobs\done 2>nul
mkdir dist\bigseller-uploader\jobs\failed 2>nul
mkdir dist\bigseller-uploader\jobs\skipped 2>nul

echo.
echo ============================================================
echo SELESAI. Hasil build ada di: dist\bigseller-uploader\
echo.
echo Langkah selanjutnya:
echo   1. Buka folder dist\bigseller-uploader\
echo   2. Copy .env.example jadi .env, isi BIGSELLER_USERNAME / PASSWORD
echo   3. Double-click bigseller-uploader.exe
echo.
echo Seluruh folder dist\bigseller-uploader\ bisa di-copy ke PC Windows lain
echo yang belum pernah install Python - tidak perlu build ulang di sana.
echo ============================================================
pause
