import csv
from dataclasses import dataclass, field

from . import config


@dataclass
class VariantCombination:
    dimension1_name: str
    dimension1_value: str
    dimension2_name: str
    dimension2_value: str
    sku: str
    price: str
    stock: str


@dataclass
class Product:
    product_id: str
    name: str
    category: str
    description: str
    image_path: str
    store: str = ""
    weight_grams: int = 50
    variants: list = field(default_factory=list)

    @property
    def dimension_names(self):
        """Nama dimensi varian unik dalam urutan kemunculan, misal ['Warna', 'Ukuran']."""
        names = []
        for v in self.variants:
            for n in (v.dimension1_name, v.dimension2_name):
                if n and n not in names:
                    names.append(n)
        return names

    def dimension_values(self, dimension_name: str):
        """Nilai unik untuk satu nama dimensi, urut kemunculan."""
        values = []
        for v in self.variants:
            for n, val in (
                (v.dimension1_name, v.dimension1_value),
                (v.dimension2_name, v.dimension2_value),
            ):
                if n == dimension_name and val and val not in values:
                    values.append(val)
        return values


def load_products(products_csv=None, variants_csv=None):
    products_csv = products_csv or config.PRODUCTS_CSV
    variants_csv = variants_csv or config.VARIANTS_CSV

    products = {}
    with open(products_csv, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            pid = row["product_id"].strip()
            products[pid] = Product(
                product_id=pid,
                name=row["name"].strip(),
                category=row["category"].strip(),
                description=row["description"].strip(),
                image_path=row["image_path"].strip(),
                store=row.get("store", "").strip(),
                weight_grams=int(row["weight_grams"]) if row.get("weight_grams", "").strip() else 50,
            )

    with open(variants_csv, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            pid = row["product_id"].strip()
            if pid not in products:
                continue
            products[pid].variants.append(
                VariantCombination(
                    dimension1_name=row.get("dimension1_name", "").strip(),
                    dimension1_value=row.get("dimension1_value", "").strip(),
                    dimension2_name=row.get("dimension2_name", "").strip(),
                    dimension2_value=row.get("dimension2_value", "").strip(),
                    sku=row.get("sku", "").strip(),
                    price=row.get("price", "").strip(),
                    stock=row.get("stock", "").strip(),
                )
            )

    return list(products.values())
