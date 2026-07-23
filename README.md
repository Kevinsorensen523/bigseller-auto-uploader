# bigseller-auto-uploader

Playwright automation untuk login ke [BigSeller](https://www.bigseller.com) dan
menambahkan produk + varian (Warna, Ukuran, Tipe HP, dll) ke listing Shopee,
tanpa isi form manual satu-satu di browser.

Tiga cara pakai:

1. **Web UI lokal** — isi form di browser, submit masuk antrian, proses belakangan.
2. **CLI queue runner** — proses semua job yang ngantri dari web UI.
3. **CSV batch** (mode lama) — isi `data/products.csv` + `data/variants.csv`, jalankan sekali proses semua.

Package ini juga bisa **diinstall di project lain** lewat `pip install git+...` (lihat di bawah).

---

## Instalasi

```bash
git clone https://github.com/Kevinsorensen523/bigseller-auto-uploader.git
cd bigseller-auto-uploader

python3 -m venv .venv
source .venv/bin/activate      # tiap buka terminal baru, jalankan ini dulu!

pip install -e .
playwright install chromium
```

> **Command `bigseller-ui` / `bigseller-upload` not found?** Hampir selalu karena
> venv belum di-*activate* di terminal itu. Jalankan `source .venv/bin/activate`
> dulu (harus diulang tiap buka terminal baru), baru command-nya kebaca.

### Install ke project lain

Dari project Python lain yang mau makai automasi ini:

```bash
pip install git+https://github.com/Kevinsorensen523/bigseller-auto-uploader.git
```

Lalu dari kode Python:

```python
from bigseller_auto_uploader import login, uploader
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    context, page = login.ensure_logged_in(browser, viewport={"width": 1440, "height": 900})
    uploader.upload_job(context, {...})  # lihat skema job di bawah
```

atau langsung pakai CLI/`bigseller-ui` yang ikut terpasang.

---

## Setup akun

```bash
cp .env.example .env
```

Isi `.env`:

```
BIGSELLER_USERNAME=...
BIGSELLER_PASSWORD=...
HEADLESS=false
```

Jangan hardcode kredensial di kode - selalu lewat `.env` (di-gitignore, tidak ikut ke repo).

### Login & captcha

Halaman login BigSeller pakai **captcha grafis wajib**. Script akan isi
username/password otomatis lalu **berhenti menunggu Anda isi captcha manual**
di window browser yang terbuka (headed, `HEADLESS=false`) - maksimal 5 menit.
Kami sengaja tidak mencoba membaca/bypass captcha secara otomatis.

Setelah login sukses sekali, sesi (cookies) disimpan ke `.playwright_session.json`
dan dipakai ulang di run-run berikutnya - **tidak perlu isi captcha lagi** selama
sesi masih valid.

---

## Cara 1: Web UI lokal

```bash
bigseller-ui
```

Buka `http://127.0.0.1:5151`. Isi form: store, nama produk, kategori (keyword
pencarian), deskripsi, berat, brand, upload foto + video, dan varian (bisa
tambah baris sebanyak apa pun, tiap baris punya SKU/harga/stock sendiri -
harga/stock **boleh beda-beda per varian**).

Submit **tidak langsung upload** - tersimpan sebagai job di `jobs/pending/`.
Review dulu di halaman `/queue`, baru proses beneran pakai CLI di bawah.

## Cara 2: Proses antrian (CLI)

```bash
bigseller-upload run-queue            # default: Save to Draft (aman, belum tayang)
bigseller-upload run-queue --publish  # langsung Save & Publish (LANGSUNG TAYANG di Shopee)
bigseller-upload run-queue --limit 5  # proses maks 5 job dulu
```

Job yang sukses dipindah ke `jobs/done/`, yang gagal ke `jobs/failed/`
(screenshot error otomatis tersimpan di `logs/` - lihat itu buat debug, lalu
pindahkan job-nya balik ke `jobs/pending/` untuk dicoba ulang).

## Cara 3: CSV batch (mode lama)

Isi `data/products.csv` dan `data/variants.csv` (lihat contoh format di file
itu), lalu:

```bash
bigseller-upload run-csv
# atau, kalau belum pip install -e .:
python main.py
```

Hasilnya di `output_report.csv` (jumlah sukses/gagal + alasan gagal).

---

## Skema job (dipakai web UI & bisa dipanggil manual)

```json
{
  "job_id": "abc123",
  "store_name": "Click Acc Shopee",
  "category_keyword": "Pelindung Layar",
  "category_match_text": "Pelindung Layar Handphone",
  "product_name": "...",
  "description": "...",
  "weight_grams": 50,
  "brand": "Tidak ada merek",
  "images": ["foto1.jpg", "foto2.jpg"],
  "video": "video.mp4",
  "dimension_name": "Tipe iPhone",
  "variants": [
    {"value": "X/XS", "sku": "TG-KA-A15-IPHONE-X-XS", "price": 180000, "stock": 1000},
    {"value": "XR",   "sku": "TG-KA-A15-IPHONE-XR",   "price": 180000, "stock": 500}
  ],
  "single_price": null,
  "single_stock": null,
  "shipping_all": true,
  "publish": false
}
```

Kalau produk tanpa varian, kosongkan `variants` (`[]`) dan isi `single_price`
+ `single_stock` saja.

`category_match_text` opsional - kalau kosong, hasil pencarian kategori
pertama otomatis dipilih. `store_name` harus persis sama dengan teks yang
muncul di dropdown Store BigSeller (case-sensitive, cek dulu di web UI).

---

## Hal-hal penting yang perlu diketahui

- **Urutan pengisian form penting**: kategori harus dipilih **sebelum**
  tabel SKU/Stock/Price diisi. Ganti kategori setelah tabel terisi akan
  **mereset seluruh tabel** (perilaku BigSeller, bukan bug automasi ini).
  `uploader.upload_job()` sudah mengikuti urutan yang benar.
- **Video resolusi tinggi gagal ter-upload tanpa error apa pun** walau
  ukurannya di bawah limit 30MB (mis. rekaman HP modern 2160x3840). Downscale
  dulu ke resolusi wajar (mis. 1080x1920) sebelum upload, contoh pakai ffmpeg:
  ```bash
  ffmpeg -i original.mp4 -vf "scale=1080:1920" -c:v libx264 -b:v 4M -c:a aac -b:a 128k out.mp4
  ```
- **Jangan percepat delay** (`ACTION_DELAY_MS`, `DELAY_BETWEEN_PRODUCTS_SEC` di
  `.env`) di bawah default tanpa alasan kuat - risiko rate-limit atau input
  ke elemen yang belum selesai render.
- Kalau BigSeller minta verifikasi device / captcha berulang terus, itu tanda
  mereka mendeteksi otomasi - jangan coba paksa bypass, tunggu atau login manual
  dulu dari browser biasa.

---

## Struktur project

```
bigseller_auto_uploader/   # package inti (importable, terinstall via pip)
  config.py                #   baca .env, path-path project
  login.py                 #   login + captcha manual + session reuse
  uploader.py               #   semua step isi form Add Product BigSeller
  data_loader.py            #   parser data/products.csv + variants.csv
  main.py                   #   mode CSV batch
  cli.py                    #   entry point `bigseller-upload`
  webapp.py                 #   entry point `bigseller-ui` (Flask)
  templates/                #   HTML form web UI
data/                       # products.csv, variants.csv, foto/video (gitignored)
jobs/{pending,done,failed}/ # antrian job dari web UI (gitignored)
logs/                       # screenshot error otomatis (gitignored)
scripts/inspect_login.py    # tool eksplorasi manual kalau BigSeller ganti UI
```

## Development

Untuk kerja di repo ini sendiri (bukan sebagai dependency di project lain):

```bash
pip install -e .
```

`-e` (editable install) supaya perubahan di `bigseller_auto_uploader/`
langsung kepakai tanpa perlu reinstall.
