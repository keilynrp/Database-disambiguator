"""
ORCID public API resolver.
Searches researchers by name. Only meaningful for entity_type in (person, general).
No authentication required for the public search API.
"""
import logging
from typing import List

import httpx

from backend.authority.base import AuthorityCandidate, BaseAuthorityResolver

logger = logging.getLogger(__name__)

_ORCID_SEARCH = "https://pub.orcid.org/v3.0/search/"
_PERSON_TYPES = {"person", "general"}


class OrcidResolver(BaseAuthorityResolver):
    source_name = "orcid"

    def resolve(self, value: str, entity_type: str) -> List[AuthorityCandidate]:
        if entity_type not in _PERSON_TYPES:
            return []
        try:
            with httpx.Client(timeout=self.timeout) as client:
                resp = client.get(
                    _ORCID_SEARCH,
                    params={"q": value, "rows": 5},
                    headers={"Accept": "application/json"},
                )
                resp.raise_for_status()
                data = resp.json()

            candidates = []
            for result in data.get("result", []):
                orcid_id = (
                    result.get("orcid-identifier", {}).get("path", "")
                )
                if not orcid_id:
                    continue
                # Build display name from personal details if available
                person = result.get("person", {})
                name_obj = person.get("name", {}) if person else {}
                given = (name_obj.get("given-names") or {}).get("value", "") if name_obj else ""
                family = (name_obj.get("family-name") or {}).get("value", "") if name_obj else ""
                label = f"{given} {family}".strip() or orcid_id
                candidates.append(AuthorityCandidate(
                    authority_source=self.source_name,
                    authority_id=orcid_id,
                    canonical_label=label,
                    description="Researcher identifier (ORCID)",
                    uri=f"https://orcid.org/{orcid_id}",
                ))
            return candidates
        except Exception as exc:
            logger.warning("OrcidResolver failed for '%s': %s", value, exc)
            return []
