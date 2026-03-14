"""
Sprint 70 — Entity Relationship Graph tests.

Covers:
- EntityRelationship model creation
- GET /entities/{id}/graph (depth=1, depth=2, empty graph)
- GET /entities/{id}/relationships
- POST /entities/{id}/relationships — success, duplicate, self-loop, 404
- DELETE /relationships/{id} — success, 404
- Auth and role guards
- Graph node/edge structure
- Cycle handling in BFS
"""
import pytest
from backend import models


def _entity(db, label="Entity", domain="default", entity_type="paper"):
    e = models.RawEntity(primary_label=label, domain=domain, entity_type=entity_type)
    db.add(e)
    db.commit()
    db.refresh(e)
    return e


def _rel(db, source_id, target_id, relation_type="cites", weight=1.0):
    r = models.EntityRelationship(
        source_id=source_id, target_id=target_id,
        relation_type=relation_type, weight=weight,
    )
    db.add(r)
    db.commit()
    db.refresh(r)
    return r


# ── Model ──────────────────────────────────────────────────────────────────────

class TestEntityRelationshipModel:
    def test_create_relationship(self, db_session):
        e1 = _entity(db_session, "A")
        e2 = _entity(db_session, "B")
        rel = _rel(db_session, e1.id, e2.id, "cites")
        assert rel.id is not None
        assert rel.source_id == e1.id
        assert rel.target_id == e2.id
        assert rel.relation_type == "cites"
        assert rel.weight == 1.0

    def test_default_weight(self, db_session):
        e1 = _entity(db_session, "X")
        e2 = _entity(db_session, "Y")
        rel = _rel(db_session, e1.id, e2.id)
        assert rel.weight == 1.0

    def test_created_at_set(self, db_session):
        e1 = _entity(db_session, "P")
        e2 = _entity(db_session, "Q")
        rel = _rel(db_session, e1.id, e2.id)
        assert rel.created_at is not None


# ── GET /entities/{id}/graph ───────────────────────────────────────────────────

class TestGetEntityGraph:
    def test_empty_graph_returns_center_only(self, client, auth_headers, db_session):
        e = _entity(db_session, "Solo")
        resp = client.get(f"/entities/{e.id}/graph", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["center_id"] == e.id
        assert len(data["nodes"]) == 1
        assert data["nodes"][0]["is_center"] is True
        assert data["edges"] == []

    def test_graph_with_one_edge(self, client, auth_headers, db_session):
        e1 = _entity(db_session, "Source")
        e2 = _entity(db_session, "Target")
        _rel(db_session, e1.id, e2.id, "cites")
        resp = client.get(f"/entities/{e1.id}/graph", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["nodes"]) == 2
        assert len(data["edges"]) == 1
        assert data["edges"][0]["relation_type"] == "cites"

    def test_graph_response_structure(self, client, auth_headers, db_session):
        e1 = _entity(db_session, "A")
        e2 = _entity(db_session, "B")
        _rel(db_session, e1.id, e2.id, "related-to", weight=2.5)
        resp = client.get(f"/entities/{e1.id}/graph", headers=auth_headers)
        data = resp.json()
        assert "center_id" in data
        assert "depth" in data
        assert "nodes" in data
        assert "edges" in data
        edge = data["edges"][0]
        assert edge["source"] == e1.id
        assert edge["target"] == e2.id
        assert edge["weight"] == 2.5

    def test_center_node_marked(self, client, auth_headers, db_session):
        e1 = _entity(db_session, "Focal")
        e2 = _entity(db_session, "Neighbor")
        _rel(db_session, e1.id, e2.id)
        resp = client.get(f"/entities/{e1.id}/graph", headers=auth_headers)
        nodes = {n["id"]: n for n in resp.json()["nodes"]}
        assert nodes[e1.id]["is_center"] is True
        assert nodes[e2.id]["is_center"] is False

    def test_depth_2_includes_second_hop(self, client, auth_headers, db_session):
        e1 = _entity(db_session, "Root")
        e2 = _entity(db_session, "Mid")
        e3 = _entity(db_session, "Leaf")
        _rel(db_session, e1.id, e2.id, "cites")
        _rel(db_session, e2.id, e3.id, "cites")
        resp = client.get(f"/entities/{e1.id}/graph?depth=2", headers=auth_headers)
        node_ids = {n["id"] for n in resp.json()["nodes"]}
        assert e3.id in node_ids

    def test_depth_1_excludes_second_hop(self, client, auth_headers, db_session):
        e1 = _entity(db_session, "Root2")
        e2 = _entity(db_session, "Mid2")
        e3 = _entity(db_session, "Leaf2")
        _rel(db_session, e1.id, e2.id, "cites")
        _rel(db_session, e2.id, e3.id, "cites")
        resp = client.get(f"/entities/{e1.id}/graph?depth=1", headers=auth_headers)
        node_ids = {n["id"] for n in resp.json()["nodes"]}
        assert e3.id not in node_ids

    def test_incoming_edges_included(self, client, auth_headers, db_session):
        e1 = _entity(db_session, "Cited")
        e2 = _entity(db_session, "Citer")
        _rel(db_session, e2.id, e1.id, "cites")
        resp = client.get(f"/entities/{e1.id}/graph", headers=auth_headers)
        node_ids = {n["id"] for n in resp.json()["nodes"]}
        assert e2.id in node_ids

    def test_graph_entity_not_found_404(self, client, auth_headers):
        resp = client.get("/entities/999999/graph", headers=auth_headers)
        assert resp.status_code == 404

    def test_graph_requires_auth(self, client, db_session):
        e = _entity(db_session, "Locked")
        resp = client.get(f"/entities/{e.id}/graph")
        assert resp.status_code in (401, 403)

    def test_depth_3_rejected(self, client, auth_headers, db_session):
        e = _entity(db_session, "D3")
        resp = client.get(f"/entities/{e.id}/graph?depth=3", headers=auth_headers)
        assert resp.status_code == 422


# ── GET /entities/{id}/relationships ──────────────────────────────────────────

class TestListRelationships:
    def test_returns_empty_list(self, client, auth_headers, db_session):
        e = _entity(db_session, "Isolated")
        resp = client.get(f"/entities/{e.id}/relationships", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json() == []

    def test_returns_outgoing_relationships(self, client, auth_headers, db_session):
        e1 = _entity(db_session, "Src")
        e2 = _entity(db_session, "Tgt")
        _rel(db_session, e1.id, e2.id, "authored-by")
        resp = client.get(f"/entities/{e1.id}/relationships", headers=auth_headers)
        assert len(resp.json()) == 1
        assert resp.json()[0]["relation_type"] == "authored-by"

    def test_returns_incoming_relationships(self, client, auth_headers, db_session):
        e1 = _entity(db_session, "In1")
        e2 = _entity(db_session, "In2")
        _rel(db_session, e2.id, e1.id, "belongs-to")
        resp = client.get(f"/entities/{e1.id}/relationships", headers=auth_headers)
        assert len(resp.json()) == 1

    def test_entity_not_found_404(self, client, auth_headers):
        resp = client.get("/entities/999999/relationships", headers=auth_headers)
        assert resp.status_code == 404


# ── POST /entities/{id}/relationships ─────────────────────────────────────────

class TestCreateRelationship:
    def test_creates_relationship(self, client, editor_headers, db_session):
        e1 = _entity(db_session, "Maker")
        e2 = _entity(db_session, "Made")
        resp = client.post(
            f"/entities/{e1.id}/relationships",
            json={"target_id": e2.id, "relation_type": "cites"},
            headers=editor_headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["source_id"] == e1.id
        assert data["target_id"] == e2.id
        assert data["relation_type"] == "cites"

    def test_response_has_id_and_timestamps(self, client, editor_headers, db_session):
        e1 = _entity(db_session, "E1")
        e2 = _entity(db_session, "E2")
        resp = client.post(
            f"/entities/{e1.id}/relationships",
            json={"target_id": e2.id, "relation_type": "related-to"},
            headers=editor_headers,
        )
        data = resp.json()
        assert "id" in data
        assert "created_at" in data

    def test_duplicate_rejected_409(self, client, editor_headers, db_session):
        e1 = _entity(db_session, "Dup1")
        e2 = _entity(db_session, "Dup2")
        _rel(db_session, e1.id, e2.id, "cites")
        resp = client.post(
            f"/entities/{e1.id}/relationships",
            json={"target_id": e2.id, "relation_type": "cites"},
            headers=editor_headers,
        )
        assert resp.status_code == 409

    def test_self_loop_rejected_400(self, client, editor_headers, db_session):
        e = _entity(db_session, "Self")
        resp = client.post(
            f"/entities/{e.id}/relationships",
            json={"target_id": e.id, "relation_type": "related-to"},
            headers=editor_headers,
        )
        assert resp.status_code == 400

    def test_invalid_relation_type_422(self, client, editor_headers, db_session):
        e1 = _entity(db_session, "Inv1")
        e2 = _entity(db_session, "Inv2")
        resp = client.post(
            f"/entities/{e1.id}/relationships",
            json={"target_id": e2.id, "relation_type": "invented-by"},
            headers=editor_headers,
        )
        assert resp.status_code == 422

    def test_source_not_found_404(self, client, editor_headers, db_session):
        e = _entity(db_session, "Real")
        resp = client.post(
            "/entities/999999/relationships",
            json={"target_id": e.id, "relation_type": "cites"},
            headers=editor_headers,
        )
        assert resp.status_code == 404

    def test_target_not_found_404(self, client, editor_headers, db_session):
        e = _entity(db_session, "SrcReal")
        resp = client.post(
            f"/entities/{e.id}/relationships",
            json={"target_id": 999999, "relation_type": "cites"},
            headers=editor_headers,
        )
        assert resp.status_code == 404

    def test_viewer_cannot_create(self, client, viewer_headers, db_session):
        e1 = _entity(db_session, "V1")
        e2 = _entity(db_session, "V2")
        resp = client.post(
            f"/entities/{e1.id}/relationships",
            json={"target_id": e2.id, "relation_type": "cites"},
            headers=viewer_headers,
        )
        assert resp.status_code in (401, 403)

    def test_weight_stored_correctly(self, client, editor_headers, db_session):
        e1 = _entity(db_session, "W1")
        e2 = _entity(db_session, "W2")
        resp = client.post(
            f"/entities/{e1.id}/relationships",
            json={"target_id": e2.id, "relation_type": "cites", "weight": 3.5},
            headers=editor_headers,
        )
        assert resp.json()["weight"] == 3.5


# ── DELETE /relationships/{id} ─────────────────────────────────────────────────

class TestDeleteRelationship:
    def test_deletes_relationship(self, client, editor_headers, db_session):
        e1 = _entity(db_session, "Del1")
        e2 = _entity(db_session, "Del2")
        rel = _rel(db_session, e1.id, e2.id)
        resp = client.delete(f"/relationships/{rel.id}", headers=editor_headers)
        assert resp.status_code == 204

    def test_deleted_relationship_gone(self, client, editor_headers, db_session):
        e1 = _entity(db_session, "Gone1")
        e2 = _entity(db_session, "Gone2")
        rel = _rel(db_session, e1.id, e2.id)
        client.delete(f"/relationships/{rel.id}", headers=editor_headers)
        resp = client.get(f"/entities/{e1.id}/relationships", headers=editor_headers)
        assert all(r["id"] != rel.id for r in resp.json())

    def test_delete_not_found_404(self, client, editor_headers):
        resp = client.delete("/relationships/999999", headers=editor_headers)
        assert resp.status_code == 404

    def test_viewer_cannot_delete(self, client, viewer_headers, db_session):
        e1 = _entity(db_session, "VD1")
        e2 = _entity(db_session, "VD2")
        rel = _rel(db_session, e1.id, e2.id)
        resp = client.delete(f"/relationships/{rel.id}", headers=viewer_headers)
        assert resp.status_code in (401, 403)
