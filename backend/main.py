from fastapi import FastAPI, Depends, UploadFile, File, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List
import pandas as pd
import io

from backend import models, schemas, database

models.Base.metadata.create_all(bind=database.engine)

app = FastAPI()

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
    if not file.filename.endswith(".xlsx"):
        raise HTTPException(status_code=400, detail="Invalid file format. Only .xlsx allowed.")

    contents = await file.read()
    df = pd.read_excel(io.BytesIO(contents))

    df.columns = df.columns.str.strip()

    # Track which columns were matched vs ignored
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


@app.delete("/products/{product_id}")
def delete_product(product_id: int, db: Session = Depends(get_db)):
    product = db.query(models.RawProduct).filter(models.RawProduct.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    db.delete(product)
    db.commit()
    return {"message": "Product deleted", "id": product_id}


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

    return {
        "total_products": total_products,
        "unique_brands": unique_brands,
        "unique_models": unique_models,
        "unique_product_types": unique_product_types,
        "validation_status": validation_status,
        "identifier_coverage": {
            "with_sku": with_sku,
            "with_barcode": with_barcode,
            "with_gtin": with_gtin,
            "total": total_products,
        },
        "top_brands": [{"name": b[0], "count": b[1]} for b in top_brands],
        "type_distribution": [{"name": t[0], "count": t[1]} for t in type_distribution],
        "status_distribution": [{"name": s[0], "count": s[1]} for s in status_distribution],
    }


# Reverse mapping: model_field -> original excel header
EXPORT_COLUMN_MAPPING = {v: k.strip() for k, v in COLUMN_MAPPING.items()}

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


@app.delete("/products/all")
def purge_all_products(include_rules: bool = False, db: Session = Depends(get_db)):
    product_count = db.query(func.count(models.RawProduct.id)).scalar() or 0
    db.query(models.RawProduct).delete()

    rules_count = 0
    if include_rules:
        rules_count = db.query(func.count(models.NormalizationRule.id)).scalar() or 0
        db.query(models.NormalizationRule).delete()

    db.commit()
    return {
        "message": "Database purged successfully",
        "products_deleted": product_count,
        "rules_deleted": rules_count,
    }


@app.get("/health")
def health_check():
    return {"status": "ok"}
