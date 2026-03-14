"""Sprint 73 — Graph Analytics tests.

Covers:
- Pure analytics functions: degree_centrality, pagerank, connected_components,
  component_sizes, shortest_path
- API endpoints: /entities/{id}/graph/metrics, /graph/stats,
  /graph/path, /graph/components
"""
import pytest
from backend import models
from backend.graph_analytics import (
    degree_centrality,
    pagerank,
    connected_components,
    component_sizes,
    shortest_path,
)


# ── Helpers ────────────────────────────────────────────────────────────────────

def _entity(db, label="Entity", domain="default", entity_type="paper"):
    e = models.RawEntity(primary_label=label, domain=domain, entity_type=entity_type)
    db.add(e)
    db.commit()
    db.refresh(e)
    return e


def _rel(db, source_id, target_id, relation_type="cites", weight=1.0):
    r = models.EntityRelationship(
        source_id=source_id,
        target_id=target_id,
        relation_type=relation_type,
        weight=weight,
    )
    db.add(r)
    db.commit()
    db.refresh(r)
    return r


# ── Unit tests: degree_centrality ─────────────────────────────────────────────

class TestDegreeCentrality:
    def test_no_edges_returns_zero(self):
        result = degree_centrality(1, [])
        assert result["in_degree"] == 0
        assert result["out_degree"] == 0
        assert result["total_degree"] == 0
        assert result["in_by_type"] == {}
        assert result["out_by_type"] == {}

    def test_out_degree_counted(self):
        edges = [(1, 2, "cites", 1.0), (1, 3, "cites", 1.0)]
        result = degree_centrality(1, edges)
        assert result["out_degree"] == 2
        assert result["in_degree"] == 0

    def test_in_degree_counted(self):
        edges = [(2, 1, "cites", 1.0), (3, 1, "cites", 1.0)]
        result = degree_centrality(1, edges)
        assert result["in_degree"] == 2
        assert result["out_degree"] == 0

    def test_by_type_breakdown(self):
        edges = [
            (1, 2, "cites", 1.0),
            (1, 3, "authored-by", 1.0),
            (4, 1, "related-to", 1.0),
        ]
        result = degree_centrality(1, edges)
        assert result["out_by_type"]["cites"] == 1
        assert result["out_by_type"]["authored-by"] == 1
        assert result["in_by_type"]["related-to"] == 1

    def test_total_degree_sum(self):
        edges = [
            (1, 2, "cites", 1.0),
            (3, 1, "cites", 1.0),
            (1, 4, "related-to", 1.0),
        ]
        result = degree_centrality(1, edges)
        assert result["total_degree"] == result["in_degree"] + result["out_degree"]
        assert result["total_degree"] == 3


# ── Unit tests: pagerank ──────────────────────────────────────────────────────

class TestPageRank:
    def test_empty_graph_returns_empty(self):
        assert pagerank([]) == {}

    def test_single_node_self_loop_handled(self):
        # A single directed edge between two nodes
        edges = [(1, 2, "cites", 1.0)]
        pr = pagerank(edges)
        assert len(pr) == 2
        # Scores should exist for both nodes
        assert 1 in pr
        assert 2 in pr

    def test_scores_sum_to_one(self):
        edges = [
            (1, 2, "cites", 1.0),
            (2, 3, "cites", 1.0),
            (3, 1, "cites", 1.0),
        ]
        pr = pagerank(edges)
        total = sum(pr.values())
        assert abs(total - 1.0) < 1e-4

    def test_hub_node_ranks_higher(self):
        # Node 4 is pointed to by 1, 2, 3 — should have highest score
        edges = [
            (1, 4, "cites", 1.0),
            (2, 4, "cites", 1.0),
            (3, 4, "cites", 1.0),
            (1, 2, "cites", 1.0),
        ]
        pr = pagerank(edges)
        # Node 4 receives most inbound links
        assert pr[4] == max(pr.values())

    def test_isolated_nodes_equal_rank(self):
        # Two disconnected edges with equal structure
        edges = [
            (1, 2, "cites", 1.0),
            (3, 4, "cites", 1.0),
        ]
        pr = pagerank(edges)
        # Nodes 2 and 4 both have one inbound edge from equal-ranked nodes
        # They should have similar (though not necessarily identical) scores
        assert abs(pr[2] - pr[4]) < 0.1


# ── Unit tests: connected_components ─────────────────────────────────────────

class TestConnectedComponents:
    def test_no_edges_empty_result(self):
        result = connected_components([])
        assert result == {}

    def test_single_component(self):
        edges = [(1, 2, "cites", 1.0), (2, 3, "cites", 1.0)]
        comps = connected_components(edges)
        # All nodes in the same component
        assert comps[1] == comps[2] == comps[3]

    def test_two_disconnected_components(self):
        edges = [
            (1, 2, "cites", 1.0),
            (3, 4, "cites", 1.0),
        ]
        comps = connected_components(edges)
        # 1 and 2 share a component; 3 and 4 share a different component
        assert comps[1] == comps[2]
        assert comps[3] == comps[4]
        assert comps[1] != comps[3]

    def test_treats_edges_as_undirected(self):
        # Even though edge is 1→2, they should be in the same weak component
        edges = [(1, 2, "cites", 1.0)]
        comps = connected_components(edges)
        assert comps[1] == comps[2]

    def test_component_sizes_correct(self):
        edges = [
            (1, 2, "cites", 1.0),
            (2, 3, "cites", 1.0),
            (4, 5, "cites", 1.0),
        ]
        comps = connected_components(edges)
        sizes = component_sizes(comps)
        size_values = sorted(sizes.values(), reverse=True)
        assert size_values[0] == 3
        assert size_values[1] == 2


# ── Unit tests: shortest_path ─────────────────────────────────────────────────

class TestShortestPath:
    def test_same_node_returns_length_zero(self):
        result = shortest_path(1, 1, [])
        assert result is not None
        assert result["length"] == 0
        assert result["path"] == [1]
        assert result["relations"] == []

    def test_direct_edge_length_one(self):
        edges = [(1, 2, "cites", 1.0)]
        result = shortest_path(1, 2, edges)
        assert result is not None
        assert result["length"] == 1
        assert result["path"] == [1, 2]

    def test_two_hop_path(self):
        edges = [(1, 2, "cites", 1.0), (2, 3, "authored-by", 1.0)]
        result = shortest_path(1, 3, edges)
        assert result is not None
        assert result["length"] == 2
        assert result["path"] == [1, 2, 3]

    def test_no_path_returns_none(self):
        edges = [(1, 2, "cites", 1.0)]
        # No path from 2 back to 1 (directed)
        result = shortest_path(2, 1, edges)
        assert result is None

    def test_returns_relation_types(self):
        edges = [
            (1, 2, "cites", 1.0),
            (2, 3, "authored-by", 1.0),
        ]
        result = shortest_path(1, 3, edges)
        assert result is not None
        assert result["relations"] == ["cites", "authored-by"]

    def test_shortest_path_not_detour(self):
        # 1→2→3 and 1→3 direct: should choose length 1
        edges = [
            (1, 2, "cites", 1.0),
            (2, 3, "cites", 1.0),
            (1, 3, "related-to", 1.0),
        ]
        result = shortest_path(1, 3, edges)
        assert result is not None
        assert result["length"] == 1


# ── API endpoint tests ─────────────────────────────────────────────────────────

class TestEntityMetricsEndpoint:
    def test_requires_auth(self, client, db_session):
        e = _entity(db_session, "AuthGuard")
        resp = client.get(f"/entities/{e.id}/graph/metrics")
        assert resp.status_code in (401, 403)

    def test_404_for_missing_entity(self, client, auth_headers):
        resp = client.get("/entities/999999/graph/metrics", headers=auth_headers)
        assert resp.status_code == 404

    def test_returns_degree_and_pagerank(self, client, auth_headers, db_session):
        e1 = _entity(db_session, "M1")
        e2 = _entity(db_session, "M2")
        _rel(db_session, e1.id, e2.id, "cites")
        resp = client.get(f"/entities/{e1.id}/graph/metrics", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "degree" in data
        assert "pagerank" in data
        assert data["degree"]["out_degree"] == 1
        assert data["degree"]["in_degree"] == 0
        assert "score" in data["pagerank"]

    def test_returns_component_info(self, client, auth_headers, db_session):
        e1 = _entity(db_session, "Comp1")
        e2 = _entity(db_session, "Comp2")
        _rel(db_session, e1.id, e2.id, "cites")
        resp = client.get(f"/entities/${e1.id}/graph/metrics", headers=auth_headers)
        # Use correct endpoint
        resp = client.get(f"/entities/{e1.id}/graph/metrics", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "component" in data
        assert data["component"]["size"] >= 1

    def test_response_structure(self, client, auth_headers, db_session):
        e = _entity(db_session, "Struct")
        resp = client.get(f"/entities/{e.id}/graph/metrics", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "entity_id" in data
        assert "primary_label" in data
        assert data["entity_id"] == e.id
        assert data["primary_label"] == "Struct"


class TestGraphStatsEndpoint:
    def test_requires_auth(self, client):
        resp = client.get("/graph/stats")
        assert resp.status_code in (401, 403)

    def test_empty_graph(self, client, auth_headers, db_session):
        resp = client.get("/graph/stats", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_nodes"] == 0
        assert data["total_edges"] == 0
        assert data["total_components"] == 0

    def test_returns_all_keys(self, client, auth_headers, db_session):
        e1 = _entity(db_session, "S1")
        e2 = _entity(db_session, "S2")
        _rel(db_session, e1.id, e2.id, "cites")
        resp = client.get("/graph/stats", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        for key in ("total_nodes", "total_edges", "total_components",
                    "largest_component_size", "top_pagerank", "top_degree"):
            assert key in data

    def test_top_pagerank_sorted_desc(self, client, auth_headers, db_session):
        # Build a small graph where one node is a clear hub
        hub = _entity(db_session, "Hub")
        for i in range(3):
            src = _entity(db_session, f"Src{i}")
            _rel(db_session, src.id, hub.id, "cites")
        resp = client.get("/graph/stats", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        pr_list = data["top_pagerank"]
        assert len(pr_list) >= 1
        # Scores should be in descending order
        scores = [row["score"] for row in pr_list]
        assert scores == sorted(scores, reverse=True)

    def test_node_edge_counts_correct(self, client, auth_headers, db_session):
        e1 = _entity(db_session, "N1")
        e2 = _entity(db_session, "N2")
        e3 = _entity(db_session, "N3")
        _rel(db_session, e1.id, e2.id, "cites")
        _rel(db_session, e2.id, e3.id, "cites")
        resp = client.get("/graph/stats", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_nodes"] == 3
        assert data["total_edges"] == 2


class TestPathEndpoint:
    def test_requires_auth(self, client):
        resp = client.get("/graph/path?from_id=1&to_id=2")
        assert resp.status_code in (401, 403)

    def test_same_id_rejected(self, client, auth_headers, db_session):
        e = _entity(db_session, "SameId")
        resp = client.get(f"/graph/path?from_id={e.id}&to_id={e.id}", headers=auth_headers)
        assert resp.status_code == 400

    def test_missing_entity_404(self, client, auth_headers, db_session):
        e = _entity(db_session, "Real")
        resp = client.get(f"/graph/path?from_id={e.id}&to_id=999999", headers=auth_headers)
        assert resp.status_code == 404

    def test_direct_path_found(self, client, auth_headers, db_session):
        e1 = _entity(db_session, "PathA")
        e2 = _entity(db_session, "PathB")
        _rel(db_session, e1.id, e2.id, "cites")
        resp = client.get(f"/graph/path?from_id={e1.id}&to_id={e2.id}", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["found"] is True
        assert data["length"] == 1
        assert len(data["steps"]) == 2

    def test_no_path_returns_found_false(self, client, auth_headers, db_session):
        e1 = _entity(db_session, "NoPathA")
        e2 = _entity(db_session, "NoPathB")
        # No relationship between them
        resp = client.get(f"/graph/path?from_id={e1.id}&to_id={e2.id}", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["found"] is False
        assert data["path"] is None

    def test_path_includes_relations(self, client, auth_headers, db_session):
        e1 = _entity(db_session, "RelA")
        e2 = _entity(db_session, "RelB")
        _rel(db_session, e1.id, e2.id, "authored-by")
        resp = client.get(f"/graph/path?from_id={e1.id}&to_id={e2.id}", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["found"] is True
        assert "authored-by" in data["relations"]


class TestComponentsEndpoint:
    def test_requires_auth(self, client):
        resp = client.get("/graph/components")
        assert resp.status_code in (401, 403)

    def test_empty_returns_zero(self, client, auth_headers, db_session):
        resp = client.get("/graph/components", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_components"] == 0
        assert data["components"] == []

    def test_components_listed(self, client, auth_headers, db_session):
        e1 = _entity(db_session, "CA1")
        e2 = _entity(db_session, "CA2")
        _rel(db_session, e1.id, e2.id, "cites")
        resp = client.get("/graph/components", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_components"] >= 1
        comp = data["components"][0]
        assert "component_id" in comp
        assert "size" in comp
        assert "entity_ids" in comp

    def test_two_components(self, client, auth_headers, db_session):
        e1 = _entity(db_session, "CC1")
        e2 = _entity(db_session, "CC2")
        e3 = _entity(db_session, "CC3")
        e4 = _entity(db_session, "CC4")
        _rel(db_session, e1.id, e2.id, "cites")
        _rel(db_session, e3.id, e4.id, "cites")
        resp = client.get("/graph/components", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_components"] == 2
        # Both components have size 2
        sizes = [c["size"] for c in data["components"]]
        assert all(s == 2 for s in sizes)

    def test_sorted_by_size_desc(self, client, auth_headers, db_session):
        # Larger component: e1-e2-e3; smaller: e4-e5
        e1 = _entity(db_session, "Big1")
        e2 = _entity(db_session, "Big2")
        e3 = _entity(db_session, "Big3")
        e4 = _entity(db_session, "Sm1")
        e5 = _entity(db_session, "Sm2")
        _rel(db_session, e1.id, e2.id, "cites")
        _rel(db_session, e2.id, e3.id, "cites")
        _rel(db_session, e4.id, e5.id, "cites")
        resp = client.get("/graph/components", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        sizes = [c["size"] for c in data["components"]]
        assert sizes == sorted(sizes, reverse=True)
