import json
import shutil
import threading
import uuid

from flask import Flask, abort, flash, jsonify, redirect, render_template, request, send_file, url_for

from . import config
from . import queue_runner
from .scrape_categories import load_categories
from .scrape_stores import load_stores
from .variant_file import build_template_xlsx, parse_variant_file
from .video_compress import maybe_compress_video

app = Flask(__name__)
app.secret_key = "bigseller-local-ui"  # UI ini cuma jalan di localhost, tanpa auth

_ensure_job_dirs = queue_runner.ensure_job_dirs

STATUS_DIRS = {
    "pending": config.JOBS_PENDING_DIR,
    "done": config.JOBS_DONE_DIR,
    "failed": config.JOBS_FAILED_DIR,
    "skipped": config.JOBS_SKIPPED_DIR,
}

# State proses "Jalankan Sekarang" dari web UI - run-queue Playwright jalan di
# thread terpisah (satu proses browser sekaligus) supaya request HTTP tidak
# ngeblock, log-nya di-poll oleh halaman queue lewat /run/status.
_run_lock = threading.Lock()
_run_state = {"running": False, "logs": []}


def _run_log(message: str) -> None:
    with _run_lock:
        _run_state["logs"].append(message)


def _run_in_background(publish: bool) -> None:
    with _run_lock:
        _run_state["running"] = True
        _run_state["logs"] = []
    try:
        queue_runner.run_queue(publish=publish, log=_run_log)
    except Exception as e:  # tampilkan error tak terduga (mis. crash Playwright) di log UI
        _run_log(f"Error tak terduga: {e}")
    finally:
        with _run_lock:
            _run_state["running"] = False


def _load_jobs(status: str) -> list[dict]:
    jobs = []
    for job_dir in sorted(STATUS_DIRS[status].glob("*")):
        job_file = job_dir / "job.json"
        if job_file.exists():
            job = json.loads(job_file.read_text(encoding="utf-8"))
            job["_status"] = status
            jobs.append(job)
    return jobs


@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")


@app.route("/submit", methods=["POST"])
def submit():
    _ensure_job_dirs()
    job_id = uuid.uuid4().hex[:10]
    job_dir = config.JOBS_PENDING_DIR / job_id
    job_dir.mkdir(parents=True, exist_ok=True)

    images = []
    for f in request.files.getlist("images"):
        if f and f.filename:
            f.save(job_dir / f.filename)
            images.append(f.filename)

    video_filename = None
    video_warning = None
    video_file = request.files.get("video")
    if video_file and video_file.filename:
        video_path = job_dir / video_file.filename
        video_file.save(video_path)
        _, compressed, video_warning = maybe_compress_video(video_path)
        video_filename = video_file.filename
        if compressed:
            flash(f"Video \"{video_filename}\" otomatis dikompres (terlalu besar/resolusi kegedean).")
        elif video_warning:
            flash(video_warning)

    variants_file = request.files.get("variants_file")
    if variants_file and variants_file.filename:
        # Excel/CSV yang diupload menang - baris yang diketik manual di form diabaikan.
        variants = parse_variant_file(variants_file)
    else:
        values = request.form.getlist("variant_value")
        skus = request.form.getlist("variant_sku")
        prices = request.form.getlist("variant_price")
        stocks = request.form.getlist("variant_stock")
        variants = []
        for value, sku, price, stock in zip(values, skus, prices, stocks):
            if value.strip():
                variants.append(
                    {
                        "value": value.strip(),
                        "sku": sku.strip(),
                        "price": int(price or 0),
                        "stock": int(stock or 0),
                    }
                )

    job = {
        "job_id": job_id,
        "store_name": request.form.get("store_name", "").strip(),
        "category_keyword": request.form.get("category_keyword", "").strip(),
        "category_match_text": request.form.get("category_match_text", "").strip() or None,
        "product_name": request.form.get("product_name", "").strip(),
        "description": request.form.get("description", "").strip(),
        "weight_grams": int(request.form.get("weight_grams") or 0),
        "brand": request.form.get("brand", "Tidak ada merek").strip() or "Tidak ada merek",
        "images": images,
        "video": video_filename,
        "dimension_name": request.form.get("dimension_name", "").strip(),
        "variants": variants,
        "single_price": int(request.form.get("single_price") or 0) if not variants else None,
        "single_stock": int(request.form.get("single_stock") or 0) if not variants else None,
        "shipping_all": True,
        "publish": False,
    }
    (job_dir / "job.json").write_text(json.dumps(job, indent=2, ensure_ascii=False), encoding="utf-8")

    flash(
        f"Job \"{job['product_name']}\" tersimpan di antrian ({job_id}). "
        f"Klik \"Jalankan Sekarang\" di halaman antrian untuk proses upload."
    )
    return redirect(url_for("queue"))


@app.route("/variant-template.xlsx")
def variant_template():
    buffer = build_template_xlsx()
    return send_file(
        buffer,
        as_attachment=True,
        download_name="template-varian.xlsx",
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


@app.route("/categories.json")
def categories_json():
    return {"categories": load_categories()}


@app.route("/stores.json")
def stores_json():
    return {"stores": load_stores()}


@app.route("/queue")
def queue():
    _ensure_job_dirs()
    jobs_by_status = {status: _load_jobs(status) for status in STATUS_DIRS}
    counts = {status: len(jobs) for status, jobs in jobs_by_status.items()}
    with _run_lock:
        run_state = {"running": _run_state["running"], "logs": list(_run_state["logs"])}
    return render_template("queue.html", jobs_by_status=jobs_by_status, counts=counts, run_state=run_state)


@app.route("/jobs/<status>/<job_id>/<action>", methods=["POST"])
def job_action(status, job_id, action):
    if status not in STATUS_DIRS:
        abort(404)
    job_dir = STATUS_DIRS[status] / job_id
    if not job_dir.is_dir():
        abort(404)

    if action == "delete":
        shutil.rmtree(job_dir)
        flash(f"Job {job_id} dihapus.")
    elif action in ("done", "skip", "restore"):
        target_status = {"done": "done", "skip": "skipped", "restore": "pending"}[action]
        target_dir = STATUS_DIRS[target_status]
        target_dir.mkdir(parents=True, exist_ok=True)
        shutil.move(str(job_dir), str(target_dir / job_id))
        flash(f"Job {job_id} dipindah ke {target_status}.")
    else:
        abort(404)

    return redirect(url_for("queue"))


@app.route("/run/start", methods=["POST"])
def run_start():
    with _run_lock:
        already_running = _run_state["running"]
    if already_running:
        flash("Proses upload masih jalan, tunggu sampai selesai.")
        return redirect(url_for("queue"))

    if not config.has_credentials():
        flash("BIGSELLER_USERNAME/BIGSELLER_PASSWORD belum diisi di .env.")
        return redirect(url_for("queue"))

    publish = request.form.get("publish") == "on"
    threading.Thread(target=_run_in_background, args=(publish,), daemon=True).start()
    flash(f"Mulai memproses antrian ({'Save & Publish' if publish else 'Save to Draft'})...")
    return redirect(url_for("queue"))


@app.route("/run/status")
def run_status():
    _ensure_job_dirs()
    with _run_lock:
        state = {"running": _run_state["running"], "logs": list(_run_state["logs"])}
    state["counts"] = {status: len(list(STATUS_DIRS[status].glob("*"))) for status in STATUS_DIRS}
    return jsonify(state)


def main():
    _ensure_job_dirs()
    print(f"Web UI jalan di http://127.0.0.1:5151  (project: {config.PROJECT_DIR})")
    app.run(host="127.0.0.1", port=5151, debug=False)


if __name__ == "__main__":
    main()
