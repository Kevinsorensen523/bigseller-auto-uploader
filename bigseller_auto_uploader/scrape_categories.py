"""Scrape seluruh tree kategori Shopee dari API internal BigSeller
(`/api/v1/product/category/queryList/shopee.json`) dan simpan jadi satu
file JSON datar (leaf categories only, dengan breadcrumb path lengkap).

Kategori Shopee bersifat global per marketplace (Indonesia), bukan per-toko,
jadi cukup di-scrape SEKALI pakai shopId toko mana pun yang sedang login,
lalu dipakai ulang untuk semua toko di UI.

Dipanggil dari script terpisah (butuh browser yang sudah login) -
lihat scripts/scrape_categories.py di root repo.
"""

import json
import time

from . import config

API_URL = "https://www.bigseller.com/api/v1/product/category/queryList/shopee.json"
CATEGORIES_JSON_PATH = config.PROJECT_DIR / "bigseller_auto_uploader" / "data_files" / "categories_shopee_id.json"


def _fetch_children(request_context, shop_id: int, pcid: int, max_retries: int = 6) -> list[dict]:
    backoff = 2.0
    for attempt in range(max_retries):
        resp = request_context.get(f"{API_URL}?pcid={pcid}&shopId={shop_id}")
        data = resp.json()
        if data.get("code") == 0:
            return data.get("data", [])
        if "frequent" in (data.get("msg") or "").lower() and attempt < max_retries - 1:
            print(f"  ... rate limited di pcid={pcid}, tunggu {backoff:.0f}s (percobaan {attempt + 1}/{max_retries})")
            time.sleep(backoff)
            backoff = min(backoff * 1.8, 30)
            continue
        raise RuntimeError(f"API error pcid={pcid}: {data.get('msg')}")
    raise RuntimeError(f"API tetap rate-limited setelah {max_retries} percobaan, pcid={pcid}")


def scrape_all_categories(request_context, shop_id: int, delay_sec: float = 0.6) -> list[dict]:
    """Return list of leaf categories: [{"cid", "path", "path_en"}, ...]
    path = breadcrumb Indonesia dipisah "/", sama persis format yang tampil
    di hasil pencarian modal "Select Category" BigSeller."""
    leaves = []
    visited_count = 0

    def walk(pcid: int, path_id: list[str], path_en: list[str]):
        nonlocal visited_count
        children = _fetch_children(request_context, shop_id, pcid)
        visited_count += 1
        if visited_count % 20 == 0:
            print(f"  ... {visited_count} node dijelajahi, {len(leaves)} leaf category ditemukan")
        time.sleep(delay_sec)

        for child in children:
            child_path_id = path_id + [child["name"]]
            child_path_en = path_en + [child.get("nameEn") or child["name"]]
            if child["leaf"]:
                leaves.append(
                    {
                        "cid": child["cid"],
                        "path": "/".join(child_path_id),
                        "path_en": "/".join(child_path_en),
                    }
                )
            else:
                walk(child["cid"], child_path_id, child_path_en)

    walk(0, [], [])
    print(f"Selesai: {visited_count} node dijelajahi, {len(leaves)} leaf category total")
    return leaves


def save_categories(leaves: list[dict]) -> None:
    CATEGORIES_JSON_PATH.parent.mkdir(parents=True, exist_ok=True)
    CATEGORIES_JSON_PATH.write_text(json.dumps(leaves, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Tersimpan ke {CATEGORIES_JSON_PATH}")


def load_categories() -> list[dict]:
    if not CATEGORIES_JSON_PATH.exists():
        return []
    return json.loads(CATEGORIES_JSON_PATH.read_text(encoding="utf-8"))
