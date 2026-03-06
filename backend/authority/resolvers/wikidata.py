"""
Wikidata authority resolver.
Uses the Wikidata Search API (wbsearchentities action).
No authentication required. Polite User-Agent header sent.
"""
import logging
from typing import List

import httpx

from backend.authority.base import AuthorityCandidate, BaseAuthorityResolver

logger = logging.getLogger(__name__)

_WIKIDATA_SEARCH = "https://www.wikidata.org/w/api.php"
_HEADERS = {"User-Agent": "UKIP/1.0 (universal-knowledge-intelligence-platform)"}


class WikidataResolver(BaseAuthorityResolver):
    source_name = "wikidata"

    def resolve(self, value: str, entity_type: str) -> List[AuthorityCandidate]:
        try:
            with httpx.Client(timeout=self.timeout, headers=_HEADERS) as client:
                resp = client.get(_WIKIDATA_SEARCH, params={
                    "action": "wbsearchentities",
                    "search": value,
                    "language": "en",
                    "format": "json",
                    "limit": 5,
                })
                resp.raise_for_status()
                data = resp.json()

            candidates = []
            for item in data.get("search", []):
                qid = item.get("id", "")
                label = item.get("label", "")
                if not qid or not label:
                    continue
                aliases = [a for a in item.get("aliases", [])]
                candidates.append(AuthorityCandidate(
                    authority_source=self.source_name,
                    authority_id=qid,
                    canonical_label=label,
                    aliases=aliases,
                    description=item.get("description"),
                    uri=f"https://www.wikidata.org/wiki/{qid}",
                ))
            return candidates
        except Exception as exc:
            logger.warning("WikidataResolver failed for '%s': %s", value, exc)
            return []
