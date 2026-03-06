"""
OpenAlex entity resolver.
Searches authors, institutions, and concepts depending on entity_type.
Reuses OPENALEX_EMAIL env var for the polite pool (same as enrichment_worker).
HTTP client: httpx — same library used in OpenAlexAdapter.
"""
import logging
import os
from typing import List

import httpx

from backend.authority.base import AuthorityCandidate, BaseAuthorityResolver

logger = logging.getLogger(__name__)

_BASE = "https://api.openalex.org"
_POLITE_EMAIL = os.environ.get("OPENALEX_EMAIL", "")


def _params(query: str) -> dict:
    p: dict = {"search": query, "per-page": 5}
    if _POLITE_EMAIL:
        p["mailto"] = _POLITE_EMAIL
    return p


class OpenAlexEntityResolver(BaseAuthorityResolver):
    source_name = "openalex"

    def resolve(self, value: str, entity_type: str) -> List[AuthorityCandidate]:
        endpoints = self._select_endpoints(entity_type)
        candidates: List[AuthorityCandidate] = []
        try:
            with httpx.Client(timeout=self.timeout) as client:
                for endpoint, kind in endpoints:
                    resp = client.get(endpoint, params=_params(value))
                    if resp.status_code != 200:
                        continue
                    results = resp.json().get("results", [])
                    for item in results[:3]:
                        oa_id = item.get("id", "")  # full URL like https://openalex.org/A123
                        display_name = item.get("display_name", "")
                        if not oa_id or not display_name:
                            continue
                        short_id = oa_id.split("/")[-1]  # e.g. A123456789
                        # Collect aliases from alternate_names or x_concepts
                        aliases = item.get("alternate_names", [])
                        description = self._build_description(item, kind)
                        candidates.append(AuthorityCandidate(
                            authority_source=self.source_name,
                            authority_id=short_id,
                            canonical_label=display_name,
                            aliases=aliases[:5],
                            description=description,
                            uri=oa_id,
                        ))
        except Exception as exc:
            logger.warning("OpenAlexEntityResolver failed for '%s': %s", value, exc)
        return candidates

    @staticmethod
    def _select_endpoints(entity_type: str) -> List[tuple]:
        """Return (url, kind) pairs to query based on entity type."""
        if entity_type == "person":
            return [(_BASE + "/authors", "author")]
        if entity_type == "institution":
            return [(_BASE + "/institutions", "institution")]
        if entity_type == "concept":
            return [(_BASE + "/concepts", "concept")]
        if entity_type == "organization":
            return [(_BASE + "/institutions", "institution")]
        # general: try authors + institutions + concepts
        return [
            (_BASE + "/authors", "author"),
            (_BASE + "/institutions", "institution"),
            (_BASE + "/concepts", "concept"),
        ]

    @staticmethod
    def _build_description(item: dict, kind: str) -> str | None:
        if kind == "author":
            inst = (item.get("last_known_institution") or {}).get("display_name", "")
            works = item.get("works_count", 0)
            return f"Researcher — {inst} ({works} works)" if inst else f"Researcher ({works} works)"
        if kind == "institution":
            country = item.get("country_code", "")
            itype = item.get("type", "")
            return f"{itype.title()} — {country}" if itype else None
        if kind == "concept":
            level = item.get("level")
            return f"Concept (level {level})" if level is not None else None
        return None
