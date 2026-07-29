import argparse
import sys

from playwright.sync_api import sync_playwright

from . import config
from . import login as login_module
from . import queue_runner


def run_queue(publish: bool = False, limit: int | None = None):
    queue_runner.run_queue(publish=publish, limit=limit, log=print)


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


def scrape_stores():
    from .scrape_stores import save_stores, scrape_stores as do_scrape_stores

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

        print("Mulai scrape daftar toko...")
        stores = do_scrape_stores(page.request)
        save_stores(stores)

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

    sub.add_parser("scrape-stores", help="Scrape/refresh daftar toko Shopee yang terhubung untuk dropdown di web UI")

    args = parser.parse_args()

    if args.command == "run-queue":
        run_queue(publish=args.publish, limit=args.limit)
    elif args.command == "run-csv":
        run_csv()
    elif args.command == "scrape-categories":
        scrape_categories(shop_id=args.shop_id)
    elif args.command == "scrape-stores":
        scrape_stores()


if __name__ == "__main__":
    main()
