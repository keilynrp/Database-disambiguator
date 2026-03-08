"""
Data ingestion and export endpoints.
  POST /upload
  POST /analyze
  GET  /export
"""
import io
import json
import logging
import math
import os
import shutil
import tempfile
import xml.etree.ElementTree as ET

import pandas as pd
from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import or_

from backend import database, models
from backend.auth import get_current_user, require_role
from backend.database import get_db
from backend.datasource_analyzer import DataSourceAnalyzer
from backend.routers.column_maps import COLUMN_MAPPING, EXPORT_COLUMN_MAPPING
from backend.routers.deps import _audit, _dispatch_webhook

logger = logging.getLogger(__name__)

router = APIRouter()

_MAX_UPLOAD_BYTES = 20 * 1024 * 1024  # 20 MB
_MAX_ROWS = 100_000
_CHUNK_SIZE = 10_000


@router.post("/upload", status_code=201)
async def upload_file(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_role("super_admin", "admin", "editor")),
):
    filename = file.filename.lower()
    allowed_extensions = (".xlsx", ".csv", ".json", ".xml", ".parquet", ".jsonld", ".rdf", ".ttl")
    if not any(filename.endswith(ext) for ext in allowed_extensions):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file format. Allowed: {', '.join(allowed_extensions)}",
        )

    contents = await file.read()
    if len(contents) > _MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Maximum allowed size is 20 MB "
                   f"(received {len(contents) // (1024*1024)} MB).",
        )

    records = []
    try:
        if filename.endswith(".xlsx"):
            df = pd.read_excel(io.BytesIO(contents))
            records = df.to_dict("records")
        elif filename.endswith(".csv"):
            try:
                df = pd.read_csv(io.BytesIO(contents), encoding="utf-8")
            except UnicodeDecodeError:
                df = pd.read_csv(io.BytesIO(contents), encoding="latin-1")
            records = df.to_dict("records")
        elif filename.endswith(".parquet"):
            df = pd.read_parquet(io.BytesIO(contents))
            records = df.to_dict("records")
        elif filename.endswith(".json") or filename.endswith(".jsonld"):
            data = json.loads(contents.decode("utf-8"))
            if isinstance(data, dict):
                list_data = next((v for v in data.values() if isinstance(v, list)), [data])
                records = list_data
            elif isinstance(data, list):
                records = data
        elif filename.endswith(".xml"):
            root = ET.fromstring(contents.decode("utf-8"))
            for child in root:
                record = {}
                for subchild in child:
                    record[subchild.tag] = subchild.text
                if record:
                    records.append(record)
        elif filename.endswith(".rdf") or filename.endswith(".ttl"):
            import rdflib
            g = rdflib.Graph()
            format_type = "ttl" if filename.endswith(".ttl") else "xml"
            g.parse(data=contents.decode("utf-8"), format=format_type)
            entities: dict = {}
            for s, p, o in g:
                subj = str(s)
                pred = str(p).split("/")[-1].split("#")[-1]
                obj = str(o)
                if subj not in entities:
                    entities[subj] = {"entity_key": subj}
                if pred in entities[subj]:
                    entities[subj][pred] += f"; {obj}"
                else:
                    entities[subj][pred] = obj
            records = list(entities.values())
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to process file: {str(e)}")

    if not records:
        return {
            "message": "No valid data found or file is empty",
            "total_rows": 0,
            "matched_columns": [],
            "unmatched_columns": [],
        }

    if len(records) > _MAX_ROWS:
        raise HTTPException(
            status_code=413,
            detail=f"File contains too many rows ({len(records):,}). "
                   f"Maximum allowed is {_MAX_ROWS:,} rows per upload.",
        )

    # Gather all unique keys from records
    all_keys: set = set()
    for row in records[:100]:
        if isinstance(row, dict):
            all_keys.update(row.keys())

    stripped_mapping = {k.strip(): v for k, v in COLUMN_MAPPING.items()}
    valid_model_keys = set(COLUMN_MAPPING.values())

    matched_columns: set = set()
    unmatched_columns: set = set()
    for col in all_keys:
        col_str = str(col).strip()
        if col_str in stripped_mapping or col_str in valid_model_keys:
            matched_columns.add(col_str)
        else:
            unmatched_columns.add(col_str)

    objects = []
    for row in records:
        if not isinstance(row, dict):
            continue

        row_data: dict = {}
        unmatched_data: dict = {}

        for k, val in row.items():
            is_nan = False
            if type(val) is float and math.isnan(val):
                is_nan = True
            elif pd.isna(val) if hasattr(pd, "isna") else False:
                try:
                    if pd.isna(val):
                        is_nan = True
                except (TypeError, ValueError):
                    pass

            if is_nan:
                val = None

            sk = str(k).strip()
            if sk in stripped_mapping:
                model_field = stripped_mapping[sk]
                row_data[model_field] = str(val) if val is not None else None
            elif sk in valid_model_keys:
                row_data[sk] = str(val) if val is not None else None
            else:
                unmatched_data[sk] = val

        if unmatched_data:
            row_data["normalized_json"] = json.dumps(
                unmatched_data, default=str, ensure_ascii=False
            )

        objects.append(models.RawEntity(**row_data))

    for i in range(0, len(objects), _CHUNK_SIZE):
        db.bulk_save_objects(objects[i : i + _CHUNK_SIZE])
    _audit(
        db, "upload",
        user_id=current_user.id,
        details={"filename": file.filename, "rows": len(objects)},
    )
    db.commit()
    _dispatch_webhook(
        "upload",
        {"filename": file.filename, "rows": len(objects)},
        database.SessionLocal,
    )

    return {
        "message": f"Successfully imported {len(objects)} entities",
        "total_rows": len(objects),
        "matched_columns": list(matched_columns),
        "unmatched_columns": list(unmatched_columns),
    }


@router.post("/analyze")
async def analyze_datasource(
    file: UploadFile = File(...),
    _: models.User = Depends(require_role("super_admin", "admin", "editor")),
):
    """
    Analyzes the structure (columns, keys, tags, predicates) of a given file.
    Supports CSV, Excel, JSON, XML, Parquet, RDF, Logs, etc.
    """
    ext = os.path.splitext(file.filename)[1].lower()
    if not ext:
        raise HTTPException(
            status_code=400, detail="File must have an extension to be analyzed"
        )

    fd, temp_path = tempfile.mkstemp(suffix=ext)
    os.close(fd)

    try:
        with open(temp_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        structure = DataSourceAnalyzer.analyze(temp_path)
        return {
            "filename": file.filename,
            "format": ext.strip("."),
            "structure": structure,
            "count": len(structure),
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception:
        logger.exception("Error analyzing file '%s'", file.filename)
        raise HTTPException(
            status_code=500, detail="Error analyzing file. Check server logs for details."
        )
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)


@router.get("/export")
def export_entities(
    search: str = None,
    limit: int = Query(default=5000, ge=1, le=50000),
    db: Session = Depends(get_db),
    _: models.User = Depends(require_role("super_admin", "admin", "editor")),
):
    query = db.query(models.RawEntity)

    if search:
        search_filter = f"%{search}%"
        query = query.filter(
            or_(
                models.RawEntity.entity_name.ilike(search_filter),
                models.RawEntity.brand_capitalized.ilike(search_filter),
                models.RawEntity.model.ilike(search_filter),
                models.RawEntity.sku.ilike(search_filter),
            )
        )

    entities = query.limit(limit).all()

    rows = []
    for p in entities:
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
        headers={"Content-Disposition": "attachment; filename=entities_export.xlsx"},
    )
