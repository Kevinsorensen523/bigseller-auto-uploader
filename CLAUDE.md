# bigseller-auto-uploader

## Ringkasan proyek

Playwright automation (Python, sync API) untuk login ke BigSeller dan
menambahkan produk + varian (Warna, Ukuran, dll) secara massal dari
`data/products.csv` + `data/variants.csv`, ke halaman listing:
`https://www.bigseller.com/web/listing/shopee/active/index.htm?bsStatus=4`

Status: **scaffold selesai, login belum berhasil dikonfirmasi end-to-end,
alur "Tambah Produk" belum pernah diinspect sama sekali.**

## Tech stack

- Python 3.14 (venv di `.venv/`)
- `playwright==1.61.0` (sync API) — sengaja tidak dipin ke versi lama;
  versi awal `1.47.0`/`greenlet` gagal build dari source karena belum ada
  wheel untuk Python 3.14 di macOS (clang error). Kalau downgrade Python,
  boleh coba pin versi lebih lama lagi.
- `python-dotenv==1.2.2` untuk load `.env`
- Tidak pakai pandas — parsing CSV manual pakai `csv` stdlib di `data_loader.py`

## Struktur file

- `config.py` — load `.env`, expose semua konstanta (URL, delay, timeout, kredensial). `has_credentials()` untuk cek username+password terisi.
- `data_loader.py` — `Product` & `VariantCombination` dataclass. `load_products()` gabungkan products.csv + variants.csv per `product_id`. `Product.dimension_names` & `Product.dimension_values(name)` derive nama/nilai dimensi varian (mis. Warna→[Merah,Biru]) dari urutan kemunculan di CSV.
- `login.py` — fungsi `login(page)` dan `is_logged_in(page)`.
- `uploader.py` — `navigate_to_add_product`, `fill_basic_info`, `upload_images`, `setup_variant_dimensions`, `fill_variant_combinations`, `save_product`, `upload_product()` (orchestrator, screenshot otomatis ke `logs/` kalau gagal di step manapun), `take_screenshot()`.
- `main.py` — loop semua produk dari CSV, login sekali, upload tiap produk, tulis `output_report.csv` (product_id, name, status, message).
- `scripts/inspect_login.py` — script eksplorasi headed manual (buka login page, dump HTML+screenshot ke `logs/`, browser dibiarkan terbuka).
- `data/products.csv`, `data/variants.csv` — 1 produk contoh ("Kaos Polos", P001) dengan 4 kombinasi Warna×Ukuran, buat testing.
- `data/images/kaos-polos.jpg` — placeholder JPEG 1x1 px dummy (bukan gambar asli, cukup untuk uji upload_images).
- `.env` — kredensial asli (gitignored). `.env.example` — template.

## Code style & konvensi

- Semua fungsi Playwright pakai `page.wait_for_timeout(config.ACTION_DELAY_MS)` setelah tiap aksi isi/klik — **jangan turunkan ACTION_DELAY_MS / DELAY_BETWEEN_PRODUCTS_SEC di bawah default tanpa diminta user** (risiko rate-limit / input sebelum render selesai).
- Selector yang **belum diverifikasi ke DOM asli** ditandai komentar `# TODO ganti selector asli` — jangan hapus komentar ini sampai selector benar-benar dicek manual.
- Kredensial **tidak boleh** di-hardcode; selalu dari `config.py` → `.env`.
- Kalau ketemu captcha/OTP saat login: **jangan coba baca/bypass otomatis**. Beri tahu user, isi manual di window browser headed yang terbuka, script `login.py` menunggu (`MANUAL_STEP_TIMEOUT_MS`, default 5 menit) sampai URL berubah dari `login`.

## Status selector per file (per sesi terakhir)

### `login.py` — sudah diverifikasi ke DOM asli
- Username: `input[name='account']`
- Password: `input[name='password']`
- Checkbox setuju T&C: klik `label.el-checkbox` (bukan `input.el-checkbox__original` langsung — elemen input-nya visually-hidden ala Element Plus, klik langsung gagal "outside viewport"; harus pakai `viewport={'width':1440,'height':900}` juga saat `new_page()`).
- Captcha grafis: `input[name='picVerificationCode']` — field wajib, manual only.
- Tombol submit (kalau tidak ada captcha — kondisi ini belum pernah terjadi di praktik): `button.opt-btn`.
- `is_logged_in()` masih sederhana: cek `"login" not in page.url.lower()`. Belum divalidasi dengan kondisi sukses nyata karena login end-to-end belum pernah berhasil dalam sesi kerja sejauh ini.

### `uploader.py` — SEMUA selector masih placeholder/TODO, belum pernah diverifikasi
Belum pernah sampai ke halaman "Tambah Produk" karena login belum tuntas. Semua ini masih dummy dan **wajib diinspect ulang** begitu login berhasil:
- `navigate_to_add_product` — tombol "Tambah Produk"
- `fill_basic_info` — nama, kategori (kemungkinan dropdown/modal bertingkat di BigSeller, alurnya belum jelas), deskripsi
- `upload_images` — input file
- `setup_variant_dimensions` — tombol tambah spesifikasi, input nama & nilai dimensi
- `fill_variant_combinations` — tabel kombinasi varian, kolom SKU/harga/stok
- `save_product` — tombol simpan, deteksi toast sukses/gagal

## Known issues / bug log

1. **Login belum pernah berhasil end-to-end dalam sesi kerja.** Dua percobaan:
   - Percobaan 1: timeout 5 menit menunggu captcha manual (user belum sempat isi / ganti akun di tengah jalan).
   - Percobaan 2: dibatalkan user sebelum sempat jalan (mau ganti akun dulu).
   - Setelah user ganti kredensial di `.env`, percobaan berikutnya belum sempat dijalankan ulang.
2. `agree_checkbox.click(force=True)` pada `input.el-checkbox__original` gagal dengan `Element is outside of the viewport` — **sudah diperbaiki** dengan klik `label.el-checkbox` sebagai gantinya (lihat di atas). Kalau muncul lagi, cek ukuran viewport `new_page()`.
3. Belum ada validasi nyata untuk `is_logged_in()` — kondisi saat ini cuma cek URL, perlu dikonfirmasi begitu ada sesi login sukses (mis. cek elemen avatar user atau redirect spesifik ke dashboard).

## TODO / next steps (urutan yang disarankan)

1. Konfirmasi `.env` sudah pakai kredensial akun yang benar (`BIGSELLER_USERNAME`, `BIGSELLER_PASSWORD`).
2. Jalankan ulang percobaan login headed (lihat pola di riwayat sesi: buat `sync_playwright()`, `new_page(viewport={'width':1440,'height':900})`, panggil `login.login(page)`), biarkan user isi captcha manual, konfirmasi berhasil masuk ke dashboard/listing.
3. Setelah login sukses, validasi/refine `is_logged_in()` dengan penanda nyata.
4. Navigasi manual/step-by-step ke alur "Tambah Produk" dari halaman listing, inspect DOM tiap tahap (nama produk, kategori, deskripsi, upload gambar, buat dimensi varian, isi tabel kombinasi, tombol simpan + toast sukses/gagal).
5. Update semua selector placeholder di `uploader.py` sesuai temuan (jangan ubah struktur/logic loop-nya).
6. Test end-to-end 1 produk dari `data/products.csv` (data contoh P001 sudah disiapkan).
7. Kalau 1 produk sukses, jalankan `main.py` dengan data lengkap, laporkan hasil dari `output_report.csv` (jumlah sukses/gagal + alasan gagal).

## Test scenarios belum selesai

- [ ] Login end-to-end sukses (dengan captcha manual) → belum pernah terjadi.
- [ ] Navigasi ke "Tambah Produk" dari halaman listing.
- [ ] Isi basic info produk (nama, kategori, deskripsi) — alur kategori BigSeller (dropdown/modal bertingkat) belum diketahui bentuknya.
- [ ] Upload gambar produk.
- [ ] Buat dimensi varian (Warna, Ukuran) + isi opsi.
- [ ] Isi tabel kombinasi varian (SKU/harga/stok) per baris.
- [ ] Simpan produk + deteksi sukses/gagal (toast atau redirect).
- [ ] Full run `main.py` dengan seluruh `data/products.csv` + `data/variants.csv`.

## Catatan tambahan dari user

- Jangan percepat `ACTION_DELAY_MS` / `DELAY_BETWEEN_PRODUCTS_SEC` di bawah default tanpa diminta.
- Kalau BigSeller memblokir otomasi (captcha berulang, verifikasi device, dll), laporkan ke user — jangan coba bypass.
