from . import config


MANUAL_STEP_TIMEOUT_MS = 5 * 60 * 1000  # 5 menit untuk isi captcha & klik Log In manual


def login(page):
    """Login ke BigSeller pakai kredensial dari .env.

    Halaman login BigSeller mewajibkan kode captcha grafis (gambar acak,
    field 'picVerificationCode'). Kita TIDAK mencoba membaca/bypass captcha
    itu secara otomatis - user harus mengisinya manual & klik "Log In" di
    window browser (headed) yang sedang terbuka.
    """
    page.goto(config.BIGSELLER_LOGIN_URL)
    page.wait_for_timeout(config.ACTION_DELAY_MS)

    username_input = page.locator("input[name='account']")
    password_input = page.locator("input[name='password']")
    agree_checkbox = page.locator("input.el-checkbox__original")
    agree_checkbox_label = page.locator("label.el-checkbox")

    username_input.fill(config.BIGSELLER_USERNAME)
    page.wait_for_timeout(config.ACTION_DELAY_MS)

    password_input.fill(config.BIGSELLER_PASSWORD)
    page.wait_for_timeout(config.ACTION_DELAY_MS)

    if agree_checkbox.count() > 0 and not agree_checkbox.is_checked():
        agree_checkbox_label.click()
        page.wait_for_timeout(config.ACTION_DELAY_MS)

    captcha_input = page.locator("input[name='picVerificationCode']")
    if captcha_input.count() > 0:
        print(
            "\n[login] Terdeteksi kode captcha grafis di halaman login. "
            "Silakan isi kode captcha dan klik tombol 'Log In' secara manual "
            "di window browser yang terbuka.\n"
            f"Menunggu hingga {MANUAL_STEP_TIMEOUT_MS // 1000} detik untuk Anda menyelesaikan login manual..."
        )
        try:
            page.wait_for_url(lambda url: "login" not in url.lower(), timeout=MANUAL_STEP_TIMEOUT_MS)
        except Exception:
            print("[login] Timeout menunggu login manual selesai.")
    else:
        # Tidak ada captcha - submit otomatis.
        submit_button = page.locator("button.opt-btn")
        submit_button.click()
        page.wait_for_timeout(config.ACTION_DELAY_MS)
        page.wait_for_load_state("networkidle")

    _accept_updated_terms_if_present(page)

    # Setelah login, BigSeller sempat mampir ke halaman interstitial
    # ("System Upgraded! ... auto redirected") sebelum ke dashboard.
    # Navigasi langsung ke halaman listing target sebagai pengecekan
    # sesi yang lebih pasti daripada menebak dari URL interstitial.
    page.goto(config.BIGSELLER_LISTING_URL)
    page.wait_for_load_state("networkidle")
    _accept_updated_terms_if_present(page)

    return is_logged_in(page)


def _accept_updated_terms_if_present(page) -> None:
    """Setelah login sukses, BigSeller kadang menampilkan modal blocking
    "The terms of use and privacy policy have been updated" dengan tombol
    "I have read and agreed" (menolak = logout otomatis). Klik setuju kalau
    modal ini muncul."""
    agree_button = page.get_by_role("button", name="I have read and agreed")
    try:
        agree_button.wait_for(state="visible", timeout=8000)
        agree_button.click()
        page.wait_for_timeout(config.ACTION_DELAY_MS)
    except Exception:
        pass  # modal tidak muncul - lanjut seperti biasa


def is_logged_in(page) -> bool:
    """Login dianggap sukses kalau setelah navigasi ke halaman listing
    target, kita tidak dilempar balik ke halaman login."""
    return "login" not in page.url.lower()


def restore_session(browser, viewport=None):
    """Coba pakai sesi tersimpan (cookies/localStorage) dari login sebelumnya
    supaya tidak perlu isi captcha lagi. Return (context, page) kalau sesi
    masih valid, atau (None, None) kalau tidak ada sesi tersimpan / sudah basi."""
    if not config.SESSION_STATE_PATH.exists():
        return None, None

    context = browser.new_context(storage_state=str(config.SESSION_STATE_PATH), viewport=viewport)
    page = context.new_page()
    page.set_default_timeout(config.DEFAULT_TIMEOUT_MS)
    page.goto(config.BIGSELLER_LISTING_URL)
    page.wait_for_load_state("networkidle")
    _accept_updated_terms_if_present(page)

    if is_logged_in(page):
        return context, page

    context.close()
    return None, None


def save_session(context) -> None:
    context.storage_state(path=str(config.SESSION_STATE_PATH))


def attach_default_context(browser, viewport=None):
    """Untuk browser yang disambungkan lewat connect_over_cdp (mis. browser
    persisten di background): context yang dibuat lewat browser.new_context()
    ikut hilang begitu koneksi CDP client-nya disconnect (proses python
    keluar). Supaya sesi tetap hidup lintas beberapa kali run script, kita
    pakai default context bawaan browser (context[0], selalu ada selama
    proses browser masih hidup) dan suntikkan cookies sesi ke situ langsung."""
    context = browser.contexts[0] if browser.contexts else browser.new_context(viewport=viewport)

    if config.SESSION_STATE_PATH.exists():
        import json

        state = json.loads(config.SESSION_STATE_PATH.read_text())
        if state.get("cookies"):
            context.add_cookies(state["cookies"])

    # Jangan pernah "pinjam" tab yang sedang dipakai untuk kerjaan lain
    # (mis. tab add.htm yang sedang diisi form) - itu akan menavigasi tab
    # tsb pergi dan menghilangkan progress. Pilih tab listing yang sudah
    # ada, atau bikin tab baru khusus untuk cek sesi.
    page = None
    for pg in context.pages:
        if pg.url.rstrip("/") == config.BIGSELLER_LISTING_URL.rstrip("/"):
            page = pg
            break
    if page is None:
        page = context.new_page()

    if viewport:
        page.set_viewport_size(viewport)
    page.set_default_timeout(config.DEFAULT_TIMEOUT_MS)
    page.goto(config.BIGSELLER_LISTING_URL)
    page.wait_for_load_state("networkidle")
    _accept_updated_terms_if_present(page)

    if is_logged_in(page):
        return context, page

    ok = login(page)
    if ok:
        context.storage_state(path=str(config.SESSION_STATE_PATH))
        print(f"[login] Sesi disimpan ke {config.SESSION_STATE_PATH}.")
    return context, page


def ensure_logged_in(browser, viewport=None):
    """Return (context, page) yang sudah login. Coba pakai sesi tersimpan
    dulu; kalau tidak ada/basi, jalankan login penuh (captcha manual) lalu
    simpan sesi baru supaya run berikutnya tidak perlu captcha lagi."""
    context, page = restore_session(browser, viewport=viewport)
    if page is not None:
        print(f"[login] Pakai sesi tersimpan dari {config.SESSION_STATE_PATH}, skip login manual.")
        return context, page

    context = browser.new_context(viewport=viewport)
    page = context.new_page()
    page.set_default_timeout(config.DEFAULT_TIMEOUT_MS)

    ok = login(page)
    if ok:
        save_session(context)
        print(f"[login] Sesi disimpan ke {config.SESSION_STATE_PATH} untuk dipakai ulang di run berikutnya.")

    return context, page
