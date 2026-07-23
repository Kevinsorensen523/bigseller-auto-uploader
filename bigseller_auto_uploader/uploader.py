from datetime import datetime

from . import config

STORE_BUTTON = "[autoid='store_button']"
SELECT_CATEGORY_BUTTON = "[autoid='select_category_button']"
CATEGORY_SEARCH_INPUT = "[autoid='category_name_search_text']"
CATEGORY_SEARCH_BUTTON = "[autoid='category_name_search_button']"
PRODUCT_NAME_INPUT = "[autoid='product_name_text']"
DESCRIPTION_TEXTAREA = "[autoid='product_description_text']"
SELECT_IMAGES_BUTTON = "[autoid='select_images_button']"
ADD_FROM_COMPUTER_OPTION = "[autoid='add_from_computer_option']"
UPLOAD_LOCAL_VIDEO_OPTION = "[autoid='upload_local_video_option']"
MULTIPLE_VARIATIONS_BUTTON = "[autoid='multiple_variations_button']"
ADD_VARIATION_OPTION = "[autoid='add_variation_option']"
WEIGHT_INPUT = "[autoid='weight_text']"
SAVE_DRAFT_BUTTON = "[autoid='save_to_draft_button']"
SAVE_PUBLISH_BUTTON = "[autoid='save_and_publish_button']"
SAVE_PUBLISH_OPTION = "[autoid='save_and_publish_option']"
SINGLE_PRICE_INPUT = "[autoid='single_variation_price_text']"
SINGLE_STOCK_INPUT = "[autoid='single_variation_stock_text']"


def take_screenshot(page, job_id: str, step: str) -> str:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = config.LOGS_DIR / f"{job_id}_{step}_{ts}.png"
    page.screenshot(path=str(path), full_page=True)
    return str(path)


def navigate_to_add_product(context):
    """Dari halaman listing, buka form Tambah Produk. Tombol "Add Product"
    membuka TAB BARU (.../listing/shopee/add.htm) - fungsi ini mengembalikan
    page dari tab baru tersebut."""
    listing_page = context.new_page()
    listing_page.set_default_timeout(config.DEFAULT_TIMEOUT_MS)
    listing_page.goto(config.BIGSELLER_LISTING_URL)
    listing_page.wait_for_load_state("networkidle")
    listing_page.wait_for_timeout(config.ACTION_DELAY_MS)

    add_product_button = listing_page.get_by_role("button", name="Add Product")
    with context.expect_page() as new_page_info:
        add_product_button.click()
    add_product_page = new_page_info.value
    add_product_page.set_default_timeout(config.DEFAULT_TIMEOUT_MS)
    add_product_page.wait_for_load_state("networkidle")
    add_product_page.wait_for_timeout(config.ACTION_DELAY_MS)

    listing_page.close()
    return add_product_page


def select_store(page, store_name: str):
    page.locator(STORE_BUTTON).click()
    page.wait_for_timeout(config.ACTION_DELAY_MS)
    page.locator(".ant-select-dropdown-menu-item", has_text=store_name).first.click()
    page.wait_for_timeout(config.ACTION_DELAY_MS)


def select_category(page, keyword: str, match_text: str | None = None):
    """Cari kategori lewat search box modal "Select Category" dan pilih hasil
    pertama yang cocok. PENTING: harus dipanggil SEBELUM setup varian/isi
    tabel SKU-Stock-Price - ganti kategori setelah tabel terisi akan
    me-reset seluruh tabel tsb (perilaku BigSeller, bukan bug kita)."""
    page.locator(SELECT_CATEGORY_BUTTON).click()
    page.wait_for_timeout(config.ACTION_DELAY_MS)
    page.locator(CATEGORY_SEARCH_INPUT).fill(keyword)
    page.locator(CATEGORY_SEARCH_BUTTON).click()
    page.wait_for_timeout(1500)

    results = page.locator(".search_value")
    if match_text:
        results = results.filter(has_text=match_text)
    results.first.click()
    page.wait_for_timeout(config.ACTION_DELAY_MS)


def fill_basic_info(page, product_name: str, description: str):
    page.locator(PRODUCT_NAME_INPUT).fill(product_name)
    page.wait_for_timeout(config.ACTION_DELAY_MS)
    page.locator(DESCRIPTION_TEXTAREA).fill(description)
    page.wait_for_timeout(config.ACTION_DELAY_MS)


def upload_images(page, image_paths: list[str]):
    with page.expect_file_chooser(timeout=10000) as fc_info:
        page.locator(SELECT_IMAGES_BUTTON).click()
        page.wait_for_timeout(300)
        page.locator(ADD_FROM_COMPUTER_OPTION).click()
    fc_info.value.set_files(image_paths)
    page.wait_for_timeout(config.ACTION_DELAY_MS * 6)


def upload_video(page, video_path: str):
    """Upload video lokal. CATATAN PENTING: video beresolusi tinggi (mis.
    2160x3840 dari rekaman HP modern) gagal ter-upload TANPA error apapun
    di BigSeller walau ukurannya di bawah limit 30MB - harus di-downscale
    dulu (mis. ke 1080x1920) sebelum diupload. Lihat CLAUDE.md."""
    page.get_by_role("button", name="Add Video").click()
    page.wait_for_timeout(500)
    with page.expect_file_chooser(timeout=10000) as fc_info:
        page.locator(UPLOAD_LOCAL_VIDEO_OPTION).click()
    fc_info.value.set_files(video_path)
    page.wait_for_timeout(config.ACTION_DELAY_MS * 10)


def select_brand(page, brand_name: str = "Tidak ada merek"):
    brand_select = page.locator(
        "xpath=//div[normalize-space(text())='Brand']/following::div[contains(@class,'ant-select-selection--single')][1]"
    )
    brand_select.click()
    page.wait_for_timeout(800)
    page.locator(".option", has_text=brand_name).first.click()
    page.wait_for_timeout(config.ACTION_DELAY_MS)


def setup_variant_dimension(page, dimension_name: str, values: list[str]):
    """Buat SATU dimensi varian (mis. "Tipe iPhone") dan isi semua opsinya.
    BigSeller batasi nama dimensi 14 karakter dan nama opsi 20 karakter."""
    page.locator(MULTIPLE_VARIATIONS_BUTTON).click()
    page.wait_for_timeout(config.ACTION_DELAY_MS)

    page.locator(ADD_VARIATION_OPTION).click()
    page.wait_for_timeout(config.ACTION_DELAY_MS)
    modal_input = page.locator(".ant-modal-body input").first
    modal_input.fill(dimension_name[:14])
    page.wait_for_timeout(300)
    page.get_by_role("button", name="Confirm").click()
    page.wait_for_timeout(config.ACTION_DELAY_MS)

    value_input = page.locator("input[autoid='add_variation_second_name_text0']")
    add_button = page.locator("[autoid='add_variation_second_name_button0']")
    for value in values:
        value_input.fill(value[:20])
        page.wait_for_timeout(200)
        add_button.click()
        page.wait_for_timeout(200)

    page.keyboard.press("Escape")
    page.wait_for_timeout(300)


def fill_variant_row(page, index: int, sku: str, price, stock):
    """Isi SKU/Stock/Price untuk SATU baris tabel kombinasi varian (index
    0-based, sesuai urutan value yang ditambahkan di setup_variant_dimension).
    Semua baris ada langsung di DOM (bukan virtual-scroll), jadi aman diakses
    langsung tanpa perlu scroll manual."""
    page.locator(f"input[autoid='variation_sku_text_{index}']").fill(sku)
    page.wait_for_timeout(150)
    page.locator(f"input[autoid='variation_stock_text_{index}']").fill(str(stock))
    page.wait_for_timeout(150)
    page.locator(f"input[autoid='variation_price_text_{index}']").fill(str(price))
    page.wait_for_timeout(150)


def fill_single_variation(page, price, stock):
    page.locator(SINGLE_PRICE_INPUT).fill(str(price))
    page.wait_for_timeout(config.ACTION_DELAY_MS)
    page.locator(SINGLE_STOCK_INPUT).fill(str(stock))
    page.wait_for_timeout(config.ACTION_DELAY_MS)


def check_all_shipping(page):
    for i in range(4):
        checkbox = page.locator(f"[autoid='shipping_method_button_{i}']")
        if checkbox.count() > 0:
            checkbox.click()
            page.wait_for_timeout(250)


def set_weight(page, grams):
    page.locator(WEIGHT_INPUT).fill(str(grams))
    page.wait_for_timeout(config.ACTION_DELAY_MS)


def save_product(page, publish: bool = False) -> tuple[bool, str]:
    """Klik Save to Draft (default, aman) atau Save & Publish (kalau
    publish=True). Sukses dideteksi dari redirect keluar halaman add.htm
    kembali ke listing."""
    if publish:
        page.locator(SAVE_PUBLISH_BUTTON).click()
        page.wait_for_timeout(800)
        page.locator(SAVE_PUBLISH_OPTION).click()
    else:
        page.locator(SAVE_DRAFT_BUTTON).click()

    try:
        page.wait_for_url(lambda u: "add.htm" not in u, timeout=25000)
        return True, "OK"
    except Exception:
        return False, "Tidak redirect setelah save - kemungkinan ada field wajib yang belum valid"


def upload_job(context, job: dict) -> tuple[bool, str]:
    """Jalankan satu alur lengkap upload 1 produk (dari dict job, lihat
    skema di webapp.py/cli.py) di tab baru. Screenshot otomatis ke logs/
    kalau gagal."""
    job_id = job.get("job_id", "job")
    try:
        page = navigate_to_add_product(context)
    except Exception as e:
        return False, f"Gagal di step 'navigate': {e}"

    try:
        select_store(page, job["store_name"])
        select_category(page, job["category_keyword"], job.get("category_match_text"))
        fill_basic_info(page, job["product_name"], job["description"])

        if job.get("images"):
            upload_images(page, job["images"])
        if job.get("video"):
            upload_video(page, job["video"])

        select_brand(page, job.get("brand") or "Tidak ada merek")

        variants = job.get("variants") or []
        if variants:
            setup_variant_dimension(page, job["dimension_name"], [v["value"] for v in variants])
            for i, v in enumerate(variants):
                fill_variant_row(page, i, v["sku"], v["price"], v["stock"])
        else:
            fill_single_variation(page, job["single_price"], job["single_stock"])

        if job.get("shipping_all", True):
            check_all_shipping(page)

        set_weight(page, job["weight_grams"])

        success, message = save_product(page, publish=job.get("publish", False))
        if not success:
            screenshot = take_screenshot(page, job_id, "save_failed")
            message = f"{message} (screenshot: {screenshot})"
        return success, message
    except Exception as e:
        screenshot = take_screenshot(page, job_id, "error")
        return False, f"{e} (screenshot: {screenshot})"
