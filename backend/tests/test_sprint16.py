"""
Sprint 16 — Authority Resolution Layer: scoring, normalización,
deduplicación y métricas.

Estructura de los tests:
  16A  — normalize.py (unit tests sin I/O)
  16B  — scoring.py   (unit tests sin I/O)
  16C  — resolve_all deduplicación (unit tests)
  16D  — Endpoint /authority/resolve con campos Sprint 16
  16E  — Contexto en el request influye en el score
  16F  — GET /authority/metrics
"""
from __future__ import annotations

import json
from unittest.mock import patch

import pytest

from backend.authority.base import AuthorityCandidate, ResolveContext
from backend.authority.normalize import (
    normalize_name,
    reformat_surname_first,
    name_variants,
    strip_diacritics,
)
from backend.authority.scoring import compute_score
from backend.authority.resolver import _deduplicate

_MOCK_TARGET = "backend.routers.authority._authority_resolve_all"


# ── 16A · normalize.py ───────────────────────────────────────────────────────

class TestNormalize:
    def test_strip_diacritics(self):
        assert strip_diacritics("García") == "Garcia"
        assert strip_diacritics("Ñoño") == "Nono"
        assert strip_diacritics("Müller") == "Muller"

    def test_normalize_name_lowercase(self):
        assert normalize_name("García Márquez") == "garcia marquez"

    def test_normalize_name_punctuation_collapsed(self):
        assert normalize_name("Smith, John A.") == "smith john a"

    def test_normalize_name_whitespace_collapsed(self):
        assert normalize_name("  García   Márquez  ") == "garcia marquez"

    def test_reformat_surname_first_inverted(self):
        assert reformat_surname_first("García Márquez, Gabriel") == "Gabriel García Márquez"

    def test_reformat_surname_first_no_comma(self):
        assert reformat_surname_first("Gabriel García Márquez") == "Gabriel García Márquez"

    def test_name_variants_returns_both_forms(self):
        variants = name_variants("García Márquez, Gabriel")
        assert "garcia marquez gabriel" in variants  # reformatted
        assert "garcia marquez" not in variants       # original without comma

    def test_name_variants_no_comma_returns_one(self):
        variants = name_variants("Gabriel García Márquez")
        assert len(variants) == 1
        assert "gabriel garcia marquez" in variants


# ── 16B · scoring.py ─────────────────────────────────────────────────────────

class TestScoringEngine:
    def test_orcid_hint_match_gives_max_identifier_score(self):
        score, breakdown, evidence, status = compute_score(
            value="Garcia Marquez",
            authority_source="orcid",
            authority_id="0000-0001-1234-5678",
            canonical_label="Gabriel García Márquez",
            description="Researcher",
            orcid_hint="0000-0001-1234-5678",
        )
        assert breakdown["identifiers"] == 1.0
        assert "orcid_hint_matched" in evidence

    def test_orcid_source_without_hint_uses_quality_prior(self):
        score, breakdown, evidence, status = compute_score(
            value="some author",
            authority_source="orcid",
            authority_id="0000-0002-9999-0000",
            canonical_label="Some Author",
            description=None,
        )
        assert breakdown["identifiers"] == 0.90
        assert "orcid_hint_matched" not in evidence

    def test_name_normalization_improves_score_for_inverted_format(self):
        # VIAF returns 'García Márquez, Gabriel' (inverted), query is 'gabriel garcia marquez'
        score, breakdown, _, _ = compute_score(
            value="gabriel garcia marquez",
            authority_source="viaf",
            authority_id="viaf/95218065",
            canonical_label="García Márquez, Gabriel",
            description=None,
        )
        # After normalisation + reformatting, name score should be high
        assert breakdown["name"] >= 0.90

    def test_affiliation_context_adds_signal(self):
        # Use a description that explicitly contains the affiliation text
        score_no_ctx, bd_no, _, _ = compute_score(
            value="John Smith",
            authority_source="openalex",
            authority_id="A123",
            canonical_label="John Smith",
            description="Researcher — Universidad de Buenos Aires (30 works)",
        )
        score_ctx, bd_ctx, ev_ctx, _ = compute_score(
            value="John Smith",
            authority_source="openalex",
            authority_id="A123",
            canonical_label="John Smith",
            description="Researcher — Universidad de Buenos Aires (30 works)",
            affiliation="Universidad de Buenos Aires",
        )
        assert bd_ctx["affiliation"] > 0.0
        assert score_ctx > score_no_ctx
        assert any("affiliation_match" in e for e in ev_ctx)

    def test_resolution_status_exact_match_threshold(self):
        # Perfect name + ORCID hint → should be exact_match
        _, _, _, status = compute_score(
            value="john smith",
            authority_source="orcid",
            authority_id="0000-0001-0000-0001",
            canonical_label="John Smith",
            description=None,
            orcid_hint="0000-0001-0000-0001",
        )
        assert status == "exact_match"

    def test_resolution_status_unresolved_for_low_score(self):
        _, _, _, status = compute_score(
            value="xyz corporation",
            authority_source="dbpedia",
            authority_id="http://dbpedia.org/resource/Some_Entity",
            canonical_label="Completely Unrelated Entity",
            description=None,
        )
        assert status == "unresolved"

    def test_score_breakdown_has_all_five_signals(self):
        _, breakdown, _, _ = compute_score(
            value="test",
            authority_source="wikidata",
            authority_id="Q1",
            canonical_label="Test Entity",
            description=None,
        )
        for key in ("identifiers", "name", "affiliation", "coauthorship", "topic"):
            assert key in breakdown

    def test_coauthorship_and_topic_are_zero_placeholders(self):
        _, breakdown, _, _ = compute_score(
            value="test",
            authority_source="wikidata",
            authority_id="Q1",
            canonical_label="Test",
            description=None,
        )
        assert breakdown["coauthorship"] == 0.0
        assert breakdown["topic"] == 0.0


# ── 16C · resolver._deduplicate ──────────────────────────────────────────────

class TestDeduplication:
    def _make(self, source, label, authority_id="X1"):
        return AuthorityCandidate(
            authority_source=source,
            authority_id=authority_id,
            canonical_label=label,
        )

    def test_same_entity_different_sources_merged(self):
        c1 = self._make("wikidata",  "Gabriel García Márquez", "Q5878")
        c2 = self._make("viaf",      "García Márquez, Gabriel", "viaf/95218065")
        result = _deduplicate([c1, c2])
        assert len(result) == 1

    def test_higher_priority_source_wins(self):
        # orcid > viaf in _SOURCE_PRIORITY
        c_viaf  = self._make("viaf",  "John Smith", "viaf/123")
        c_orcid = self._make("orcid", "John Smith", "0000-0001-0000-0000")
        result = _deduplicate([c_viaf, c_orcid])
        assert len(result) == 1
        assert result[0].authority_source == "orcid"

    def test_merged_sources_recorded(self):
        c1 = self._make("wikidata", "Microsoft Corporation", "Q2283")
        c2 = self._make("dbpedia",  "Microsoft Corporation", "http://dbpedia.org/resource/Microsoft")
        result = _deduplicate([c1, c2])
        assert len(result) == 1
        assert len(result[0].merged_sources) == 1
        assert "dbpedia" in result[0].merged_sources[0]

    def test_different_entities_not_merged(self):
        c1 = self._make("wikidata", "Microsoft")
        c2 = self._make("wikidata", "Apple Inc.")
        result = _deduplicate([c1, c2])
        assert len(result) == 2

    def test_single_candidate_unchanged(self):
        c = self._make("wikidata", "Microsoft")
        result = _deduplicate([c])
        assert len(result) == 1

    def test_empty_list(self):
        assert _deduplicate([]) == []


# ── 16D · Endpoint /authority/resolve — campos Sprint 16 ────────────────────

def _candidate_with_score(**kwargs):
    """Create an AuthorityCandidate with Sprint-16 scoring fields pre-filled."""
    defaults = dict(
        authority_source="wikidata",
        authority_id="Q2283",
        canonical_label="Microsoft",
        description="Technology company",
        confidence=0.82,
        resolution_status="probable_match",
        score_breakdown={"identifiers": 0.55, "name": 0.80, "affiliation": 0.0, "coauthorship": 0.0, "topic": 0.0},
        evidence=["source_quality:wikidata=0.55", "name_score:0.800"],
        merged_sources=[],
    )
    defaults.update(kwargs)
    return AuthorityCandidate(**defaults)


class TestResolveEndpointSprint16:
    def test_response_includes_resolution_status(self, client, editor_headers, db_session):
        with patch(_MOCK_TARGET, return_value=[_candidate_with_score()]):
            resp = client.post("/authority/resolve", json={
                "field_name": "brand_capitalized",
                "value": "microsoft",
            }, headers=editor_headers)
        assert resp.status_code == 201
        r = resp.json()[0]
        assert "resolution_status" in r
        assert r["resolution_status"] == "probable_match"

    def test_response_includes_score_breakdown(self, client, editor_headers, db_session):
        with patch(_MOCK_TARGET, return_value=[_candidate_with_score()]):
            resp = client.post("/authority/resolve", json={
                "field_name": "brand_capitalized",
                "value": "microsoft",
            }, headers=editor_headers)
        r = resp.json()[0]
        assert "score_breakdown" in r
        bd = r["score_breakdown"]
        for key in ("identifiers", "name", "affiliation", "coauthorship", "topic"):
            assert key in bd

    def test_response_includes_evidence_list(self, client, editor_headers, db_session):
        with patch(_MOCK_TARGET, return_value=[_candidate_with_score()]):
            resp = client.post("/authority/resolve", json={
                "field_name": "brand_capitalized",
                "value": "microsoft",
            }, headers=editor_headers)
        r = resp.json()[0]
        assert "evidence" in r
        assert isinstance(r["evidence"], list)

    def test_response_includes_merged_sources(self, client, editor_headers, db_session):
        with patch(_MOCK_TARGET, return_value=[_candidate_with_score()]):
            resp = client.post("/authority/resolve", json={
                "field_name": "brand_capitalized",
                "value": "microsoft",
            }, headers=editor_headers)
        r = resp.json()[0]
        assert "merged_sources" in r
        assert isinstance(r["merged_sources"], list)


# ── 16E · Context fields accepted in request ────────────────────────────────

class TestContextFields:
    def test_context_fields_accepted_in_request(self, client, editor_headers, db_session):
        with patch(_MOCK_TARGET, return_value=[]):
            resp = client.post("/authority/resolve", json={
                "field_name": "author_name",
                "value": "garcia marquez",
                "entity_type": "person",
                "context_affiliation": "Universidad Nacional de Colombia",
                "context_orcid_hint": "0000-0001-1234-5678",
                "context_doi": "10.1000/xyz123",
                "context_year": 1967,
            }, headers=editor_headers)
        assert resp.status_code == 201

    def test_invalid_context_year_rejected(self, client, editor_headers):
        with patch(_MOCK_TARGET, return_value=[]):
            resp = client.post("/authority/resolve", json={
                "field_name": "author_name",
                "value": "test",
                "context_year": 999,  # below ge=1000
            }, headers=editor_headers)
        assert resp.status_code == 422


# ── 16F · GET /authority/metrics ────────────────────────────────────────────

class TestMetricsEndpoint:
    def test_no_auth_returns_401(self, client):
        assert client.get("/authority/metrics").status_code == 401

    def test_viewer_can_access_metrics(self, client, viewer_headers):
        resp = client.get("/authority/metrics", headers=viewer_headers)
        assert resp.status_code == 200

    def test_metrics_shape(self, client, auth_headers):
        resp = client.get("/authority/metrics", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        for key in ("total_records", "by_status", "by_resolution_status",
                    "by_source", "avg_confidence", "confirm_rate", "reject_rate"):
            assert key in data

    def test_metrics_totals_are_consistent(self, client, editor_headers, auth_headers, db_session):
        with patch(_MOCK_TARGET, return_value=[_candidate_with_score(), _candidate_with_score(
            authority_source="viaf", authority_id="viaf/123", canonical_label="Microsofte",
            resolution_status="ambiguous",
        )]):
            client.post("/authority/resolve", json={
                "field_name": "brand_capitalized", "value": "microsoft",
            }, headers=editor_headers)

        resp = client.get("/authority/metrics", headers=auth_headers)
        data = resp.json()
        assert data["total_records"] >= 2
        total_by_status = sum(data["by_status"].values())
        assert total_by_status == data["total_records"]

    def test_confirm_rate_updates_after_confirm(self, client, editor_headers, auth_headers, db_session):
        with patch(_MOCK_TARGET, return_value=[_candidate_with_score()]):
            res = client.post("/authority/resolve", json={
                "field_name": "brand_capitalized", "value": "microsoft",
            }, headers=editor_headers)
        rid = res.json()[0]["id"]
        client.post(f"/authority/records/{rid}/confirm",
                    json={"also_create_rule": False}, headers=editor_headers)
        metrics = client.get("/authority/metrics", headers=auth_headers).json()
        assert metrics["confirm_rate"] > 0.0
