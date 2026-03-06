"""
Authority Resolution Orchestrator.

Steps:
  1. Call all 5 resolvers in parallel (ThreadPoolExecutor).
  2. Apply weighted scoring engine (identifiers + name + affiliation signals).
  3. Deduplicate candidates across sources that refer to the same entity.
  4. Return top-20 candidates ranked by confidence descending.
"""
from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Optional

from thefuzz import fuzz

from backend.authority.base import AuthorityCandidate, ResolveContext
from backend.authority.normalize import normalize_name
from backend.authority.scoring import compute_score
from backend.authority.resolvers.wikidata import WikidataResolver
from backend.authority.resolvers.viaf     import ViafResolver
from backend.authority.resolvers.orcid    import OrcidResolver
from backend.authority.resolvers.dbpedia  import DbpediaResolver
from backend.authority.resolvers.openalex import OpenAlexEntityResolver

logger = logging.getLogger(__name__)

_RESOLVERS = [
    WikidataResolver(),
    ViafResolver(),
    OrcidResolver(),
    DbpediaResolver(),
    OpenAlexEntityResolver(),
]

_MAX_RESULTS      = 20
_PARALLEL_TIMEOUT = 12   # seconds to wait for all futures
_DEDUP_THRESHOLD  = 92   # token_sort_ratio threshold for same-entity merging

# Source priority for picking the "winner" when merging duplicates
_SOURCE_PRIORITY = {"orcid": 5, "openalex": 4, "viaf": 3, "wikidata": 2, "dbpedia": 1}


def _deduplicate(candidates: List[AuthorityCandidate]) -> List[AuthorityCandidate]:
    """
    Merge candidates from different sources that refer to the same entity.

    Two candidates are considered duplicates when the token_sort_ratio of their
    normalised canonical labels is >= _DEDUP_THRESHOLD.  The candidate from the
    higher-quality source wins; merged sources are recorded in merged_sources.
    """
    if len(candidates) <= 1:
        return candidates

    used = [False] * len(candidates)
    merged: List[AuthorityCandidate] = []

    for i, c in enumerate(candidates):
        if used[i]:
            continue
        group = [c]
        used[i] = True
        for j in range(i + 1, len(candidates)):
            if used[j]:
                continue
            sim = fuzz.token_sort_ratio(
                normalize_name(c.canonical_label),
                normalize_name(candidates[j].canonical_label),
            )
            if sim >= _DEDUP_THRESHOLD:
                group.append(candidates[j])
                used[j] = True

        if len(group) == 1:
            merged.append(c)
            continue

        # Pick the highest-quality source as the representative
        best = max(group, key=lambda x: _SOURCE_PRIORITY.get(x.authority_source, 0))
        other_refs = [
            f"{x.authority_source}:{x.authority_id}"
            for x in group
            if x is not best
        ]
        best.merged_sources = other_refs
        merged.append(best)

    return merged


def resolve_all(
    value: str,
    entity_type: str,
    context: Optional[ResolveContext] = None,
) -> List[AuthorityCandidate]:
    """
    Query all authority sources in parallel for the given value.

    Applies the weighted scoring engine (identifiers + name + affiliation)
    and deduplicates candidates that refer to the same entity across sources.
    Returns at most _MAX_RESULTS candidates sorted by confidence descending.
    """
    if context is None:
        context = ResolveContext()

    raw: List[AuthorityCandidate] = []

    with ThreadPoolExecutor(max_workers=5) as pool:
        futures = {
            pool.submit(resolver.resolve, value, entity_type): resolver.source_name
            for resolver in _RESOLVERS
        }
        for future in as_completed(futures, timeout=_PARALLEL_TIMEOUT):
            source = futures[future]
            try:
                raw.extend(future.result())
            except Exception as exc:
                logger.warning("Authority resolver '%s' timed out or failed: %s", source, exc)

    # Apply weighted scoring engine
    for c in raw:
        score, breakdown, evidence, resolution_status = compute_score(
            value=value,
            authority_source=c.authority_source,
            authority_id=c.authority_id,
            canonical_label=c.canonical_label,
            description=c.description,
            orcid_hint=context.orcid_hint,
            affiliation=context.affiliation,
        )
        c.confidence        = score
        c.score_breakdown   = breakdown
        c.evidence          = evidence
        c.resolution_status = resolution_status

    # Deduplicate cross-source
    deduped = _deduplicate(raw)

    deduped.sort(key=lambda c: c.confidence, reverse=True)
    return deduped[:_MAX_RESULTS]
