from abc import ABC, abstractmethod
from typing import List, Optional

from backend.schemas_enrichment import EnrichedRecord

class BaseScientometricAdapter(ABC):
    """
    Abstract interface for all scientometric APIs (OpenAlex, WoS, Scopus).
    Follows the Adapter pattern defined in our Architecture docs to shield
    the core app from external API changes and varied authentication schemas.
    """
    
    @abstractmethod
    def search_by_doi(self, doi: str) -> Optional[EnrichedRecord]:
        """
        Retrieves a single publication unified record based on its DOI.
        """
        pass
    
    @abstractmethod
    def search_by_title(self, title: str, limit: int = 5) -> List[EnrichedRecord]:
        """
        Performs a fuzzy search on the title field.
        """
        pass
    
    @abstractmethod
    def search_by_author(self, name: str, limit: int = 10) -> List[EnrichedRecord]:
        """
        Finds matching works depending on the author's normalized name.
        """
        pass
