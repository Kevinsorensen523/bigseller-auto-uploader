"""Script eksplorasi: buka halaman login BigSeller secara headed, lalu dump
HTML ke logs/login_page.html untuk dilihat strukturnya. Browser dibiarkan
terbuka supaya bisa dipakai untuk login manual/selesaikan captcha kalau perlu.

Jalankan: python scripts/inspect_login.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from playwright.sync_api import sync_playwright

from bigseller_auto_uploader import config

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    page = browser.new_page()
    page.goto(config.BIGSELLER_LOGIN_URL)
    page.wait_for_load_state("networkidle")

    html_path = config.LOGS_DIR / "login_page.html"
    html_path.write_text(page.content(), encoding="utf-8")
    print(f"HTML disimpan ke {html_path}")

    screenshot_path = config.LOGS_DIR / "login_page.png"
    page.screenshot(path=str(screenshot_path), full_page=True)
    print(f"Screenshot disimpan ke {screenshot_path}")

    input("Browser dibiarkan terbuka untuk inspect manual. Tekan Enter di terminal ini untuk menutup...")
    browser.close()
