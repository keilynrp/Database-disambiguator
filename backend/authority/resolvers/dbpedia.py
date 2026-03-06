"""
DBpedia Lookup API resolver.
Uses the DBpedia Lookup REST endpoint — no authentication required.
Good coverage for persons, organizations, and general concepts via Wikipedia.
"""
import logging
from typing import List

import httpx

from backend.authority.base import AuthorityCandidate, BaseAuthorityResolver

logger = logging.getLogger(__name__)

_DBPEDIA_LOOKUP = "https://lookup.dbpedia.org/api/search"
_DESC_MAX_LEN = 200


class DbpediaResolver(BaseAuthorityResolver):
    source_name = "dbpedia"

    def resolve(self, value: str, entity_type: str) -> List[AuthorityCandidate]:
        try:
            with httpx.Client(timeout=self.timeout) as client:
                resp = client.get(_DBPEDIA_LOOKUP, params={
                    "query": value,
                    "maxResults": 5,
                    "format": "json",
                })
                resp.raise_for_status()
                data = resp.json()

            candidates = []
            for doc in data.get("docs", []):
                uri = doc.get("resource", [None])[0] if doc.get("resource") else None
                label_list = doc.get("label", [])
                label = label_list[0] if label_list else ""
                if not uri or not label:
                    continue
                comment_list = doc.get("comment", [])
                raw_desc = comment_list[0] if comment_list else None
                description = raw_desc[:_DESC_MAX_LEN] if raw_desc else None
                # Extract aliases from redirects field
                redirects = doc.get("redirectlabel", [])
                candidates.append(AuthorityCandidate(
                    authority_source=self.source_name,
                    authority_id=uri,
                    canonical_label=label,
                    aliases=redirects[:10],
                    description=description,
                    uri=uri,
                ))
            return candidates
        except Exception as exc:
            logger.warning("DbpediaResolver failed for '%s': %s", value, exc)
            return []
