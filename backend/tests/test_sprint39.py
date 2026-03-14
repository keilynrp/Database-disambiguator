"""
Sprint 39 regression tests — Executive Dashboard GET /dashboard/summary
"""
import pytest
from backend import models


# ── Helpers ──────────────────────────────────────────────────────────────────

def _seed_entities(db, n=5):
    """Insert n raw entities with varied data."""
    for i in range(n):
        db.add(models.RawEntity(
            primary_label=f"Entity {i}",
            domain="default",
            enrichment_status="completed" if i % 2 == 0 else "none",
            enrichment_citation_count=10 * (i + 1) if i % 2 == 0 else None,
            enrichment_source="openalex" if i % 2 == 0 else None,
            enrichment_concepts="AI, Machine Learning" if i % 2 == 0 else None,
        ))
    db.commit()


# ── Auth tests ────────────────────────────────────────────────────────────────

def test_dashboard_summary_requires_auth(client):
    """Unauthenticated requests must return 401/403."""
    response = client.get("/dashboard/summary")
    assert response.status_code in (401, 403)


# ── Shape / contract tests ────────────────────────────────────────────────────

def test_dashboard_summary_returns_shape(client, auth_headers, db_session):
    _seed_entities(db_session)
    response = client.get("/dashboard/summary", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()

    # Top-level keys
    assert "domain_id" in data
    assert "kpis" in data
    assert "entities_by_year" in data
    assert "brand_year_matrix" in data
    assert "top_concepts" in data
    assert "top_entities" in data

    # KPI shape
    kpis = data["kpis"]
    for key in ("total_entities", "enriched_count", "enrichment_pct", "avg_citations", "total_concepts"):
        assert key in kpis

    # Matrix shape
    matrix = data["brand_year_matrix"]
    assert "brands" in matrix
    assert "years" in matrix
    assert "matrix" in matrix


def test_dashboard_kpis_match_entity_count(client, auth_headers, db_session):
    """kpis.total_entities must equal the actual entity count in the DB."""
    _seed_entities(db_session, n=3)
    response = client.get("/dashboard/summary", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    actual = db_session.query(models.RawEntity).count()
    assert data["kpis"]["total_entities"] == actual


def test_dashboard_empty_domain_returns_zeros(client, auth_headers):
    """With no entities, KPIs are zero and lists are empty — no server error."""
    response = client.get("/dashboard/summary?domain_id=empty_test_domain", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["kpis"]["total_entities"] == 0
    assert data["entities_by_year"] == []
    assert data["top_entities"] == []


def test_dashboard_entities_by_year_sorted(client, auth_headers, db_session):
    """entities_by_year must be sorted in ascending year order."""
    _seed_entities(db_session)
    response = client.get("/dashboard/summary", headers=auth_headers)
    assert response.status_code == 200
    years_list = [item["year"] for item in response.json()["entities_by_year"]]
    assert years_list == sorted(years_list)


def test_dashboard_brand_matrix_top5(client, auth_headers, db_session):
    """brand_year_matrix.brands must have at most 5 entries."""
    # Seed entities with many different brands
    for i in range(10):
        db_session.add(models.RawEntity(
            primary_label=f"Entity brand {i}",
            secondary_label=f"Brand{i}",
            enrichment_status="none",
        ))
    db_session.commit()
    response = client.get("/dashboard/summary", headers=auth_headers)
    assert response.status_code == 200
    brands = response.json()["brand_year_matrix"]["brands"]
    assert len(brands) <= 5
