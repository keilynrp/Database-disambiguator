"""
Sprint 45 — Knowledge Gap Detector tests
GET /artifacts/gaps/{domain_id}
"""
import pytest
from backend import models


# ── Helpers ────────────────────────────────────────────────────────────────────

def _add_entity(db, enrichment_status="none", concepts=None):
    e = models.RawEntity(
        primary_label="Test Entity",
        enrichment_status=enrichment_status,
        enrichment_concepts=concepts,
    )
    db.add(e)
    db.commit()
    return e


def _add_authority(db, status="pending"):
    r = models.AuthorityRecord(
        field_name="brand_capitalized",
        original_value="Apple",
        authority_source="wikidata",
        authority_id="Q312",
        canonical_label="Apple Inc.",
        confidence=0.85,
        status=status,
    )
    db.add(r)
    db.commit()
    return r


# ── Tests ──────────────────────────────────────────────────────────────────────

def test_gaps_requires_auth(client):
    resp = client.get("/artifacts/gaps/default")
    assert resp.status_code in (401, 403)


def test_gaps_invalid_domain_404(client, auth_headers):
    resp = client.get("/artifacts/gaps/nonexistent_domain_xyz", headers=auth_headers)
    assert resp.status_code == 404


def test_gaps_returns_shape(client, auth_headers, db_session):
    resp = client.get("/artifacts/gaps/default", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "domain_id" in data
    assert "summary" in data
    assert "gaps" in data
    assert isinstance(data["gaps"], list)
    summary = data["summary"]
    assert "critical" in summary
    assert "warning" in summary
    assert "total_entities" in summary


def test_gaps_enrichment_detected(client, auth_headers, db_session):
    # Seed 5 unenriched entities (100% gap → critical)
    for _ in range(5):
        _add_entity(db_session, enrichment_status="none")

    resp = client.get("/artifacts/gaps/default", headers=auth_headers)
    assert resp.status_code == 200
    gaps = resp.json()["gaps"]
    enrichment_gaps = [g for g in gaps if g["category"] == "enrichment"]
    assert len(enrichment_gaps) >= 1
    gap = enrichment_gaps[0]
    assert gap["severity"] in ("critical", "warning")
    assert gap["affected_count"] == 5


def test_gaps_authority_pending_detected(client, auth_headers, db_session):
    _add_authority(db_session, status="pending")

    resp = client.get("/artifacts/gaps/default", headers=auth_headers)
    assert resp.status_code == 200
    gaps = resp.json()["gaps"]
    auth_gaps = [g for g in gaps if g["category"] == "authority"]
    assert len(auth_gaps) == 1
    assert auth_gaps[0]["affected_count"] == 1


def test_gaps_severity_sort(client, auth_headers, db_session):
    # Seed many unenriched to trigger critical, plus 1 pending authority for warning
    for _ in range(10):
        _add_entity(db_session, enrichment_status="none")
    _add_authority(db_session, status="pending")

    resp = client.get("/artifacts/gaps/default", headers=auth_headers)
    assert resp.status_code == 200
    gaps = resp.json()["gaps"]
    if len(gaps) >= 2:
        _order = {"critical": 0, "warning": 1, "ok": 2}
        severities = [_order[g["severity"]] for g in gaps]
        assert severities == sorted(severities), "Gaps must be sorted critical first"
