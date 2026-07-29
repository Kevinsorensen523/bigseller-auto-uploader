import json
import shutil
import subprocess
from pathlib import Path

from . import config


def ffmpeg_available() -> bool:
    return shutil.which("ffmpeg") is not None and shutil.which("ffprobe") is not None


def _probe_video(path: Path) -> tuple[int, int]:
    """Return (width, height) of the first video stream."""
    result = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-select_streams",
            "v:0",
            "-show_entries",
            "stream=width,height",
            "-of",
            "json",
            str(path),
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    stream = json.loads(result.stdout)["streams"][0]
    return int(stream["width"]), int(stream["height"])


def needs_compression(path: Path) -> bool:
    size_mb = path.stat().st_size / (1024 * 1024)
    if size_mb > config.VIDEO_MAX_SIZE_MB:
        return True
    width, height = _probe_video(path)
    return max(width, height) > config.VIDEO_MAX_DIMENSION


def compress_video(path: Path) -> Path:
    """Downscale (cap sisi terpanjang ke VIDEO_MAX_DIMENSION) & re-encode
    dengan CRF untuk mengecilkan ukuran file. Overwrite file asli di tempat
    (nama file tetap sama) supaya job.json tidak perlu diubah."""
    tmp_output = path.with_name(f"{path.stem}.compressed.mp4")

    max_dim = config.VIDEO_MAX_DIMENSION
    scale_filter = (
        f"scale=w=min(iw\\,{max_dim}):h=min(ih\\,{max_dim}):force_original_aspect_ratio=decrease,"
        "scale=trunc(iw/2)*2:trunc(ih/2)*2"
    )

    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-i",
            str(path),
            "-vf",
            scale_filter,
            "-c:v",
            "libx264",
            "-crf",
            "26",
            "-preset",
            "veryfast",
            "-c:a",
            "aac",
            "-b:a",
            "128k",
            "-movflags",
            "+faststart",
            str(tmp_output),
        ],
        capture_output=True,
        check=True,
    )

    tmp_output.replace(path)
    return path


def maybe_compress_video(path: Path) -> tuple[Path, bool, str | None]:
    """Kompres video di tempat kalau perlu (terlalu besar atau resolusi
    terlalu tinggi). Return (path, was_compressed, error_message).
    Kalau ffmpeg tidak ada atau kompresi gagal, video asli dibiarkan apa
    adanya dan error_message diisi supaya bisa ditampilkan ke user."""
    if not config.VIDEO_AUTO_COMPRESS:
        return path, False, None

    if not ffmpeg_available():
        return path, False, "ffmpeg tidak ditemukan di sistem - video tidak dikompres otomatis."

    try:
        if not needs_compression(path):
            return path, False, None
        compress_video(path)
        return path, True, None
    except subprocess.CalledProcessError as e:
        return path, False, f"Gagal kompres video: {e}"
