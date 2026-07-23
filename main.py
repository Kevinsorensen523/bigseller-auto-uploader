"""Entry point lama, dipertahankan untuk kompatibilitas: `python main.py`
menjalankan mode CSV (data/products.csv + data/variants.csv), sama seperti
`bigseller-upload run-csv` setelah package ini diinstall."""

from bigseller_auto_uploader.main import run

if __name__ == "__main__":
    run()
