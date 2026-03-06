"""
VIAF (Virtual International Authority File) resolver.
Uses the VIAF AutoSuggest API — no authentication required.
Best coverage for personal names and corporate bodies.
"""
import logging
from typing import List

import httpx

from backend.authority.base import AuthorityCandidate, BaseAuthorityResolver

logger = logging.getLogger(__name__)

_VIAF_SUGGEST = "https://www.viaf.org/viaf/AutoSuggest"

# Map our entity_type to VIAF nametype values
_NAMETYPE_FILTER = {
    "person":       {"Personal"},
    "organization": {"Corporate"},
    "institution":  {"Corporate"},
    "concept":      set(),  # VIAF doesn't cover concepts well — return all
    "general":      set(),  # no filter
}


class ViafResolver(BaseAuthorityResolver):
    source_name = "viaf"

    def resolve(self, value: str, entity_type: str) -> List[AuthorityCandidate]:
        try:
            with httpx.Client(timeout=self.timeout) as client:
                resp = client.get(_VIAF_SUGGEST, params={"query": value})
                resp.raise_for_status()
                data = resp.json()

            allowed_types = _NAMETYPE_FILTER.get(entity_type, set())
            candidates = []
            for item in data.get("result", []):
                viafid = str(item.get("viafid", ""))
                term = item.get("term", "")
                nametype = item.get("nametype", "")
                if not viafid or not term:
                    continue
                if allowed_types and nametype not in allowed_types:
                    continue
                candidates.append(AuthorityCandidate(
                    authority_source=self.source_name,
                    authority_id=f"viaf/{viafid}",
                    canonical_label=term,
                    description=f"VIAF nametype: {nametype}" if nametype else None,
                    uri=f"https://viaf.org/viaf/{viafid}",
                ))
            return candidates[:5]
        except Exception as exc:
            logger.warning("ViafResolver failed for '%s': %s", value, exc)
            return []
