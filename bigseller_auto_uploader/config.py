import os
from pathlib import Path

from dotenv import load_dotenv

# PROJECT_DIR = folder tempat perintah dijalankan (project yang MEMAKAI package
# ini), bukan folder instalasi package. Override lewat env BIGSELLER_PROJECT_DIR
# kalau mau jalankan dari lokasi lain.
PROJECT_DIR = Path(os.environ.get("BIGSELLER_PROJECT_DIR", Path.cwd())).resolve()
load_dotenv(PROJECT_DIR / ".env")


def _get_bool(name: str, default: bool) -> bool:
    val = os.getenv(name)
    if val is None:
        return default
    return val.strip().lower() in ("1", "true", "yes", "on")


def _get_int(name: str, default: int) -> int:
    val = os.getenv(name)
    if val is None or val.strip() == "":
        return default
    return int(val)


BIGSELLER_USERNAME = os.getenv("BIGSELLER_USERNAME", "")
BIGSELLER_PASSWORD = os.getenv("BIGSELLER_PASSWORD", "")

BIGSELLER_LOGIN_URL = os.getenv("BIGSELLER_LOGIN_URL", "https://www.bigseller.com/web/login.htm")
BIGSELLER_LISTING_URL = os.getenv(
    "BIGSELLER_LISTING_URL",
    "https://www.bigseller.com/web/listing/shopee/active/index.htm?bsStatus=4",
)

HEADLESS = _get_bool("HEADLESS", True)
ACTION_DELAY_MS = _get_int("ACTION_DELAY_MS", 800)
DELAY_BETWEEN_PRODUCTS_SEC = _get_int("DELAY_BETWEEN_PRODUCTS_SEC", 5)
DEFAULT_TIMEOUT_MS = _get_int("DEFAULT_TIMEOUT_MS", 15000)

# BigSeller batasi video produk 30MB & video resolusi tinggi (mis. 2160x3840
# dari HP modern) gagal ter-upload tanpa error meski di bawah limit ukuran
# (lihat uploader.upload_video). VIDEO_MAX_SIZE_MB dikasih margin di bawah 30
# supaya masih aman setelah overhead container mp4.
VIDEO_AUTO_COMPRESS = _get_bool("VIDEO_AUTO_COMPRESS", True)
VIDEO_MAX_SIZE_MB = _get_int("VIDEO_MAX_SIZE_MB", 25)
VIDEO_MAX_DIMENSION = _get_int("VIDEO_MAX_DIMENSION", 1920)

DATA_DIR = PROJECT_DIR / "data"
LOGS_DIR = PROJECT_DIR / "logs"
PRODUCTS_CSV = DATA_DIR / "products.csv"
VARIANTS_CSV = DATA_DIR / "variants.csv"
OUTPUT_REPORT_CSV = PROJECT_DIR / "output_report.csv"
SESSION_STATE_PATH = PROJECT_DIR / ".playwright_session.json"

JOBS_DIR = PROJECT_DIR / "jobs"
JOBS_PENDING_DIR = JOBS_DIR / "pending"
JOBS_DONE_DIR = JOBS_DIR / "done"
JOBS_FAILED_DIR = JOBS_DIR / "failed"
JOBS_SKIPPED_DIR = JOBS_DIR / "skipped"

LOGS_DIR.mkdir(exist_ok=True)


def has_credentials() -> bool:
    return bool(BIGSELLER_USERNAME.strip()) and bool(BIGSELLER_PASSWORD.strip())
