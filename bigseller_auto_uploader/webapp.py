import json
import uuid

from flask import Flask, flash, redirect, render_template, request, send_file, url_for

from . import config
from .variant_file import build_template_xlsx, parse_variant_file

app = Flask(__name__)
app.secret_key = "bigseller-local-ui"  # UI ini cuma jalan di localhost, tanpa auth


def _ensure_job_dirs():
    for d in (config.JOBS_PENDING_DIR, config.JOBS_DONE_DIR, config.JOBS_FAILED_DIR):
        d.mkdir(parents=True, exist_ok=True)


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
    video_file = request.files.get("video")
    if video_file and video_file.filename:
        video_file.save(job_dir / video_file.filename)
        video_filename = video_file.filename

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
        f"Jalankan `bigseller-upload run-queue` di terminal untuk proses upload."
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


@app.route("/queue")
def queue():
    _ensure_job_dirs()
    jobs = []
    for job_dir in sorted(config.JOBS_PENDING_DIR.glob("*")):
        job_file = job_dir / "job.json"
        if job_file.exists():
            jobs.append(json.loads(job_file.read_text(encoding="utf-8")))
    return render_template("queue.html", jobs=jobs)


def main():
    _ensure_job_dirs()
    print(f"Web UI jalan di http://127.0.0.1:5151  (project: {config.PROJECT_DIR})")
    app.run(host="127.0.0.1", port=5151, debug=False)


if __name__ == "__main__":
    main()
