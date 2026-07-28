"""Scrape daftar toko (shop) yang terhubung ke akun BigSeller, dari
`/api/v1/shopsAndPlatforms.json` (endpoint yang sama dipakai halaman utama
BigSeller buat nampilin daftar toko). Cuma toko platform Shopee yang
diambil, karena package ini fokus ke alur Shopee."""

import json

from . import config

API_URL = "https://www.bigseller.com/api/v1/shopsAndPlatforms.json"
STORES_JSON_PATH = config.PROJECT_DIR / "bigseller_auto_uploader" / "data_files" / "stores_shopee.json"


def scrape_stores(request_context) -> list[dict]:
    resp = request_context.get(API_URL)
    data = resp.json()
    if data.get("code") != 0:
        raise RuntimeError(f"API error: {data.get('msg')}")
    shopee_shops = data.get("data", {}).get("shops", {}).get("shopee", []) or []
    return [{"id": shop["id"], "name": shop["name"]} for shop in shopee_shops]


def save_stores(stores: list[dict]) -> None:
    STORES_JSON_PATH.parent.mkdir(parents=True, exist_ok=True)
    STORES_JSON_PATH.write_text(json.dumps(stores, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Tersimpan ke {STORES_JSON_PATH} ({len(stores)} toko)")


def load_stores() -> list[dict]:
    if not STORES_JSON_PATH.exists():
        return []
    return json.loads(STORES_JSON_PATH.read_text(encoding="utf-8"))
