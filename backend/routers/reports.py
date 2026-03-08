"""
Report builder endpoints.
  POST /reports/generate
  GET  /reports/sections
"""
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend import models
from backend import report_builder as _report_builder
from backend.auth import get_current_user, require_role
from backend.database import get_db

router = APIRouter()

_ALL_REPORT_SECTIONS = list(_report_builder.SECTION_LABELS.keys())


class _ReportRequest(BaseModel):
    domain_id: str          = Field(default="default", min_length=1, max_length=64)
    sections:  List[str]    = Field(default=_ALL_REPORT_SECTIONS, min_length=1, max_length=10)
    title:     Optional[str] = Field(default=None, max_length=200)


@router.post("/reports/generate", tags=["reports"])
def generate_report(
    payload: _ReportRequest,
    db: Session = Depends(get_db),
    _: models.User = Depends(require_role("super_admin", "admin", "editor")),
):
    """Generate a self-contained HTML report and return it as a downloadable file."""
    invalid = [s for s in payload.sections if s not in _report_builder.SECTION_BUILDERS]
    if invalid:
        raise HTTPException(
            status_code=422,
            detail=f"Unknown sections: {invalid}. Valid: {_ALL_REPORT_SECTIONS}",
        )
    html = _report_builder.build(db, payload.domain_id, payload.sections, payload.title)
    filename = (
        f"ukip_report_{payload.domain_id}_"
        f"{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.html"
    )
    return Response(
        content=html,
        media_type="text/html",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/reports/sections", tags=["reports"])
def list_report_sections(_: models.User = Depends(get_current_user)):
    """Return available report sections."""
    return [{"id": k, "label": v} for k, v in _report_builder.SECTION_LABELS.items()]
