import os
import yaml
from typing import List, Dict, Optional
from pydantic import BaseModel

DOMAINS_DIR = os.path.join(os.path.dirname(__file__), "domains")

class AttributeSchema(BaseModel):
    name: str             # db field name or arbitrary json key
    type: str             # string, integer, float, boolean, array
    label: str            # human-readable label
    required: bool = False
    is_core: bool = False # whether it matches standard RawEntity columns or goes into normalized_json

class DomainSchema(BaseModel):
    id: str
    name: str
    description: str
    primary_entity: str
    icon: Optional[str] = "Database"
    attributes: List[AttributeSchema]

class SchemaRegistry:
    def __init__(self):
        self.domains: Dict[str, DomainSchema] = {}
        self._load_registry()

    def _load_registry(self):
        self.domains.clear()
        if not os.path.exists(DOMAINS_DIR):
            os.makedirs(DOMAINS_DIR, exist_ok=True)
            
        for filename in os.listdir(DOMAINS_DIR):
            if filename.endswith(".yaml") or filename.endswith(".yml"):
                filepath = os.path.join(DOMAINS_DIR, filename)
                try:
                    with open(filepath, "r", encoding="utf-8") as f:
                        data = yaml.safe_load(f)
                        if data:
                            schema = DomainSchema(**data)
                            self.domains[schema.id] = schema
                except Exception as e:
                    print(f"Error loading domain schema {filename}: {e}")

    def get_all_domains(self) -> List[DomainSchema]:
        # Return default first if available
        domains_list = list(self.domains.values())
        return sorted(domains_list, key=lambda d: 0 if d.id == "default" else 1)

    def get_domain(self, domain_id: str) -> Optional[DomainSchema]:
        return self.domains.get(domain_id)

registry = SchemaRegistry()
