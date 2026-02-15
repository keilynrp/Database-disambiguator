"""CLI script to bulk-import an Excel product report into the database.

Usage (run from project root):
    python -m scripts.import_data [path_to_excel_file]

If no path is provided, it looks for the first .xlsx file in data/.
"""

import pandas as pd
import os
import sys

# Ensure project root is on sys.path so `backend` package resolves
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT_DIR)

from backend import models, database

COLUMN_MAPPING = {
    "Nombre del Producto": "product_name",
    "Clasificación": "classification",
    "Tipo de Producto": "product_type",
    "¿Posible vender en cantidad decimal?": "is_decimal_sellable",
    "¿Controlarás el stock del producto?": "control_stock",
    "Estado": "status",
    "Impuestos": "taxes",
    "Variante": "variant",
    "Código universal de producto": "product_code_universal_1",
    "Codigo universal": "product_code_universal_2",
    "Codigo universal del producto": "product_code_universal_3",
    "CODIGO UNIVERSAL DEL PRODRUCTO": "product_code_universal_4",
    "marca": "brand_lower",
    "Marca": "brand_capitalized",
    "modelo": "model",
    "GTIN": "gtin",
    "Motivo de GTIN": "gtin_reason",
    "Motivo de GTIN vacío": "gtin_empty_reason_1",
    "Motivo GTIN vacío": "gtin_empty_reason_2",
    "Motivo GTIN vacia": "gtin_empty_reason_3",
    "Motivo GTIN de producto": "gtin_product_reason",
    "motivo GTIN": "gtin_reason_lower",
    "Mtivo GTIN vacio": "gtin_empty_reason_typo",
    "EQUIMAPIENTO": "equipment",
    "MEDIDA": "measure",
    "TIPO DE UNION": "union_type",
    "¿permitirás ventas sin stock?": "allow_sales_without_stock",
    "Código de Barras": "barcode",
    "SKU": "sku",
    "Sucursales": "branches",
    "Fecha de creacion": "creation_date",
    "Estado Variante": "variant_status",
    "Clave de producto": "product_key",
    "Unidad de medida": "unit_of_measure",
}


def import_data(file_path: str):
    if not os.path.exists(file_path):
        print(f"File not found: {file_path}")
        return

    print(f"Reading Excel file: {file_path}")
    try:
        df = pd.read_excel(file_path)
    except Exception as e:
        print(f"Error reading Excel file: {e}")
        return

    df.columns = df.columns.str.strip()

    print("Initializing database...")
    models.Base.metadata.create_all(bind=database.engine)
    db = database.SessionLocal()

    print("Mapping data...")
    objects = []
    for _, row in df.iterrows():
        row_data = {}
        for excel_col, model_field in COLUMN_MAPPING.items():
            if excel_col in df.columns:
                val = row[excel_col]
            elif excel_col.strip() in df.columns:
                val = row[excel_col.strip()]
            else:
                continue

            if pd.isna(val):
                val = None
            else:
                val = str(val).strip()

            row_data[model_field] = val

        objects.append(models.RawProduct(**row_data))

        if len(objects) % 1000 == 0:
            print(f"  Prepared {len(objects)} rows...")

    print(f"Saving {len(objects)} rows to database...")
    try:
        db.bulk_save_objects(objects)
        db.commit()
        print("Import successful!")
    except Exception as e:
        print(f"Error saving to database: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    if len(sys.argv) > 1:
        path = sys.argv[1]
    else:
        data_dir = os.path.join(ROOT_DIR, "data")
        xlsx_files = [f for f in os.listdir(data_dir) if f.endswith(".xlsx")]
        if not xlsx_files:
            print("No .xlsx files found in data/. Pass a file path as argument.")
            sys.exit(1)
        path = os.path.join(data_dir, xlsx_files[0])
        print(f"Using: {path}")

    import_data(path)
