"""
Sprint 70 — Entity Relationship Graph
  GET  /entities/{id}/graph            — graph: nodes + edges up to depth N
  GET  /entities/{id}/relationships    — list direct relationships
  POST /entities/{id}/relationships    — create a new relationship
  DELETE /relationships/{rel_id}       — delete a relationship
"""
import logging
from collections import deque
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from sqlalchemy.orm import Session

from backend import models, schemas
from backend.auth import get_current_user, require_role
from backend.database import get_db

logger = logging.getLogger(__name__)

router = APIRouter(tags=["relationships"])


def _get_entity_or_404(entity_id: int, db: Session) -> models.RawEntity:
    entity = db.get(models.RawEntity, entity_id)
    if not entity:
        raise HTTPException(status_code=404, detail=f"Entity {entity_id} not found")
    return entity


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
