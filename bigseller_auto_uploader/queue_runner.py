import json
import shutil
from collections.abc import Callable

from playwright.sync_api import sync_playwright

from . import config
from . import login as login_module
from . import uploader


def ensure_job_dirs() -> None:
    for d in (config.JOBS_PENDING_DIR, config.JOBS_DONE_DIR, config.JOBS_FAILED_DIR, config.JOBS_SKIPPED_DIR):
        d.mkdir(parents=True, exist_ok=True)


def run_queue(publish: bool = False, limit: int | None = None, log: Callable[[str], None] = print) -> None:
    """Proses semua job pending. Dipakai oleh CLI (`run-queue`) dan web UI
    (tombol "Jalankan Sekarang") - `log` dipanggil per baris progres supaya
    web UI bisa streaming log yang sama seperti output terminal."""
    if not config.has_credentials():
        log("BIGSELLER_USERNAME/BIGSELLER_PASSWORD belum diisi di .env.")
        return

    ensure_job_dirs()
    job_dirs = sorted(d for d in config.JOBS_PENDING_DIR.iterdir() if d.is_dir())
    if limit:
        job_dirs = job_dirs[:limit]

    if not job_dirs:
        log("Tidak ada job pending di antrian.")
        return

    log(f"Memproses {len(job_dirs)} job ({'Save & Publish' if publish else 'Save to Draft'})...")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=config.HEADLESS)
        context, page = login_module.ensure_logged_in(browser, viewport={"width": 1440, "height": 900})

        if context is None or not login_module.is_logged_in(page):
            log("Login gagal. Cek kredensial atau captcha yang perlu diselesaikan manual.")
            browser.close()
            return

        for job_dir in job_dirs:
            job_file = job_dir / "job.json"
            if not job_file.exists():
                continue

            job = json.loads(job_file.read_text(encoding="utf-8"))
            job["images"] = [str(job_dir / f) for f in job.get("images", [])]
            if job.get("video"):
                job["video"] = str(job_dir / job["video"])
            job["publish"] = publish

            log(f"Uploading: {job['product_name']} ...")
            success, message = uploader.upload_job(context, job)
            log(f"  -> {'OK' if success else 'GAGAL'}: {message}")

            target_root = config.JOBS_DONE_DIR if success else config.JOBS_FAILED_DIR
            shutil.move(str(job_dir), str(target_root / job_dir.name))

        browser.close()

    log("Selesai. Lihat jobs/done/ dan jobs/failed/ untuk detail per job.")
