import csv
import sys
import time

from playwright.sync_api import sync_playwright

from . import config
from . import login as login_module
from . import uploader
from .data_loader import load_products


def _product_to_job(product) -> dict:
    variants = [
        {
            "value": v.dimension1_value,
            "sku": v.sku,
            "price": v.price,
            "stock": v.stock,
        }
        for v in product.variants
    ]
    dimension_name = product.variants[0].dimension1_name if product.variants else ""
    return {
        "job_id": product.product_id,
        "store_name": product.store,
        "category_keyword": product.category,
        "category_match_text": None,
        "product_name": product.name,
        "description": product.description,
        "weight_grams": product.weight_grams,
        "brand": "Tidak ada merek",
        "images": [product.image_path] if product.image_path else [],
        "video": None,
        "dimension_name": dimension_name,
        "variants": variants,
        "single_price": None,
        "single_stock": None,
        "shipping_all": True,
        "publish": False,
    }


def run(products_csv=None, variants_csv=None):
    if not config.has_credentials():
        print(
            "BIGSELLER_USERNAME/BIGSELLER_PASSWORD belum diisi di .env. "
            "Isi dulu sebelum menjalankan proses login."
        )
        sys.exit(1)

    products = load_products(products_csv, variants_csv)
    if not products:
        print("Tidak ada produk untuk diupload.")
        return

    results = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=config.HEADLESS)
        context, page = login_module.ensure_logged_in(browser, viewport={"width": 1440, "height": 900})

        if context is None or not login_module.is_logged_in(page):
            print("Login gagal. Cek kredensial atau apakah ada captcha/OTP yang perlu diselesaikan manual.")
            browser.close()
            sys.exit(1)

        for i, product in enumerate(products):
            print(f"[{i + 1}/{len(products)}] Uploading {product.product_id} - {product.name} ...")
            job = _product_to_job(product)
            success, message = uploader.upload_job(context, job)
            results.append(
                {
                    "product_id": product.product_id,
                    "name": product.name,
                    "status": "SUCCESS" if success else "FAILED",
                    "message": message,
                }
            )
            print(f"  -> {'SUCCESS' if success else 'FAILED'}: {message}")

            if i < len(products) - 1:
                time.sleep(config.DELAY_BETWEEN_PRODUCTS_SEC)

        browser.close()

    write_report(results)


def write_report(results, output_path=None):
    output_path = output_path or config.OUTPUT_REPORT_CSV
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["product_id", "name", "status", "message"])
        writer.writeheader()
        writer.writerows(results)

    success_count = sum(1 for r in results if r["status"] == "SUCCESS")
    failed_count = len(results) - success_count
    print(f"\nSelesai. Sukses: {success_count}, Gagal: {failed_count}")
    print(f"Laporan lengkap: {output_path}")


if __name__ == "__main__":
    run()
