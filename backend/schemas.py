from pydantic import BaseModel
from typing import Optional, List

class ProductBase(BaseModel):
    product_name: Optional[str] = None
    classification: Optional[str] = None
    product_type: Optional[str] = None
    is_decimal_sellable: Optional[str] = None
    control_stock: Optional[str] = None
    status: Optional[str] = None
    taxes: Optional[str] = None
    variant: Optional[str] = None
    product_code_universal_1: Optional[str] = None
    product_code_universal_2: Optional[str] = None
    product_code_universal_3: Optional[str] = None
    product_code_universal_4: Optional[str] = None
    brand_lower: Optional[str] = None
    brand_capitalized: Optional[str] = None
    model: Optional[str] = None
    gtin: Optional[str] = None
    gtin_reason: Optional[str] = None
    gtin_empty_reason_1: Optional[str] = None
    gtin_empty_reason_2: Optional[str] = None
    gtin_empty_reason_3: Optional[str] = None
    gtin_product_reason: Optional[str] = None
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
    product_key: Optional[str] = None
    unit_of_measure: Optional[str] = None

class Product(ProductBase):
    id: int
    validation_status: str
    normalized_json: Optional[str] = None

    class Config:
        from_attributes = True

class RuleBase(BaseModel):
    field_name: str
    original_value: str
    normalized_value: str
    is_regex: bool = False

class Rule(RuleBase):
    id: int

    class Config:
        from_attributes = True

class BulkRuleCreate(BaseModel):
    field_name: str
    canonical_value: str
    variations: List[str]
