"""
Harmonization pipeline endpoints.
  GET  /harmonization/steps
  POST /harmonization/preview/{step_id}
  POST /harmonization/apply/{step_id}
  POST /harmonization/apply-all
  GET  /harmonization/logs
  POST /harmonization/undo/{log_id}
  POST /harmonization/redo/{log_id}
"""
import json
import logging
import re
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Path
from sqlalchemy import func
from sqlalchemy.orm import Session

from backend import database, models
from backend.auth import get_current_user, require_role
from backend.database import get_db
from backend.routers.column_maps import EXPORT_COLUMN_CORRECTIONS, EXPORT_COLUMN_MAPPING
from backend.routers.deps import _audit, _dispatch_webhook

logger = logging.getLogger(__name__)

router = APIRouter()

# ── Harmonization pipeline metadata ──────────────────────────────────────────

HARMONIZATION_STEPS = [
    {
        "step_id": "consolidate_brands",
        "name": "Consolidate Brand Columns",
        "description": "Merge brand_lower into brand_capitalized when empty and apply brand normalization rules.",
        "order": 1,
    },
    {
        "step_id": "clean_entity_names",
        "name": "Clean Product Names",
        "description": "Remove double spaces, trim whitespace, and normalize special characters.",
        "order": 2,
    },
    {
        "step_id": "standardize_volumes",
        "name": "Standardize Volume/Unit Variants",
        "description": "Normalize volume formats (250ML → 250 mL, 1L → 1 L, 500gr → 500 g).",
        "order": 3,
    },
    {
        "step_id": "consolidate_gtin",
        "name": "Consolidate GTIN Columns",
        "description": "Merge 4 product code columns and 7 GTIN reason fields into single authoritative values.",
        "order": 4,
    },
    {
        "step_id": "fix_export_typos",
        "name": "Fix Export Column Name Typos",
        "description": "Correct EQUIMAPIENTO → EQUIPAMIENTO, PRODRUCTO → PRODUCTO in export headers.",
        "order": 5,
    },
]

VOLUME_PATTERNS = [
    (r"(\d+)\s*(?:ML|Ml|ml)", r"\1 mL"),
    (r"(\d+(?:\.\d+)?)\s*(?:LT|Lt|lt|lts|LTS|Lts)\b", r"\1 L"),
    (r"(\d+(?:\.\d+)?)\s*[Ll]\b(?![\w])", r"\1 L"),
    (r"(\d+(?:\.\d+)?)\s*(?:KG|Kg|kg|kgs|KGS)\b", r"\1 kg"),
    (r"(\d+)\s*(?:GR|Gr|gr|grs|GRS)\b", r"\1 g"),
    (r"(\d+(?:\.\d+)?)\s*(?:CM|Cm|cm)\b", r"\1 cm"),
    (r"(\d+(?:\.\d+)?)\s*(?:MT|Mt|mt|mts|MTS)\b", r"\1 m"),
]

_PREVIEW_ROW_CAP = 10_000  # Max rows examined during preview to avoid OOM


# ── Step functions ────────────────────────────────────────────────────────────

def _step_consolidate_brands(db: Session, preview_only: bool):
    changes = []
    q = db.query(models.RawEntity)
    if preview_only:
        q = q.limit(_PREVIEW_ROW_CAP)
    entities = q.all()

    brand_rules = db.query(models.NormalizationRule).filter(
        models.NormalizationRule.field_name == "brand_capitalized",
        models.NormalizationRule.is_regex == False,
    ).all()
    brand_map = {r.original_value: r.normalized_value for r in brand_rules}

    for p in entities:
        new_brand = p.brand_capitalized
        if not new_brand or not new_brand.strip():
            if p.brand_lower and p.brand_lower.strip():
                new_brand = p.brand_lower.strip()
            else:
                continue
        new_brand = new_brand.strip()
        if new_brand in brand_map:
            new_brand = brand_map[new_brand]
        if new_brand != p.brand_capitalized:
            changes.append({
                "record_id": p.id,
                "field":     "brand_capitalized",
                "old_value": p.brand_capitalized,
                "new_value": new_brand,
            })
            if not preview_only:
                p.brand_capitalized = new_brand

    if not preview_only:
        db.commit()
    return changes


def _step_clean_entity_names(db: Session, preview_only: bool):
    changes = []
    q = db.query(models.RawEntity).filter(models.RawEntity.primary_label != None)
    if preview_only:
        q = q.limit(_PREVIEW_ROW_CAP)
    entities = q.all()

    for p in entities:
        original = p.primary_label
        if not original:
            continue
        cleaned = original
        cleaned = cleaned.replace("\u00a0", " ")
        cleaned = cleaned.replace("\t", " ")
        cleaned = re.sub(r"\s{2,}", " ", cleaned)
        cleaned = cleaned.strip()
        if cleaned != original:
            changes.append({
                "record_id": p.id,
                "field":     "primary_label",
                "old_value": original,
                "new_value": cleaned,
            })
            if not preview_only:
                p.primary_label = cleaned

    if not preview_only:
        db.commit()
    return changes


def _step_standardize_volumes(db: Session, preview_only: bool):
    changes = []
    target_fields = ["primary_label", "measure"]
    regex_rules = db.query(models.NormalizationRule).filter(
        models.NormalizationRule.is_regex == True
    ).all()

    for field_name in target_fields:
        column = getattr(models.RawEntity, field_name)
        q = db.query(models.RawEntity).filter(column != None)
        if preview_only:
            q = q.limit(_PREVIEW_ROW_CAP)
        entities = q.all()

        for p in entities:
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
                    "field":     field_name,
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
    q = db.query(models.RawEntity)
    if preview_only:
        q = q.limit(_PREVIEW_ROW_CAP)
    entities = q.all()

    code_fields = [
        "entity_code_universal_1",
        "entity_code_universal_2",
        "entity_code_universal_3",
        "entity_code_universal_4",
    ]
    reason_fields = [
        "gtin_empty_reason_1",
        "gtin_empty_reason_2",
        "gtin_empty_reason_3",
        "gtin_entity_reason",
        "gtin_reason_lower",
        "gtin_empty_reason_typo",
    ]

    for p in entities:
        current_gtin = p.gtin
        if not current_gtin or not current_gtin.strip():
            for code_field in code_fields:
                val = getattr(p, code_field)
                if val and val.strip():
                    changes.append({
                        "record_id": p.id,
                        "field":     "gtin",
                        "old_value": current_gtin,
                        "new_value": val.strip(),
                    })
                    if not preview_only:
                        p.gtin = val.strip()
                    break

        current_reason = p.gtin_reason
        if not current_reason or not current_reason.strip():
            for reason_field in reason_fields:
                val = getattr(p, reason_field)
                if val and val.strip():
                    changes.append({
                        "record_id": p.id,
                        "field":     "gtin_reason",
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
                "field":     field,
                "old_value": current_header,
                "new_value": corrected_header,
            })
            if not preview_only:
                EXPORT_COLUMN_MAPPING[field] = corrected_header
    return changes


STEP_FUNCTIONS = {
    "consolidate_brands":  _step_consolidate_brands,
    "clean_entity_names":  _step_clean_entity_names,
    "standardize_volumes": _step_standardize_volumes,
    "consolidate_gtin":    _step_consolidate_gtin,
    "fix_export_typos":    _step_fix_export_typos,
}


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/harmonization/steps")
def get_harmonization_steps(
    db: Session = Depends(get_db),
    _: models.User = Depends(require_role("super_admin", "admin", "editor")),
):
    total_entities = db.query(func.count(models.RawEntity.id)).scalar() or 0
    steps_with_status = []
    for step in HARMONIZATION_STEPS:
        last_log = (
            db.query(models.HarmonizationLog)
            .filter(models.HarmonizationLog.step_id == step["step_id"])
            .order_by(models.HarmonizationLog.id.desc())
            .first()
        )
        steps_with_status.append({
            **step,
            "status":               "completed" if last_log else "pending",
            "last_run":             last_log.executed_at.isoformat() if last_log and last_log.executed_at else None,
            "last_records_updated": last_log.records_updated if last_log else None,
        })
    return {"steps": steps_with_status, "total_entities": total_entities}


@router.post("/harmonization/preview/{step_id}")
def preview_harmonization_step(
    step_id: str,
    db: Session = Depends(get_db),
    _: models.User = Depends(require_role("super_admin", "admin", "editor")),
):
    if step_id not in STEP_FUNCTIONS:
        raise HTTPException(status_code=400, detail=f"Unknown step: {step_id}")
    step_def = next(s for s in HARMONIZATION_STEPS if s["step_id"] == step_id)
    changes = STEP_FUNCTIONS[step_id](db, preview_only=True)
    return {
        "step_id":       step_id,
        "step_name":     step_def["name"],
        "description":   step_def["description"],
        "total_affected": len(changes),
        "changes":       changes[:200],
        "sample_changes": changes[:50],
    }


@router.post("/harmonization/apply/{step_id}")
def apply_harmonization_step(
    step_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_role("super_admin", "admin", "editor")),
):
    if step_id not in STEP_FUNCTIONS:
        raise HTTPException(status_code=400, detail=f"Unknown step: {step_id}")
    step_def = next(s for s in HARMONIZATION_STEPS if s["step_id"] == step_id)
    changes = STEP_FUNCTIONS[step_id](db, preview_only=False)

    fields_modified = list({c["field"] for c in changes})
    log_entry = models.HarmonizationLog(
        step_id=step_id,
        step_name=step_def["name"],
        records_updated=len(changes),
        fields_modified=json.dumps(fields_modified),
        executed_at=datetime.now(timezone.utc),
        details=json.dumps({"sample": changes[:20]}),
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

    _audit(
        db, "harmonization.apply",
        user_id=current_user.id,
        details={
            "step_id":         step_id,
            "step_name":       step_def["name"],
            "records_updated": len(changes),
        },
    )
    db.commit()
    _dispatch_webhook(
        "harmonization.apply",
        {"step_id": step_id, "records_updated": len(changes)},
        database.SessionLocal,
    )
    return {
        "step_id":          step_id,
        "step_name":        step_def["name"],
        "records_updated":  len(changes),
        "fields_modified":  fields_modified,
        "log_id":           log_entry.id,
    }


@router.post("/harmonization/apply-all")
def apply_all_harmonization_steps(
    db: Session = Depends(get_db),
    _: models.User = Depends(require_role("super_admin", "admin", "editor")),
):
    results = []
    for step in HARMONIZATION_STEPS:
        step_id = step["step_id"]
        changes = STEP_FUNCTIONS[step_id](db, preview_only=False)
        fields_modified = list({c["field"] for c in changes})

        log_entry = models.HarmonizationLog(
            step_id=step_id,
            step_name=step["name"],
            records_updated=len(changes),
            fields_modified=json.dumps(fields_modified),
            executed_at=datetime.now(timezone.utc),
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
            "step_id":         step_id,
            "step_name":       step["name"],
            "records_updated": len(changes),
            "fields_modified": fields_modified,
            "log_id":          log_entry.id,
        })

    db.commit()
    return {"results": results, "total_steps": len(results)}


@router.get("/harmonization/logs")
def get_harmonization_logs(
    db: Session = Depends(get_db),
    _: models.User = Depends(require_role("super_admin", "admin", "editor")),
):
    logs = (
        db.query(models.HarmonizationLog)
        .order_by(models.HarmonizationLog.id.desc())
        .limit(50)
        .all()
    )
    return [
        {
            "id":               log.id,
            "step_id":          log.step_id,
            "step_name":        log.step_name,
            "records_updated":  log.records_updated,
            "fields_modified":  json.loads(log.fields_modified) if log.fields_modified else [],
            "executed_at":      log.executed_at.isoformat() if log.executed_at else None,
            "reverted":         bool(log.reverted) if log.reverted is not None else False,
        }
        for log in logs
    ]


@router.post("/harmonization/undo/{log_id}")
def undo_harmonization(
    log_id: int = Path(..., ge=1),
    db: Session = Depends(get_db),
    _: models.User = Depends(require_role("super_admin", "admin", "editor")),
):
    log_entry = db.query(models.HarmonizationLog).filter(
        models.HarmonizationLog.id == log_id
    ).first()
    if not log_entry:
        raise HTTPException(status_code=404, detail="Log entry not found")
    if log_entry.reverted:
        raise HTTPException(status_code=400, detail="This operation has already been reverted")

    change_records = db.query(models.HarmonizationChangeRecord).filter(
        models.HarmonizationChangeRecord.log_id == log_id
    ).all()

    if not change_records and log_entry.records_updated > 0:
        raise HTTPException(
            status_code=400,
            detail="No change records found for this log entry (pre-undo data not available)",
        )

    restored = 0
    for cr in change_records:
        entity = db.query(models.RawEntity).filter(models.RawEntity.id == cr.record_id).first()
        if entity:
            setattr(entity, cr.field, cr.old_value)
            restored += 1

    log_entry.reverted = True
    db.commit()
    return {
        "log_id":           log_id,
        "action":           "undo",
        "records_restored": restored,
        "step_id":          log_entry.step_id,
        "step_name":        log_entry.step_name,
    }


@router.post("/harmonization/redo/{log_id}")
def redo_harmonization(
    log_id: int = Path(..., ge=1),
    db: Session = Depends(get_db),
    _: models.User = Depends(require_role("super_admin", "admin", "editor")),
):
    log_entry = db.query(models.HarmonizationLog).filter(
        models.HarmonizationLog.id == log_id
    ).first()
    if not log_entry:
        raise HTTPException(status_code=404, detail="Log entry not found")
    if not log_entry.reverted:
        raise HTTPException(
            status_code=400, detail="This operation has not been reverted, cannot redo"
        )

    change_records = db.query(models.HarmonizationChangeRecord).filter(
        models.HarmonizationChangeRecord.log_id == log_id
    ).all()

    reapplied = 0
    for cr in change_records:
        entity = db.query(models.RawEntity).filter(models.RawEntity.id == cr.record_id).first()
        if entity:
            setattr(entity, cr.field, cr.new_value)
            reapplied += 1

    log_entry.reverted = False
    db.commit()
    return {
        "log_id":           log_id,
        "action":           "redo",
        "records_restored": reapplied,
        "step_id":          log_entry.step_id,
        "step_name":        log_entry.step_name,
    }
