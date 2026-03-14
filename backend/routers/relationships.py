"""
Sprint 70 — Entity Relationship Graph
  GET  /entities/{id}/graph            — graph: nodes + edges up to depth N
  GET  /entities/{id}/relationships    — list direct relationships
  POST /entities/{id}/relationships    — create a new relationship
  DELETE /relationships/{rel_id}       — delete a relationship

Sprint 73 — Graph Analytics
  GET  /entities/{id}/graph/metrics    — degree, PageRank, component info
  GET  /graph/stats                    — global graph statistics
  GET  /graph/path                     — BFS shortest path
  GET  /graph/components               — list connected components
"""
import logging
from collections import defaultdict, deque
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from sqlalchemy.orm import Session

from backend import graph_analytics, models, schemas
from backend.auth import get_current_user, require_role
from backend.database import get_db

logger = logging.getLogger(__name__)

router = APIRouter(tags=["relationships"])


def _get_entity_or_404(entity_id: int, db: Session) -> models.RawEntity:
    entity = db.get(models.RawEntity, entity_id)
    if not entity:
        raise HTTPException(status_code=404, detail=f"Entity {entity_id} not found")
    return entity


@router.get("/graph/stats")
def get_graph_stats(
    db: Session = Depends(get_db),
    _: models.User = Depends(get_current_user),
):
    """Sprint 73 — Global graph statistics: nodes, edges, components, top PageRank."""
    edges = graph_analytics.fetch_edges(db)

    if not edges:
        return {
            "total_nodes": 0, "total_edges": 0,
            "total_components": 0, "largest_component_size": 0,
            "top_pagerank": [], "top_degree": [],
        }

    nodes: set[int] = set()
    for src, dst, _, _ in edges:
        nodes.add(src)
        nodes.add(dst)

    components = graph_analytics.connected_components(edges)
    sizes = graph_analytics.component_sizes(components)

    pr = graph_analytics.pagerank(edges)
    top_pr = sorted(pr.items(), key=lambda x: x[1], reverse=True)[:10]

    # Top by total degree
    degree_map: dict[int, int] = {}
    for node in nodes:
        d = graph_analytics.degree_centrality(node, edges)
        degree_map[node] = d["total_degree"]
    top_degree = sorted(degree_map.items(), key=lambda x: x[1], reverse=True)[:10]

    # Resolve labels for top nodes
    top_ids = {nid for nid, _ in top_pr + top_degree}
    label_map = {
        e.id: e.primary_label
        for e in db.query(models.RawEntity).filter(models.RawEntity.id.in_(top_ids)).all()
    }

    return {
        "total_nodes":            len(nodes),
        "total_edges":            len(edges),
        "total_components":       len(sizes),
        "largest_component_size": max(sizes.values()) if sizes else 0,
        "top_pagerank": [
            {"entity_id": nid, "primary_label": label_map.get(nid), "score": score}
            for nid, score in top_pr
        ],
        "top_degree": [
            {"entity_id": nid, "primary_label": label_map.get(nid), "total_degree": deg}
            for nid, deg in top_degree
        ],
    }


@router.get("/graph/path")
def get_shortest_path(
    from_id: int = Query(..., ge=1),
    to_id:   int = Query(..., ge=1),
    db: Session = Depends(get_db),
    _: models.User = Depends(get_current_user),
):
    """Sprint 73 — BFS shortest path between two entities (directed)."""
    if from_id == to_id:
        raise HTTPException(status_code=400, detail="from_id and to_id must be different")

    # Verify both entities exist
    for eid in (from_id, to_id):
        if not db.query(models.RawEntity).filter(models.RawEntity.id == eid).first():
            raise HTTPException(status_code=404, detail=f"Entity {eid} not found")

    edges = graph_analytics.fetch_edges(db)
    result = graph_analytics.shortest_path(from_id, to_id, edges)

    if result is None:
        return {"found": False, "from_id": from_id, "to_id": to_id, "path": None}

    # Resolve labels
    path_ids = result["path"]
    label_map = {
        e.id: e.primary_label
        for e in db.query(models.RawEntity).filter(models.RawEntity.id.in_(path_ids)).all()
    }
    steps = [
        {"entity_id": pid, "primary_label": label_map.get(pid)}
        for pid in path_ids
    ]

    return {
        "found":     True,
        "from_id":   from_id,
        "to_id":     to_id,
        "length":    result["length"],
        "relations": result["relations"],
        "steps":     steps,
    }


@router.get("/graph/components")
def get_graph_components(
    db: Session = Depends(get_db),
    _: models.User = Depends(get_current_user),
):
    """Sprint 73 — List all weakly connected components with sizes and member IDs."""
    edges = graph_analytics.fetch_edges(db)

    if not edges:
        return {"total_components": 0, "components": []}

    node_to_comp = graph_analytics.connected_components(edges)
    sizes = graph_analytics.component_sizes(node_to_comp)

    # Group nodes by component
    comp_members: dict[int, list[int]] = defaultdict(list)
    for node_id, comp_id in node_to_comp.items():
        comp_members[comp_id].append(node_id)

    # Sort by size descending
    sorted_comps = sorted(sizes.items(), key=lambda x: x[1], reverse=True)

    return {
        "total_components": len(sizes),
        "components": [
            {
                "component_id": comp_id,
                "size": size,
                "entity_ids": sorted(comp_members[comp_id]),
            }
            for comp_id, size in sorted_comps
        ],
    }


@router.get("/entities/{entity_id}/graph/metrics")
def get_entity_graph_metrics(
    entity_id: int = Path(..., ge=1),
    db: Session = Depends(get_db),
    _: models.User = Depends(get_current_user),
):
    """
    Sprint 73 — Return graph analytics metrics for a single entity:
    degree centrality, PageRank score, connected component info.
    """
    entity = db.query(models.RawEntity).filter(models.RawEntity.id == entity_id).first()
    if not entity:
        raise HTTPException(status_code=404, detail="Entity not found")

    edges = graph_analytics.fetch_edges(db)

    # Degree
    degree = graph_analytics.degree_centrality(entity_id, edges)

    # PageRank
    pr = graph_analytics.pagerank(edges)
    pr_score = pr.get(entity_id, 0.0)
    # Rank position
    sorted_pr = sorted(pr.items(), key=lambda x: x[1], reverse=True)
    pr_rank = next((i + 1 for i, (nid, _) in enumerate(sorted_pr) if nid == entity_id), None)

    # Components
    components = graph_analytics.connected_components(edges)
    sizes = graph_analytics.component_sizes(components)
    comp_id = components.get(entity_id)
    comp_size = sizes.get(comp_id, 0) if comp_id is not None else 0

    return {
        "entity_id":       entity_id,
        "primary_label":   entity.primary_label,
        "degree":          degree,
        "pagerank": {
            "score":        round(pr_score, 6),
            "rank":         pr_rank,
            "total_nodes":  len(pr),
        },
        "component": {
            "component_id": comp_id,
            "size":         comp_size,
        },
    }


@router.get("/entities/{entity_id}/graph", response_model=schemas.EntityGraphResponse)
def get_entity_graph(
    entity_id: int = Path(..., ge=1),
    depth: int = Query(default=1, ge=1, le=2),
    db: Session = Depends(get_db),
    _: models.User = Depends(get_current_user),
):
    """
    Return a subgraph centered on entity_id.
    depth=1 → direct neighbors only.
    depth=2 → neighbors + their neighbors (capped at 50 nodes total).
    """
    _get_entity_or_404(entity_id, db)

    visited_ids = set()
    queue = deque([(entity_id, 0)])
    collected_edges: List[models.EntityRelationship] = []
    NODE_CAP = 50

    while queue and len(visited_ids) < NODE_CAP:
        current_id, current_depth = queue.popleft()
        if current_id in visited_ids:
            continue
        visited_ids.add(current_id)

        if current_depth >= depth:
            continue

        # Edges where this node is source or target
        rels = (
            db.query(models.EntityRelationship)
            .filter(
                (models.EntityRelationship.source_id == current_id)
                | (models.EntityRelationship.target_id == current_id)
            )
            .all()
        )
        for rel in rels:
            collected_edges.append(rel)
            neighbor = rel.target_id if rel.source_id == current_id else rel.source_id
            if neighbor not in visited_ids and len(visited_ids) < NODE_CAP:
                queue.append((neighbor, current_depth + 1))

    # Deduplicate edges
    seen_edge_ids = set()
    unique_edges = []
    for e in collected_edges:
        if e.id not in seen_edge_ids:
            seen_edge_ids.add(e.id)
            unique_edges.append(e)

    # Only include edges where BOTH endpoints are in visited_ids
    final_edges = [
        e for e in unique_edges
        if e.source_id in visited_ids and e.target_id in visited_ids
    ]

    # Fetch node data
    entities = db.query(models.RawEntity).filter(models.RawEntity.id.in_(visited_ids)).all()
    entity_map = {e.id: e for e in entities}

    nodes = [
        schemas.GraphNode(
            id=eid,
            label=entity_map[eid].primary_label or f"Entity #{eid}" if eid in entity_map else f"Entity #{eid}",
            entity_type=entity_map[eid].entity_type if eid in entity_map else None,
            domain=entity_map[eid].domain if eid in entity_map else None,
            is_center=(eid == entity_id),
        )
        for eid in visited_ids
    ]

    edges = [
        schemas.GraphEdge(
            id=e.id,
            source=e.source_id,
            target=e.target_id,
            relation_type=e.relation_type,
            weight=e.weight,
        )
        for e in final_edges
    ]

    return schemas.EntityGraphResponse(
        center_id=entity_id,
        depth=depth,
        nodes=nodes,
        edges=edges,
    )


@router.get("/entities/{entity_id}/relationships", response_model=List[schemas.EntityRelationshipResponse])
def list_relationships(
    entity_id: int = Path(..., ge=1),
    db: Session = Depends(get_db),
    _: models.User = Depends(get_current_user),
):
    """List all relationships where this entity is source or target."""
    _get_entity_or_404(entity_id, db)
    return (
        db.query(models.EntityRelationship)
        .filter(
            (models.EntityRelationship.source_id == entity_id)
            | (models.EntityRelationship.target_id == entity_id)
        )
        .order_by(models.EntityRelationship.created_at.desc())
        .all()
    )


@router.post("/entities/{entity_id}/relationships", response_model=schemas.EntityRelationshipResponse, status_code=201)
def create_relationship(
    payload: schemas.EntityRelationshipCreate,
    entity_id: int = Path(..., ge=1),
    db: Session = Depends(get_db),
    _: models.User = Depends(require_role("super_admin", "admin", "editor")),
):
    """Create a directed relationship from entity_id → target_id."""
    _get_entity_or_404(entity_id, db)
    _get_entity_or_404(payload.target_id, db)

    if entity_id == payload.target_id:
        raise HTTPException(status_code=400, detail="Self-referential relationships are not allowed.")

    # Prevent duplicate directed edge of same type
    existing = (
        db.query(models.EntityRelationship)
        .filter(
            models.EntityRelationship.source_id == entity_id,
            models.EntityRelationship.target_id == payload.target_id,
            models.EntityRelationship.relation_type == payload.relation_type,
        )
        .first()
    )
    if existing:
        raise HTTPException(status_code=409, detail="This relationship already exists.")

    rel = models.EntityRelationship(
        source_id=entity_id,
        target_id=payload.target_id,
        relation_type=payload.relation_type,
        weight=payload.weight,
        notes=payload.notes,
    )
    db.add(rel)
    db.commit()
    db.refresh(rel)
    return rel


@router.delete("/relationships/{rel_id}", status_code=204)
def delete_relationship(
    rel_id: int = Path(..., ge=1),
    db: Session = Depends(get_db),
    _: models.User = Depends(require_role("super_admin", "admin", "editor")),
):
    """Delete a relationship by ID."""
    rel = db.get(models.EntityRelationship, rel_id)
    if not rel:
        raise HTTPException(status_code=404, detail="Relationship not found")
    db.delete(rel)
    db.commit()
