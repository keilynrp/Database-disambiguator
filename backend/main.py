from fastapi import FastAPI, Depends, UploadFile, File, HTTPException, Query
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List
import pandas as pd
import io
import re
import json
from datetime import datetime

from backend import models, schemas, database, enrichment_worker
from backend.datasource_analyzer import DataSourceAnalyzer
from sqlalchemy import inspect, text, func

models.Base.metadata.create_all(bind=database.engine)

# Lightweight migration: add enrichment columns
with database.engine.connect() as conn:
    inspector = inspect(database.engine)
    if "harmonization_logs" in inspector.get_table_names():
        columns = [col["name"] for col in inspector.get_columns("harmonization_logs")]
        if "reverted" not in columns:
            conn.execute(text("ALTER TABLE harmonization_logs ADD COLUMN reverted BOOLEAN DEFAULT 0"))
            
    if "raw_products" in inspector.get_table_names():
        columns = [col["name"] for col in inspector.get_columns("raw_products")]
        if "enrichment_doi" not in columns:
            conn.execute(text("ALTER TABLE raw_products ADD COLUMN enrichment_doi VARCHAR"))
            conn.execute(text("ALTER TABLE raw_products ADD COLUMN enrichment_citation_count INTEGER DEFAULT 0"))
            conn.execute(text("ALTER TABLE raw_products ADD COLUMN enrichment_concepts TEXT"))
            conn.execute(text("ALTER TABLE raw_products ADD COLUMN enrichment_source VARCHAR"))
            conn.execute(text("ALTER TABLE raw_products ADD COLUMN enrichment_status VARCHAR DEFAULT 'none'"))
            conn.commit()

app = FastAPI()

import asyncio

@app.on_event("startup")
async def start_background_workers():
    # Helper to yield DB sessions for background worker safely
    def get_db_gen():
        while True:
            db = database.SessionLocal()
            try:
                yield db
            finally:
                pass # The worker will close after each loop iteration
    
    # We create the task and let it run
    asyncio.create_task(enrichment_worker.background_enrichment_worker(get_db_gen()))


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Allow all origins for dev
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_db():
    db = database.SessionLocal()
    try:
        yield db
    finally:
        db.close()

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
    "CODIGO UNIVERSAL DEL PRODRUCTO ": "product_code_universal_4", 
    "marca": "brand_lower",
    "Marca": "brand_capitalized",
    "modelo": "model",
    "GTIN": "gtin",
    "Motivo de GTIN": "gtin_reason",
    "Motivo de GTIN vacío": "gtin_empty_reason_1",
    "Motivo GTIN vacío ": "gtin_empty_reason_2",
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
    "Unidad de medida": "unit_of_measure"
}

@app.post("/upload")
async def upload_file(file: UploadFile = File(...), db: Session = Depends(get_db)):
    filename = file.filename.lower()
    if not (filename.endswith(".xlsx") or filename.endswith(".csv")):
        raise HTTPException(status_code=400, detail="Invalid file format. Only .xlsx and .csv allowed.")

    contents = await file.read()
    
    if filename.endswith(".xlsx"):
        df = pd.read_excel(io.BytesIO(contents))
    else:
        # Detect delimiter or just assume comma with fallback? 
        # Usually Excel exports use semicolons in some locales, but CSV implies Comma.
        try:
            df = pd.read_csv(io.BytesIO(contents), encoding='utf-8')
        except UnicodeDecodeError:
            df = pd.read_csv(io.BytesIO(contents), encoding='latin-1')

    df.columns = df.columns.str.strip()

    # Track which columns were matched vs ignored
    # We use stripped keys to be more resilient to surrounding whitespace in headers
    stripped_mapping = {k.strip(): v for k, v in COLUMN_MAPPING.items()}
    matched_columns = [col for col in df.columns if col in stripped_mapping]
    unmatched_columns = [col for col in df.columns if col not in stripped_mapping]

    objects = []
    for _, row in df.iterrows():
        row_data = {}
        for excel_col in matched_columns:
            model_field = stripped_mapping[excel_col]
            val = row[excel_col]
            if pd.isna(val):
                val = None
            else:
                val = str(val)
            row_data[model_field] = val

        objects.append(models.RawProduct(**row_data))

    db.bulk_save_objects(objects)
    db.commit()

    return {
        "message": f"Successfully imported {len(objects)} rows",
        "total_rows": len(objects),
        "matched_columns": matched_columns,
        "unmatched_columns": unmatched_columns,
    }


import shutil
import tempfile
import os

@app.post("/analyze")
async def analyze_datasource(file: UploadFile = File(...)):
    """
    Analyzes the structure (columns, keys, tags, predicates) of a given file.
    Supports CSV, Excel, JSON, XML, Parquet, RDF, Logs, etc.
    """
    # Create a temporary file preserving the extension since DataSourceAnalyzer relies on it
    ext = os.path.splitext(file.filename)[1].lower()
    if not ext:
        raise HTTPException(status_code=400, detail="File must have an extension to be analyzed")

    fd, temp_path = tempfile.mkstemp(suffix=ext)
    os.close(fd) # Close file descriptor so we can open it via shutil

    try:
        with open(temp_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Run analyzer
        structure = DataSourceAnalyzer.analyze(temp_path)
        
        return {
            "filename": file.filename,
            "format": ext.strip("."),
            "structure": structure,
            "count": len(structure)
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error analyzing file: {str(e)}")
    finally:
        # Clean up
        if os.path.exists(temp_path):
            os.remove(temp_path)


from sqlalchemy import or_, func, update

@app.get("/products", response_model=List[schemas.Product])
def get_products(skip: int = 0, limit: int = 100, search: str = None, db: Session = Depends(get_db)):
    query = db.query(models.RawProduct)
    
    if search:
        search_filter = f"%{search}%"
        query = query.filter(
            or_(
                models.RawProduct.product_name.ilike(search_filter),
                models.RawProduct.brand_capitalized.ilike(search_filter),
                models.RawProduct.model.ilike(search_filter),
                models.RawProduct.sku.ilike(search_filter)
            )
        )
    
    products = query.offset(skip).limit(limit).all()
    return products


@app.get("/products/grouped")
def get_products_grouped(skip: int = 0, limit: int = 100, search: str = None, db: Session = Depends(get_db)):
    """
    Group products by product_name and show all variants for each product.
    Similar to OpenRefine's clustering/faceting feature.
    """
    # Subquery to count variants per product_name
    variant_counts = db.query(
        models.RawProduct.product_name,
        func.count(models.RawProduct.id).label("variant_count")
    ).filter(
        models.RawProduct.product_name != None
    ).group_by(models.RawProduct.product_name).subquery()
    
    # Main query
    query = db.query(
        models.RawProduct.product_name,
        variant_counts.c.variant_count
    ).join(
        variant_counts,
        models.RawProduct.product_name == variant_counts.c.product_name
    ).group_by(
        models.RawProduct.product_name,
        variant_counts.c.variant_count
    )
    
    if search:
        search_filter = f"%{search}%"
        query = query.filter(models.RawProduct.product_name.ilike(search_filter))
    
    # Order by variant count descending (products with most variants first)
    query = query.order_by(variant_counts.c.variant_count.desc())
    
    # Paginate
    product_groups = query.offset(skip).limit(limit).all()
    
    # For each product name, fetch all its variants
    result = []
    for product_name, variant_count in product_groups:
        variants = db.query(models.RawProduct).filter(
            models.RawProduct.product_name == product_name
        ).all()
        
        result.append({
            "product_name": product_name,
            "variant_count": variant_count,
            "variants": variants
        })
    
    return result


@app.put("/products/{product_id}", response_model=schemas.Product)
def update_product(product_id: int, payload: schemas.ProductBase, db: Session = Depends(get_db)):
    product = db.query(models.RawProduct).filter(models.RawProduct.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(product, field, value)

    db.commit()
    db.refresh(product)
    return product




@app.delete("/products/all")
def purge_all_products(include_rules: str = Query("false"), db: Session = Depends(get_db)):
    # Convert string to boolean
    include_rules_bool = include_rules.lower() in ("true", "1", "yes")
    
    product_count = db.query(func.count(models.RawProduct.id)).scalar() or 0
    db.query(models.RawProduct).delete()

    rules_count = 0
    if include_rules_bool:
        rules_count = db.query(func.count(models.NormalizationRule.id)).scalar() or 0
        db.query(models.NormalizationRule).delete()

    db.commit()
    return {
        "message": "Database purged successfully",
        "products_deleted": product_count,
        "rules_deleted": rules_count,
    }


@app.delete("/products/{product_id}")
def delete_product(product_id: int, db: Session = Depends(get_db)):
    product = db.query(models.RawProduct).filter(models.RawProduct.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    db.delete(product)
    db.commit()
    return {"message": "Product deleted", "id": product_id}


@app.post("/enrich/row/{product_id}", response_model=schemas.Product)
def enrich_single_product(product_id: int, db: Session = Depends(get_db)):
    """Enriches a single row manually (e.g. from a UI click)"""
    product = db.query(models.RawProduct).filter(models.RawProduct.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    # Force single enrichment fetch
    enriched = enrichment_worker.enrich_single_record(db, product)
    return enriched

@app.post("/enrich/bulk")
def enrich_bulk_queue(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """Queues missing records for background enrichment"""
    count = enrichment_worker.trigger_enrichment_bulk(db, skip=skip, limit=limit)
    return {"message": "Bulk queue triggered", "queued_records": count}



from thefuzz import process, fuzz

@app.get("/disambiguate/{field}")
def disambiguate_field(field: str, threshold: int = 80, db: Session = Depends(get_db)):
    if field not in AUTHORITY_FIELDS:
        raise HTTPException(status_code=400, detail=f"Field {field} not supported for disambiguation")

    groups = _build_disambig_groups(field, threshold, db)
    return {"groups": groups, "total_groups": len(groups)}

@app.get("/stats")
def get_stats(db: Session = Depends(get_db)):
    total_products = db.query(func.count(models.RawProduct.id)).scalar() or 0

    unique_brands = db.query(func.count(func.distinct(models.RawProduct.brand_capitalized))).filter(
        models.RawProduct.brand_capitalized != None
    ).scalar() or 0

    unique_models = db.query(func.count(func.distinct(models.RawProduct.model))).filter(
        models.RawProduct.model != None
    ).scalar() or 0

    unique_product_types = db.query(func.count(func.distinct(models.RawProduct.product_type))).filter(
        models.RawProduct.product_type != None
    ).scalar() or 0

    # Validation status breakdown
    validation_rows = db.query(
        models.RawProduct.validation_status,
        func.count(models.RawProduct.id)
    ).group_by(models.RawProduct.validation_status).all()
    validation_status = {row[0] or "pending": row[1] for row in validation_rows}

    # Identifier coverage
    with_sku = db.query(func.count(models.RawProduct.id)).filter(
        models.RawProduct.sku != None, models.RawProduct.sku != ""
    ).scalar() or 0
    with_barcode = db.query(func.count(models.RawProduct.id)).filter(
        models.RawProduct.barcode != None, models.RawProduct.barcode != ""
    ).scalar() or 0
    with_gtin = db.query(func.count(models.RawProduct.id)).filter(
        models.RawProduct.gtin != None, models.RawProduct.gtin != ""
    ).scalar() or 0

    # Top brands (top 10)
    top_brands = db.query(
        models.RawProduct.brand_capitalized,
        func.count(models.RawProduct.id).label("count")
    ).filter(
        models.RawProduct.brand_capitalized != None
    ).group_by(
        models.RawProduct.brand_capitalized
    ).order_by(func.count(models.RawProduct.id).desc()).limit(10).all()

    # Product type distribution
    type_distribution = db.query(
        models.RawProduct.product_type,
        func.count(models.RawProduct.id).label("count")
    ).filter(
        models.RawProduct.product_type != None
    ).group_by(
        models.RawProduct.product_type
    ).order_by(func.count(models.RawProduct.id).desc()).limit(10).all()

    # Status distribution
    status_distribution = db.query(
        models.RawProduct.status,
        func.count(models.RawProduct.id).label("count")
    ).filter(
        models.RawProduct.status != None
    ).group_by(
        models.RawProduct.status
    ).order_by(func.count(models.RawProduct.id).desc()).all()

    # Classification distribution
    classification_distribution = db.query(
        models.RawProduct.classification,
        func.count(models.RawProduct.id).label("count")
    ).filter(
        models.RawProduct.classification != None
    ).group_by(
        models.RawProduct.classification
    ).order_by(func.count(models.RawProduct.id).desc()).all()

    
    # Variant statistics
    products_with_variants = db.query(func.count(models.RawProduct.id)).filter(
        models.RawProduct.variant != None,
        models.RawProduct.variant != ""
    ).scalar() or 0
    
    # Count unique product names that have variants
    unique_products_with_variants = db.query(
        func.count(func.distinct(models.RawProduct.product_name))
    ).filter(
        models.RawProduct.variant != None,
        models.RawProduct.variant != "",
        models.RawProduct.product_name != None
    ).scalar() or 0

    return {
        "total_products": total_products,
        "unique_brands": unique_brands,
        "unique_models": unique_models,
        "unique_product_types": unique_product_types,
        "products_with_variants": products_with_variants,
        "unique_products_with_variants": unique_products_with_variants,
        "validation_status": validation_status,
        "identifier_coverage": {
            "with_sku": with_sku,
            "with_barcode": with_barcode,
            "with_gtin": with_gtin,
            "total": total_products,
        },
        "top_brands": [{"name": b[0], "count": b[1]} for b in top_brands],
        "type_distribution": [{"name": t[0], "count": t[1]} for t in type_distribution],
        "classification_distribution": [{"name": c[0], "count": c[1]} for c in classification_distribution],
        "status_distribution": [{"name": s[0], "count": s[1]} for s in status_distribution],
    }


@app.get("/brands")
def get_all_brands(db: Session = Depends(get_db)):
    brands = db.query(
        models.RawProduct.brand_capitalized,
        func.count(models.RawProduct.id).label("count")
    ).filter(
        models.RawProduct.brand_capitalized != None
    ).group_by(
        models.RawProduct.brand_capitalized
    ).order_by(func.count(models.RawProduct.id).desc()).all()
    
    return [{"name": b[0], "count": b[1]} for b in brands]


@app.get("/product-types")
def get_all_product_types(db: Session = Depends(get_db)):
    types = db.query(
        models.RawProduct.product_type,
        func.count(models.RawProduct.id).label("count")
    ).filter(
        models.RawProduct.product_type != None
    ).group_by(
        models.RawProduct.product_type
    ).order_by(func.count(models.RawProduct.id).desc()).all()
    
    return [{"name": t[0], "count": t[1]} for t in types]


@app.get("/classifications")
def get_all_classifications(db: Session = Depends(get_db)):
    classes = db.query(
        models.RawProduct.classification,
        func.count(models.RawProduct.id).label("count")
    ).filter(
        models.RawProduct.classification != None
    ).group_by(
        models.RawProduct.classification
    ).order_by(func.count(models.RawProduct.id).desc()).all()
    
    return [{"name": c[0], "count": c[1]} for c in classes]


# Reverse mapping: model_field -> original excel header
EXPORT_COLUMN_MAPPING = {v: k.strip() for k, v in COLUMN_MAPPING.items()}

# Fix typos in export column headers
EXPORT_COLUMN_MAPPING.update({
    "equipment": "EQUIPAMIENTO",
    "gtin_empty_reason_typo": "Motivo GTIN vacio",
    "product_code_universal_4": "CODIGO UNIVERSAL DEL PRODUCTO",
})

@app.get("/export")
def export_products(search: str = None, db: Session = Depends(get_db)):
    query = db.query(models.RawProduct)

    if search:
        search_filter = f"%{search}%"
        query = query.filter(
            or_(
                models.RawProduct.product_name.ilike(search_filter),
                models.RawProduct.brand_capitalized.ilike(search_filter),
                models.RawProduct.model.ilike(search_filter),
                models.RawProduct.sku.ilike(search_filter)
            )
        )

    products = query.all()

    rows = []
    for p in products:
        row = {}
        for model_field, excel_col in EXPORT_COLUMN_MAPPING.items():
            row[excel_col] = getattr(p, model_field, None)
        rows.append(row)

    df = pd.DataFrame(rows)

    # Preserve original column order
    ordered_cols = [k.strip() for k in COLUMN_MAPPING.keys()]
    existing_cols = [c for c in ordered_cols if c in df.columns]
    df = df[existing_cols]

    output = io.BytesIO()
    df.to_excel(output, index=False, engine="openpyxl")
    output.seek(0)

    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=products_export.xlsx"}
    )


AUTHORITY_FIELDS = ["brand_capitalized", "product_name", "model", "product_type"]


def _build_disambig_groups(field: str, threshold: int, db: Session):
    """Shared disambiguation logic reused by /disambiguate and /authority."""
    column = getattr(models.RawProduct, field)
    values = db.query(column).distinct().filter(column != None).all()
    values = [v[0] for v in values if v[0]]
    values.sort(key=len, reverse=True)

    groups = []
    processed = set()

    for val in values:
        if val in processed:
            continue
        matches = process.extract(val, values, scorer=fuzz.token_sort_ratio, limit=50)
        group_members = [m[0] for m in matches if m[1] >= threshold]

        if len(group_members) > 1:
            groups.append({
                "main": val,
                "variations": group_members,
                "count": len(group_members),
            })
            for g in group_members:
                processed.add(g)
        else:
            processed.add(val)

    return groups


@app.get("/rules", response_model=List[schemas.Rule])
def get_rules(field_name: str = None, db: Session = Depends(get_db)):
    query = db.query(models.NormalizationRule)
    if field_name:
        query = query.filter(models.NormalizationRule.field_name == field_name)
    return query.order_by(models.NormalizationRule.id.desc()).all()


@app.post("/rules/bulk")
def create_rules_bulk(payload: schemas.BulkRuleCreate, db: Session = Depends(get_db)):
    # Delete existing rules for the same field + canonical so we can re-save cleanly
    for var in payload.variations:
        if var == payload.canonical_value:
            continue
        existing = db.query(models.NormalizationRule).filter(
            models.NormalizationRule.field_name == payload.field_name,
            models.NormalizationRule.original_value == var,
        ).first()
        if existing:
            existing.normalized_value = payload.canonical_value
        else:
            db.add(models.NormalizationRule(
                field_name=payload.field_name,
                original_value=var,
                normalized_value=payload.canonical_value,
            ))
    db.commit()
    return {"message": f"Rules saved for '{payload.canonical_value}'", "variations": len(payload.variations) - 1}


@app.delete("/rules/{rule_id}")
def delete_rule(rule_id: int, db: Session = Depends(get_db)):
    rule = db.query(models.NormalizationRule).filter(models.NormalizationRule.id == rule_id).first()
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    db.delete(rule)
    db.commit()
    return {"message": "Rule deleted"}


@app.post("/rules/apply")
def apply_rules(field_name: str = None, db: Session = Depends(get_db)):
    query = db.query(models.NormalizationRule)
    if field_name:
        query = query.filter(models.NormalizationRule.field_name == field_name)
    rules = query.all()

    total_updated = 0
    for rule in rules:
        if rule.field_name not in AUTHORITY_FIELDS:
            continue
        column = getattr(models.RawProduct, rule.field_name)

        if rule.is_regex:
            products = db.query(models.RawProduct).filter(column != None).all()
            for p in products:
                original = getattr(p, rule.field_name)
                if original:
                    try:
                        new_val = re.sub(rule.original_value, rule.normalized_value, original)
                        if new_val != original:
                            setattr(p, rule.field_name, new_val)
                            total_updated += 1
                    except re.error:
                        pass
        else:
            result = db.execute(
                update(models.RawProduct)
                .where(column == rule.original_value)
                .values({rule.field_name: rule.normalized_value})
            )
            total_updated += result.rowcount

    db.commit()
    return {
        "message": f"Applied {len(rules)} rules",
        "rules_applied": len(rules),
        "records_updated": total_updated,
    }


@app.get("/authority/{field}")
def get_authority_view(field: str, threshold: int = 80, db: Session = Depends(get_db)):
    if field not in AUTHORITY_FIELDS:
        raise HTTPException(status_code=400, detail=f"Field '{field}' not supported")

    groups = _build_disambig_groups(field, threshold, db)

    # Fetch existing rules for this field
    rules = db.query(models.NormalizationRule).filter(
        models.NormalizationRule.field_name == field
    ).all()
    rules_by_original = {r.original_value: r.normalized_value for r in rules}

    # Annotate groups with rule status
    annotated = []
    for g in groups:
        resolved_to = None
        has_rules = False
        for var in g["variations"]:
            if var in rules_by_original:
                has_rules = True
                resolved_to = rules_by_original[var]
                break
        annotated.append({
            **g,
            "has_rules": has_rules,
            "resolved_to": resolved_to,
        })

    total_rules = db.query(func.count(models.NormalizationRule.id)).filter(
        models.NormalizationRule.field_name == field
    ).scalar() or 0

    return {
        "groups": annotated,
        "total_groups": len(annotated),
        "total_rules": total_rules,
        "pending_groups": sum(1 for g in annotated if not g["has_rules"]),
    }



# ── Harmonization Pipeline ──────────────────────────────────────────────

HARMONIZATION_STEPS = [
    {"step_id": "consolidate_brands",   "name": "Consolidate Brand Columns",          "description": "Merge brand_lower into brand_capitalized when empty and apply brand normalization rules.", "order": 1},
    {"step_id": "clean_product_names",  "name": "Clean Product Names",                "description": "Remove double spaces, trim whitespace, and normalize special characters.",                "order": 2},
    {"step_id": "standardize_volumes",  "name": "Standardize Volume/Unit Variants",   "description": "Normalize volume formats (250ML → 250 mL, 1L → 1 L, 500gr → 500 g).",                  "order": 3},
    {"step_id": "consolidate_gtin",     "name": "Consolidate GTIN Columns",           "description": "Merge 4 product code columns and 7 GTIN reason fields into single authoritative values.","order": 4},
    {"step_id": "fix_export_typos",     "name": "Fix Export Column Name Typos",       "description": "Correct EQUIMAPIENTO → EQUIPAMIENTO, PRODRUCTO → PRODUCTO in export headers.",           "order": 5},
]

VOLUME_PATTERNS = [
    (r'(\d+)\s*(?:ML|Ml|ml)', r'\1 mL'),
    (r'(\d+(?:\.\d+)?)\s*(?:LT|Lt|lt|lts|LTS|Lts)\b', r'\1 L'),
    (r'(\d+(?:\.\d+)?)\s*[Ll]\b(?![\w])', r'\1 L'),
    (r'(\d+(?:\.\d+)?)\s*(?:KG|Kg|kg|kgs|KGS)\b', r'\1 kg'),
    (r'(\d+)\s*(?:GR|Gr|gr|grs|GRS)\b', r'\1 g'),
    (r'(\d+(?:\.\d+)?)\s*(?:CM|Cm|cm)\b', r'\1 cm'),
    (r'(\d+(?:\.\d+)?)\s*(?:MT|Mt|mt|mts|MTS)\b', r'\1 m'),
]

EXPORT_COLUMN_CORRECTIONS = {
    "equipment": "EQUIPAMIENTO",
    "gtin_empty_reason_typo": "Motivo GTIN vacio",
    "product_code_universal_4": "CODIGO UNIVERSAL DEL PRODUCTO",
}


def _step_consolidate_brands(db: Session, preview_only: bool):
    changes = []
    products = db.query(models.RawProduct).all()

    # Load existing brand normalization rules
    brand_rules = db.query(models.NormalizationRule).filter(
        models.NormalizationRule.field_name == "brand_capitalized",
        models.NormalizationRule.is_regex == False,
    ).all()
    brand_map = {r.original_value: r.normalized_value for r in brand_rules}

    for p in products:
        new_brand = p.brand_capitalized

        if not new_brand or not new_brand.strip():
            if p.brand_lower and p.brand_lower.strip():
                new_brand = p.brand_lower.strip()
            else:
                continue

        new_brand = new_brand.strip()

        # Apply normalization rules
        if new_brand in brand_map:
            new_brand = brand_map[new_brand]

        if new_brand != p.brand_capitalized:
            changes.append({
                "record_id": p.id,
                "field": "brand_capitalized",
                "old_value": p.brand_capitalized,
                "new_value": new_brand,
            })
            if not preview_only:
                p.brand_capitalized = new_brand

    if not preview_only:
        db.commit()
    return changes


def _step_clean_product_names(db: Session, preview_only: bool):
    changes = []
    products = db.query(models.RawProduct).filter(
        models.RawProduct.product_name != None
    ).all()

    for p in products:
        original = p.product_name
        if not original:
            continue

        cleaned = original
        cleaned = cleaned.replace('\u00a0', ' ')
        cleaned = cleaned.replace('\t', ' ')
        cleaned = re.sub(r'\s{2,}', ' ', cleaned)
        cleaned = cleaned.strip()

        if cleaned != original:
            changes.append({
                "record_id": p.id,
                "field": "product_name",
                "old_value": original,
                "new_value": cleaned,
            })
            if not preview_only:
                p.product_name = cleaned

    if not preview_only:
        db.commit()
    return changes


def _step_standardize_volumes(db: Session, preview_only: bool):
    changes = []
    target_fields = ["product_name", "measure"]

    # Load regex normalization rules
    regex_rules = db.query(models.NormalizationRule).filter(
        models.NormalizationRule.is_regex == True
    ).all()

    for field_name in target_fields:
        column = getattr(models.RawProduct, field_name)
        products = db.query(models.RawProduct).filter(column != None).all()

        for p in products:
            original = getattr(p, field_name)
            if not original:
                continue

            modified = original
            for pattern, replacement in VOLUME_PATTERNS:
                modified = re.sub(pattern, replacement, modified)

            for rule in regex_rules:
                if rule.field_name == field_name:
                    try:
                        modified = re.sub(rule.original_value, rule.normalized_value, modified)
                    except re.error:
                        pass

            if modified != original:
                changes.append({
                    "record_id": p.id,
                    "field": field_name,
                    "old_value": original,
                    "new_value": modified,
                })
                if not preview_only:
                    setattr(p, field_name, modified)

    if not preview_only:
        db.commit()
    return changes


def _step_consolidate_gtin(db: Session, preview_only: bool):
    changes = []
    products = db.query(models.RawProduct).all()

    code_fields = [
        "product_code_universal_1",
        "product_code_universal_2",
        "product_code_universal_3",
        "product_code_universal_4",
    ]

    reason_fields = [
        "gtin_empty_reason_1",
        "gtin_empty_reason_2",
        "gtin_empty_reason_3",
        "gtin_product_reason",
        "gtin_reason_lower",
        "gtin_empty_reason_typo",
    ]

    for p in products:
        # Consolidate product codes into gtin
        current_gtin = p.gtin
        if not current_gtin or not current_gtin.strip():
            for code_field in code_fields:
                val = getattr(p, code_field)
                if val and val.strip():
                    changes.append({
                        "record_id": p.id,
                        "field": "gtin",
                        "old_value": current_gtin,
                        "new_value": val.strip(),
                    })
                    if not preview_only:
                        p.gtin = val.strip()
                    break

        # Consolidate GTIN reasons into gtin_reason
        current_reason = p.gtin_reason
        if not current_reason or not current_reason.strip():
            for reason_field in reason_fields:
                val = getattr(p, reason_field)
                if val and val.strip():
                    changes.append({
                        "record_id": p.id,
                        "field": "gtin_reason",
                        "old_value": current_reason,
                        "new_value": val.strip(),
                    })
                    if not preview_only:
                        p.gtin_reason = val.strip()
                    break

    if not preview_only:
        db.commit()
    return changes


def _step_fix_export_typos(db: Session, preview_only: bool):
    changes = []
    for field, corrected_header in EXPORT_COLUMN_CORRECTIONS.items():
        current_header = EXPORT_COLUMN_MAPPING.get(field, "")
        if current_header != corrected_header:
            changes.append({
                "record_id": 0,
                "field": field,
                "old_value": current_header,
                "new_value": corrected_header,
            })
            if not preview_only:
                EXPORT_COLUMN_MAPPING[field] = corrected_header
    return changes


STEP_FUNCTIONS = {
    "consolidate_brands": _step_consolidate_brands,
    "clean_product_names": _step_clean_product_names,
    "standardize_volumes": _step_standardize_volumes,
    "consolidate_gtin": _step_consolidate_gtin,
    "fix_export_typos": _step_fix_export_typos,
}


@app.get("/harmonization/steps")
def get_harmonization_steps(db: Session = Depends(get_db)):
    total_products = db.query(func.count(models.RawProduct.id)).scalar() or 0

    steps_with_status = []
    for step in HARMONIZATION_STEPS:
        last_log = db.query(models.HarmonizationLog).filter(
            models.HarmonizationLog.step_id == step["step_id"]
        ).order_by(models.HarmonizationLog.id.desc()).first()

        steps_with_status.append({
            **step,
            "status": "completed" if last_log else "pending",
            "last_run": last_log.executed_at.isoformat() if last_log and last_log.executed_at else None,
            "last_records_updated": last_log.records_updated if last_log else None,
        })

    return {"steps": steps_with_status, "total_products": total_products}


@app.post("/harmonization/preview/{step_id}")
def preview_harmonization_step(step_id: str, db: Session = Depends(get_db)):
    if step_id not in STEP_FUNCTIONS:
        raise HTTPException(status_code=400, detail=f"Unknown step: {step_id}")

    step_def = next(s for s in HARMONIZATION_STEPS if s["step_id"] == step_id)
    changes = STEP_FUNCTIONS[step_id](db, preview_only=True)

    return {
        "step_id": step_id,
        "step_name": step_def["name"],
        "description": step_def["description"],
        "total_affected": len(changes),
        "changes": changes[:200],
        "sample_changes": changes[:50],
    }


@app.post("/harmonization/apply/{step_id}")
def apply_harmonization_step(step_id: str, db: Session = Depends(get_db)):
    if step_id not in STEP_FUNCTIONS:
        raise HTTPException(status_code=400, detail=f"Unknown step: {step_id}")

    step_def = next(s for s in HARMONIZATION_STEPS if s["step_id"] == step_id)
    changes = STEP_FUNCTIONS[step_id](db, preview_only=False)

    fields_modified = list(set(c["field"] for c in changes))
    log_entry = models.HarmonizationLog(
        step_id=step_id,
        step_name=step_def["name"],
        records_updated=len(changes),
        fields_modified=json.dumps(fields_modified),
        executed_at=datetime.utcnow(),
        details=json.dumps({"sample": changes[:20]}),
        reverted=False,
    )
    db.add(log_entry)
    db.flush()  # Get log_entry.id before committing

    # Store all individual changes for undo/redo
    for c in changes:
        db.add(models.HarmonizationChangeRecord(
            log_id=log_entry.id,
            record_id=c["record_id"],
            field=c["field"],
            old_value=c["old_value"],
            new_value=c["new_value"],
        ))

    db.commit()

    return {
        "step_id": step_id,
        "step_name": step_def["name"],
        "records_updated": len(changes),
        "fields_modified": fields_modified,
        "log_id": log_entry.id,
    }


@app.post("/harmonization/apply-all")
def apply_all_harmonization_steps(db: Session = Depends(get_db)):
    results = []
    for step in HARMONIZATION_STEPS:
        step_id = step["step_id"]
        changes = STEP_FUNCTIONS[step_id](db, preview_only=False)
        fields_modified = list(set(c["field"] for c in changes))

        log_entry = models.HarmonizationLog(
            step_id=step_id,
            step_name=step["name"],
            records_updated=len(changes),
            fields_modified=json.dumps(fields_modified),
            executed_at=datetime.utcnow(),
            reverted=False,
        )
        db.add(log_entry)
        db.flush()

        for c in changes:
            db.add(models.HarmonizationChangeRecord(
                log_id=log_entry.id,
                record_id=c["record_id"],
                field=c["field"],
                old_value=c["old_value"],
                new_value=c["new_value"],
            ))

        results.append({
            "step_id": step_id,
            "step_name": step["name"],
            "records_updated": len(changes),
            "fields_modified": fields_modified,
            "log_id": log_entry.id,
        })

    db.commit()
    return {"results": results, "total_steps": len(results)}


@app.get("/harmonization/logs")
def get_harmonization_logs(db: Session = Depends(get_db)):
    logs = db.query(models.HarmonizationLog).order_by(
        models.HarmonizationLog.id.desc()
    ).limit(50).all()

    return [{
        "id": log.id,
        "step_id": log.step_id,
        "step_name": log.step_name,
        "records_updated": log.records_updated,
        "fields_modified": json.loads(log.fields_modified) if log.fields_modified else [],
        "executed_at": log.executed_at.isoformat() if log.executed_at else None,
        "reverted": bool(log.reverted) if log.reverted is not None else False,
    } for log in logs]


@app.post("/harmonization/undo/{log_id}")
def undo_harmonization(log_id: int, db: Session = Depends(get_db)):
    log_entry = db.query(models.HarmonizationLog).filter(
        models.HarmonizationLog.id == log_id
    ).first()
    if not log_entry:
        raise HTTPException(status_code=404, detail="Log entry not found")
    if log_entry.reverted:
        raise HTTPException(status_code=400, detail="This operation has already been reverted")

    # Fetch all stored changes for this log
    change_records = db.query(models.HarmonizationChangeRecord).filter(
        models.HarmonizationChangeRecord.log_id == log_id
    ).all()

    if not change_records and log_entry.records_updated > 0:
        raise HTTPException(status_code=400, detail="No change records found for this log entry (pre-undo data not available)")

    restored = 0
    for cr in change_records:
        product = db.query(models.RawProduct).filter(
            models.RawProduct.id == cr.record_id
        ).first()
        if product:
            setattr(product, cr.field, cr.old_value)
            restored += 1

    log_entry.reverted = True
    db.commit()

    return {
        "log_id": log_id,
        "action": "undo",
        "records_restored": restored,
        "step_id": log_entry.step_id,
        "step_name": log_entry.step_name,
    }


@app.post("/harmonization/redo/{log_id}")
def redo_harmonization(log_id: int, db: Session = Depends(get_db)):
    log_entry = db.query(models.HarmonizationLog).filter(
        models.HarmonizationLog.id == log_id
    ).first()
    if not log_entry:
        raise HTTPException(status_code=404, detail="Log entry not found")
    if not log_entry.reverted:
        raise HTTPException(status_code=400, detail="This operation has not been reverted, cannot redo")

    change_records = db.query(models.HarmonizationChangeRecord).filter(
        models.HarmonizationChangeRecord.log_id == log_id
    ).all()

    reapplied = 0
    for cr in change_records:
        product = db.query(models.RawProduct).filter(
            models.RawProduct.id == cr.record_id
        ).first()
        if product:
            setattr(product, cr.field, cr.new_value)
            reapplied += 1

    log_entry.reverted = False
    db.commit()

    return {
        "log_id": log_id,
        "action": "redo",
        "records_restored": reapplied,
        "step_id": log_entry.step_id,
        "step_name": log_entry.step_name,
    }


# ── Store Integration Endpoints ─────────────────────────────────────────

SUPPORTED_PLATFORMS = ["woocommerce", "shopify", "bsale", "custom"]

@app.get("/stores")
def get_all_stores(db: Session = Depends(get_db)):
    stores = db.query(models.StoreConnection).order_by(models.StoreConnection.id.desc()).all()
    result = []
    for s in stores:
        result.append({
            "id": s.id,
            "name": s.name,
            "platform": s.platform,
            "base_url": s.base_url,
            "is_active": s.is_active,
            "last_sync_at": str(s.last_sync_at) if s.last_sync_at else None,
            "created_at": str(s.created_at) if s.created_at else None,
            "product_count": s.product_count or 0,
            "sync_direction": s.sync_direction or "bidirectional",
            "notes": s.notes,
        })
    return result


@app.get("/stores/{store_id}")
def get_store(store_id: int, db: Session = Depends(get_db)):
    store = db.query(models.StoreConnection).filter(models.StoreConnection.id == store_id).first()
    if not store:
        raise HTTPException(status_code=404, detail="Store connection not found")
    return {
        "id": store.id,
        "name": store.name,
        "platform": store.platform,
        "base_url": store.base_url,
        "is_active": store.is_active,
        "last_sync_at": str(store.last_sync_at) if store.last_sync_at else None,
        "created_at": str(store.created_at) if store.created_at else None,
        "product_count": store.product_count or 0,
        "sync_direction": store.sync_direction or "bidirectional",
        "notes": store.notes,
        "has_api_key": bool(store.api_key),
        "has_api_secret": bool(store.api_secret),
        "has_access_token": bool(store.access_token),
    }


@app.post("/stores")
def create_store(payload: schemas.StoreConnectionCreate, db: Session = Depends(get_db)):
    if payload.platform not in SUPPORTED_PLATFORMS:
        raise HTTPException(status_code=400, detail=f"Platform '{payload.platform}' not supported. Use: {SUPPORTED_PLATFORMS}")

    store = models.StoreConnection(
        name=payload.name,
        platform=payload.platform,
        base_url=payload.base_url.rstrip("/"),
        api_key=payload.api_key,
        api_secret=payload.api_secret,
        access_token=payload.access_token,
        custom_headers=payload.custom_headers,
        sync_direction=payload.sync_direction,
        notes=payload.notes,
        is_active=True,
        created_at=datetime.utcnow(),
        product_count=0,
    )
    db.add(store)
    db.commit()
    db.refresh(store)

    return {
        "message": f"Store '{store.name}' created successfully",
        "id": store.id,
        "platform": store.platform,
    }


@app.put("/stores/{store_id}")
def update_store(store_id: int, payload: schemas.StoreConnectionUpdate, db: Session = Depends(get_db)):
    store = db.query(models.StoreConnection).filter(models.StoreConnection.id == store_id).first()
    if not store:
        raise HTTPException(status_code=404, detail="Store connection not found")

    update_data = payload.model_dump(exclude_unset=True)
    if "base_url" in update_data and update_data["base_url"]:
        update_data["base_url"] = update_data["base_url"].rstrip("/")

    for field, value in update_data.items():
        setattr(store, field, value)

    db.commit()
    db.refresh(store)
    return {"message": f"Store '{store.name}' updated successfully", "id": store.id}


@app.delete("/stores/{store_id}")
def delete_store(store_id: int, db: Session = Depends(get_db)):
    store = db.query(models.StoreConnection).filter(models.StoreConnection.id == store_id).first()
    if not store:
        raise HTTPException(status_code=404, detail="Store connection not found")

    # Also delete associated mappings and logs
    db.query(models.StoreSyncMapping).filter(models.StoreSyncMapping.store_id == store_id).delete()
    db.query(models.SyncLog).filter(models.SyncLog.store_id == store_id).delete()
    db.delete(store)
    db.commit()
    return {"message": f"Store '{store.name}' and all associated data deleted", "id": store_id}


@app.post("/stores/{store_id}/toggle")
def toggle_store(store_id: int, db: Session = Depends(get_db)):
    store = db.query(models.StoreConnection).filter(models.StoreConnection.id == store_id).first()
    if not store:
        raise HTTPException(status_code=404, detail="Store connection not found")
    store.is_active = not store.is_active
    db.commit()
    return {"message": f"Store '{store.name}' {'activated' if store.is_active else 'deactivated'}", "is_active": store.is_active}


@app.get("/stores/stats/summary")
def get_stores_summary(db: Session = Depends(get_db)):
    total_stores = db.query(func.count(models.StoreConnection.id)).scalar() or 0
    active_stores = db.query(func.count(models.StoreConnection.id)).filter(
        models.StoreConnection.is_active == True
    ).scalar() or 0
    total_mappings = db.query(func.count(models.StoreSyncMapping.id)).scalar() or 0

    platform_counts = db.query(
        models.StoreConnection.platform,
        func.count(models.StoreConnection.id)
    ).group_by(models.StoreConnection.platform).all()

    return {
        "total_stores": total_stores,
        "active_stores": active_stores,
        "total_mappings": total_mappings,
        "platforms": {p[0]: p[1] for p in platform_counts},
    }


# ── Sync Engine Endpoints ───────────────────────────────────────────────

from backend.adapters import get_adapter

def _get_store_adapter(store: models.StoreConnection):
    """Build adapter from store connection model."""
    config = {
        "platform": store.platform,
        "base_url": store.base_url,
        "api_key": store.api_key,
        "api_secret": store.api_secret,
        "access_token": store.access_token,
        "custom_headers": store.custom_headers,
    }
    return get_adapter(store.platform, config)


@app.post("/stores/{store_id}/test")
def test_store_connection(store_id: int, db: Session = Depends(get_db)):
    store = db.query(models.StoreConnection).filter(models.StoreConnection.id == store_id).first()
    if not store:
        raise HTTPException(status_code=404, detail="Store not found")

    try:
        adapter = _get_store_adapter(store)
        result = adapter.test_connection()
        return {
            "success": result.success,
            "message": result.message,
            "store_name": result.store_name,
            "product_count": result.product_count,
            "api_version": result.api_version,
        }
    except Exception as e:
        return {"success": False, "message": str(e)}


@app.post("/stores/{store_id}/pull")
def pull_products_from_store(store_id: int, page: int = 1, per_page: int = 50, db: Session = Depends(get_db)):
    """Pull products from remote store and create queue items for human review."""
    store = db.query(models.StoreConnection).filter(models.StoreConnection.id == store_id).first()
    if not store:
        raise HTTPException(status_code=404, detail="Store not found")
    if not store.is_active:
        raise HTTPException(status_code=400, detail="Store connection is inactive")

    try:
        adapter = _get_store_adapter(store)
        remote_products = adapter.fetch_products(page=page, per_page=per_page)
    except Exception as e:
        # Log the error
        db.add(models.SyncLog(
            store_id=store_id, action="pull", status="error",
            records_affected=0, details=str(e), executed_at=datetime.utcnow()
        ))
        db.commit()
        raise HTTPException(status_code=502, detail=f"Failed to fetch from store: {e}")

    new_mappings = 0
    new_queue_items = 0
    skipped = 0

    for rp in remote_products:
        if not rp.canonical_url:
            skipped += 1
            continue

        # Check if mapping exists by canonical_url
        existing = db.query(models.StoreSyncMapping).filter(
            models.StoreSyncMapping.store_id == store_id,
            models.StoreSyncMapping.canonical_url == rp.canonical_url,
        ).first()

        if not existing:
            # Create new mapping
            mapping = models.StoreSyncMapping(
                store_id=store_id,
                local_product_id=None,
                remote_product_id=rp.remote_id,
                canonical_url=rp.canonical_url,
                remote_sku=rp.sku,
                remote_name=rp.name,
                remote_price=rp.price,
                remote_stock=rp.stock,
                remote_status=rp.status,
                remote_data_json=json.dumps(rp.raw_data, default=str, ensure_ascii=False) if rp.raw_data else None,
                sync_status="pending",
                created_at=datetime.utcnow(),
            )
            db.add(mapping)
            db.flush()
            new_mappings += 1

            # Create queue item for human review
            db.add(models.SyncQueueItem(
                store_id=store_id,
                mapping_id=mapping.id,
                direction="pull",
                product_name=rp.name,
                canonical_url=rp.canonical_url,
                field="new_product",
                local_value=None,
                remote_value=rp.name,
                status="pending",
                created_at=datetime.utcnow(),
            ))
            new_queue_items += 1
        else:
            # Check for changes in existing mapping
            changes = []
            if existing.remote_name != rp.name and rp.name:
                changes.append(("name", existing.remote_name, rp.name))
            if existing.remote_price != rp.price and rp.price:
                changes.append(("price", existing.remote_price, rp.price))
            if existing.remote_stock != rp.stock and rp.stock:
                changes.append(("stock", existing.remote_stock, rp.stock))
            if existing.remote_sku != rp.sku and rp.sku:
                changes.append(("sku", existing.remote_sku, rp.sku))
            if existing.remote_status != rp.status and rp.status:
                changes.append(("status", existing.remote_status, rp.status))

            for field, old_val, new_val in changes:
                # Only create queue item if not already pending for this field
                already_pending = db.query(models.SyncQueueItem).filter(
                    models.SyncQueueItem.mapping_id == existing.id,
                    models.SyncQueueItem.field == field,
                    models.SyncQueueItem.status == "pending",
                ).first()
                if not already_pending:
                    db.add(models.SyncQueueItem(
                        store_id=store_id,
                        mapping_id=existing.id,
                        direction="pull",
                        product_name=rp.name,
                        canonical_url=rp.canonical_url,
                        field=field,
                        local_value=old_val,
                        remote_value=new_val,
                        status="pending",
                        created_at=datetime.utcnow(),
                    ))
                    new_queue_items += 1

            # Update snapshot
            existing.remote_name = rp.name or existing.remote_name
            existing.remote_price = rp.price or existing.remote_price
            existing.remote_stock = rp.stock or existing.remote_stock
            existing.remote_sku = rp.sku or existing.remote_sku
            existing.remote_status = rp.status or existing.remote_status
            existing.remote_data_json = json.dumps(rp.raw_data, default=str, ensure_ascii=False) if rp.raw_data else existing.remote_data_json
            existing.last_synced_at = datetime.utcnow()

    # Log the sync
    store.last_sync_at = datetime.utcnow()
    db.add(models.SyncLog(
        store_id=store_id, action="pull", status="success",
        records_affected=new_mappings + new_queue_items,
        details=json.dumps({"new_mappings": new_mappings, "queue_items": new_queue_items, "skipped": skipped}),
        executed_at=datetime.utcnow()
    ))
    db.commit()

    return {
        "message": f"Pull completed: {len(remote_products)} products fetched",
        "new_mappings": new_mappings,
        "new_queue_items": new_queue_items,
        "skipped": skipped,
        "total_fetched": len(remote_products),
    }


@app.get("/stores/{store_id}/mappings")
def get_store_mappings(store_id: int, skip: int = 0, limit: int = 50, db: Session = Depends(get_db)):
    total = db.query(func.count(models.StoreSyncMapping.id)).filter(
        models.StoreSyncMapping.store_id == store_id
    ).scalar() or 0

    mappings = db.query(models.StoreSyncMapping).filter(
        models.StoreSyncMapping.store_id == store_id
    ).order_by(models.StoreSyncMapping.id.desc()).offset(skip).limit(limit).all()

    return {
        "total": total,
        "mappings": [{
            "id": m.id,
            "local_product_id": m.local_product_id,
            "remote_product_id": m.remote_product_id,
            "canonical_url": m.canonical_url,
            "remote_sku": m.remote_sku,
            "remote_name": m.remote_name,
            "remote_price": m.remote_price,
            "remote_stock": m.remote_stock,
            "remote_status": m.remote_status,
            "sync_status": m.sync_status,
            "last_synced_at": str(m.last_synced_at) if m.last_synced_at else None,
        } for m in mappings]
    }


@app.get("/stores/{store_id}/queue")
def get_store_queue(store_id: int, status: str = "pending", skip: int = 0, limit: int = 50, db: Session = Depends(get_db)):
    query = db.query(models.SyncQueueItem).filter(
        models.SyncQueueItem.store_id == store_id,
    )
    if status != "all":
        query = query.filter(models.SyncQueueItem.status == status)

    total = query.count()
    items = query.order_by(models.SyncQueueItem.id.desc()).offset(skip).limit(limit).all()

    return {
        "total": total,
        "items": [{
            "id": q.id,
            "mapping_id": q.mapping_id,
            "direction": q.direction,
            "product_name": q.product_name,
            "canonical_url": q.canonical_url,
            "field": q.field,
            "local_value": q.local_value,
            "remote_value": q.remote_value,
            "status": q.status,
            "created_at": str(q.created_at) if q.created_at else None,
            "resolved_at": str(q.resolved_at) if q.resolved_at else None,
        } for q in items]
    }


@app.post("/stores/queue/{item_id}/approve")
def approve_queue_item(item_id: int, db: Session = Depends(get_db)):
    item = db.query(models.SyncQueueItem).filter(models.SyncQueueItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Queue item not found")
    if item.status != "pending":
        raise HTTPException(status_code=400, detail=f"Item is already {item.status}")
    item.status = "approved"
    item.resolved_at = datetime.utcnow()
    db.commit()
    return {"message": "Item approved", "id": item_id, "status": "approved"}


@app.post("/stores/queue/{item_id}/reject")
def reject_queue_item(item_id: int, db: Session = Depends(get_db)):
    item = db.query(models.SyncQueueItem).filter(models.SyncQueueItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Queue item not found")
    if item.status != "pending":
        raise HTTPException(status_code=400, detail=f"Item is already {item.status}")
    item.status = "rejected"
    item.resolved_at = datetime.utcnow()
    db.commit()
    return {"message": "Item rejected", "id": item_id, "status": "rejected"}


@app.post("/stores/queue/bulk-approve")
def bulk_approve_queue(store_id: int, db: Session = Depends(get_db)):
    """Approve all pending queue items for a store."""
    updated = db.query(models.SyncQueueItem).filter(
        models.SyncQueueItem.store_id == store_id,
        models.SyncQueueItem.status == "pending",
    ).update({"status": "approved", "resolved_at": datetime.utcnow()})
    db.commit()
    return {"message": f"{updated} items approved", "count": updated}


@app.post("/stores/queue/bulk-reject")
def bulk_reject_queue(store_id: int, db: Session = Depends(get_db)):
    """Reject all pending queue items for a store."""
    updated = db.query(models.SyncQueueItem).filter(
        models.SyncQueueItem.store_id == store_id,
        models.SyncQueueItem.status == "pending",
    ).update({"status": "rejected", "resolved_at": datetime.utcnow()})
    db.commit()
    return {"message": f"{updated} items rejected", "count": updated}


@app.get("/stores/{store_id}/logs")
def get_store_logs(store_id: int, skip: int = 0, limit: int = 20, db: Session = Depends(get_db)):
    logs = db.query(models.SyncLog).filter(
        models.SyncLog.store_id == store_id
    ).order_by(models.SyncLog.id.desc()).offset(skip).limit(limit).all()

    return [{
        "id": l.id,
        "action": l.action,
        "status": l.status,
        "records_affected": l.records_affected,
        "details": l.details,
        "executed_at": str(l.executed_at) if l.executed_at else None,
    } for l in logs]


@app.get("/health")
def health_check():
    return {"status": "ok"}
