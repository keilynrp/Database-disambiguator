from enum import Enum

from pydantic import BaseModel, ConfigDict, Field
from typing import Literal, Optional, List

class EntityBase(BaseModel):
    entity_name: Optional[str] = None
    classification: Optional[str] = None
    entity_type: Optional[str] = None
    is_decimal_sellable: Optional[str] = None
    control_stock: Optional[str] = None
    status: Optional[str] = None
    taxes: Optional[str] = None
    variant: Optional[str] = None
    entity_code_universal_1: Optional[str] = None
    entity_code_universal_2: Optional[str] = None
    entity_code_universal_3: Optional[str] = None
    entity_code_universal_4: Optional[str] = None
    brand_lower: Optional[str] = None
    brand_capitalized: Optional[str] = None
    model: Optional[str] = None
    gtin: Optional[str] = None
    gtin_reason: Optional[str] = None
    gtin_empty_reason_1: Optional[str] = None
    gtin_empty_reason_2: Optional[str] = None
    gtin_empty_reason_3: Optional[str] = None
    gtin_entity_reason: Optional[str] = None
    gtin_reason_lower: Optional[str] = None
    gtin_empty_reason_typo: Optional[str] = None
    equipment: Optional[str] = None
    measure: Optional[str] = None
    union_type: Optional[str] = None
    allow_sales_without_stock: Optional[str] = None
    barcode: Optional[str] = None
    sku: Optional[str] = None
    branches: Optional[str] = None
    creation_date: Optional[str] = None
    variant_status: Optional[str] = None
    entity_key: Optional[str] = None
    unit_of_measure: Optional[str] = None
    validation_status: Optional[str] = None
    
    # Enrichment fields
    enrichment_doi: Optional[str] = None
    enrichment_citation_count: int = 0
    enrichment_concepts: Optional[str] = None
    enrichment_source: Optional[str] = None
    enrichment_status: str = "none"

class Entity(EntityBase):
    id: int
    normalized_json: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

class RuleBase(BaseModel):
    field_name: str
    original_value: str
    normalized_value: str
    is_regex: bool = False

class Rule(RuleBase):
    id: int

    model_config = ConfigDict(from_attributes=True)

class BulkRuleCreate(BaseModel):
    field_name: str
    canonical_value: str
    variations: List[str]


class HarmonizationChange(BaseModel):
    record_id: int
    field: str
    old_value: Optional[str] = None
    new_value: Optional[str] = None


class HarmonizationLogResponse(BaseModel):
    id: int
    step_id: str
    step_name: str
    records_updated: int
    fields_modified: List[str]
    executed_at: Optional[str] = None
    reverted: bool = False

    model_config = ConfigDict(from_attributes=True)


class UndoRedoResponse(BaseModel):
    log_id: int
    action: str
    records_restored: int
    step_id: str
    step_name: str


# ── Store Integration Schemas ─────────────────────────────────────────

_Platform = Literal["woocommerce", "shopify", "bsale", "custom"]
_SyncDirection = Literal["pull", "push", "bidirectional"]


class StoreConnectionCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    platform: _Platform
    base_url: str = Field(min_length=1, max_length=500)
    api_key: Optional[str] = None
    api_secret: Optional[str] = None
    access_token: Optional[str] = None
    custom_headers: Optional[str] = Field(default=None, max_length=5000)
    sync_direction: _SyncDirection = "bidirectional"
    notes: Optional[str] = None


class StoreConnectionUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    platform: Optional[_Platform] = None
    base_url: Optional[str] = Field(default=None, min_length=1, max_length=500)
    api_key: Optional[str] = None
    api_secret: Optional[str] = None
    access_token: Optional[str] = None
    custom_headers: Optional[str] = Field(default=None, max_length=5000)
    is_active: Optional[bool] = None
    sync_direction: Optional[_SyncDirection] = None
    notes: Optional[str] = None


class StoreConnectionResponse(BaseModel):
    id: int
    name: str
    platform: str
    base_url: str
    is_active: bool
    last_sync_at: Optional[str] = None
    created_at: Optional[str] = None
    entity_count: int = 0
    sync_direction: str = "bidirectional"
    notes: Optional[str] = None
    # Credentials are intentionally excluded from responses

    model_config = ConfigDict(from_attributes=True)


# ── RBAC: Users ───────────────────────────────────────────────────────────

class UserRole(str, Enum):
    super_admin = "super_admin"
    admin       = "admin"
    editor      = "editor"
    viewer      = "viewer"


class UserCreate(BaseModel):
    username: str           = Field(min_length=3, max_length=50)
    email:    Optional[str] = Field(default=None, max_length=255)
    password: str           = Field(min_length=8, max_length=128)
    role:     UserRole      = UserRole.viewer


class UserUpdate(BaseModel):
    email:     Optional[str]      = Field(default=None, max_length=255)
    password:  Optional[str]      = Field(default=None, min_length=8, max_length=128)
    role:      Optional[UserRole] = None
    is_active: Optional[bool]     = None


class UserResponse(BaseModel):
    id:         int
    username:   str
    email:      Optional[str] = None
    role:       str
    is_active:  bool
    created_at: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class PasswordChange(BaseModel):
    current_password: str = Field(min_length=1, max_length=128)
    new_password:     str = Field(min_length=8, max_length=128)
