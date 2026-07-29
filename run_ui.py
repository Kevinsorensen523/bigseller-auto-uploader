"""Entry point untuk build .exe (PyInstaller). Cukup jalankan file ini
langsung, sama seperti `bigseller-ui` di terminal."""

import os
import sys

# Harus di-set SEBELUM playwright ke-import (lewat queue_runner/uploader) -
# browser Chromium di-bundle di dalam .exe pas build (lihat
# .github/workflows/build-windows-exe.yml), bukan di-download ulang di PC
# user. PLAYWRIGHT_BROWSERS_PATH=0 bikin playwright cari browser relatif ke
# folder package-nya sendiri, bukan cache global (~/.cache/ms-playwright)
# yang belum tentu ada di PC yang belum pernah pasang Playwright.
os.environ.setdefault("PLAYWRIGHT_BROWSERS_PATH", "0")

if getattr(sys, "frozen", False):
    # Saat di-bundle PyInstaller, "project" default (cwd) bisa jadi folder
    # temp ekstraksi - arahkan ke folder tempat .exe-nya sendiri berada
    # supaya jobs/, data/, .env dibaca/ditulis di sebelah .exe, bukan hilang
    # begitu proses selesai.
    os.environ.setdefault("BIGSELLER_PROJECT_DIR", os.path.dirname(sys.executable))

from bigseller_auto_uploader.webapp import main

if __name__ == "__main__":
    main()
