import argparse
import json
import shutil
import sys

from playwright.sync_api import sync_playwright

from . import config
from . import login as login_module
from . import uploader


def _ensure_job_dirs():
    for d in (config.JOBS_PENDING_DIR, config.JOBS_DONE_DIR, config.JOBS_FAILED_DIR):
        d.mkdir(parents=True, exist_ok=True)


def run_queue(publish: bool = False, limit: int | None = None):
    if not config.has_credentials():
        print("BIGSELLER_USERNAME/BIGSELLER_PASSWORD belum diisi di .env.")
        sys.exit(1)

    _ensure_job_dirs()
    job_dirs = sorted(d for d in config.JOBS_PENDING_DIR.iterdir() if d.is_dir())
    if limit:
        job_dirs = job_dirs[:limit]

    if not job_dirs:
        print("Tidak ada job pending di antrian.")
        return

    print(f"Memproses {len(job_dirs)} job ({'Save & Publish' if publish else 'Save to Draft'})...")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=config.HEADLESS)
        context, page = login_module.ensure_logged_in(browser, viewport={"width": 1440, "height": 900})

        if context is None or not login_module.is_logged_in(page):
            print("Login gagal. Cek kredensial atau captcha yang perlu diselesaikan manual.")
            browser.close()
            sys.exit(1)

        for job_dir in job_dirs:
            job_file = job_dir / "job.json"
            if not job_file.exists():
                continue

            job = json.loads(job_file.read_text(encoding="utf-8"))
            job["images"] = [str(job_dir / f) for f in job.get("images", [])]
            if job.get("video"):
                job["video"] = str(job_dir / job["video"])
            job["publish"] = publish

            print(f"Uploading: {job['product_name']} ...")
            success, message = uploader.upload_job(context, job)
            print(f"  -> {'OK' if success else 'GAGAL'}: {message}")

            target_root = config.JOBS_DONE_DIR if success else config.JOBS_FAILED_DIR
            shutil.move(str(job_dir), str(target_root / job_dir.name))

        browser.close()

    print("Selesai. Lihat jobs/done/ dan jobs/failed/ untuk detail per job.")


def run_csv():
    from . import main as legacy_main

    legacy_main.run()


def scrape_categories(shop_id: int):
    from .scrape_categories import save_categories, scrape_all_categories

    if not config.has_credentials():
        print("BIGSELLER_USERNAME/BIGSELLER_PASSWORD belum diisi di .env.")
        sys.exit(1)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=config.HEADLESS)
        context, page = login_module.ensure_logged_in(browser, viewport={"width": 1440, "height": 900})

        if not login_module.is_logged_in(page):
            print("Login gagal.")
            browser.close()
            sys.exit(1)

        print("Mulai scrape kategori (bisa beberapa menit, ~1700 kategori)...")
        leaves = scrape_all_categories(page.request, shop_id=shop_id)
        save_categories(leaves)

        browser.close()


def main():
    parser = argparse.ArgumentParser(prog="bigseller-upload")
    sub = parser.add_subparsers(dest="command", required=True)

    run_p = sub.add_parser("run-queue", help="Proses semua job pending dari web UI")
    run_p.add_argument("--publish", action="store_true", help="Langsung publish (default: save to draft)")
    run_p.add_argument("--limit", type=int, default=None, help="Batasi jumlah job yang diproses")

    sub.add_parser("run-csv", help="Proses dari data/products.csv + data/variants.csv (mode lama)")

    scrape_p = sub.add_parser(
        "scrape-categories", help="Scrape/refresh daftar kategori Shopee untuk dropdown di web UI"
    )
    scrape_p.add_argument(
        "--shop-id",
        type=int,
        required=True,
        help="Shop ID toko mana pun (kategori Shopee sama untuk semua toko) - lihat di URL API network tab",
    )

    args = parser.parse_args()

    if args.command == "run-queue":
        run_queue(publish=args.publish, limit=args.limit)
    elif args.command == "run-csv":
        run_csv()
    elif args.command == "scrape-categories":
        scrape_categories(shop_id=args.shop_id)


if __name__ == "__main__":
    main()
