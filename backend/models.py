from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text
from .database import Base

class RawProduct(Base):
    __tablename__ = "raw_products"

    id = Column(Integer, primary_key=True, index=True)
    
    # Original Columns normalized to snake_case
    product_name = Column(String, index=True) # Nombre del Producto
    classification = Column(String) # Clasificación
    product_type = Column(String) # Tipo de Producto
    is_decimal_sellable = Column(String) # ¿Posible vender en cantidad decimal?
    control_stock = Column(String) # ¿Controlarás el stock del producto?
    status = Column(String) # Estado
    taxes = Column(String) # Impuestos
    variant = Column(String) # Variante
    
    # Messy ID definitions
    product_code_universal_1 = Column(String) # Código universal de producto
    product_code_universal_2 = Column(String) # Codigo universal
    product_code_universal_3 = Column(String) # Codigo universal del producto
    product_code_universal_4 = Column(String) # CODIGO UNIVERSAL DEL PRODRUCTO 
    
    brand_lower = Column(String) # marca
    brand_capitalized = Column(String) # Marca
    
    model = Column(String) # modelo
    
    # GTIN mess
    gtin = Column(String) # GTIN
    gtin_reason = Column(String) # Motivo de GTIN
    gtin_empty_reason_1 = Column(String) # Motivo de GTIN vacío
    gtin_empty_reason_2 = Column(String) # Motivo GTIN vacío 
    gtin_empty_reason_3 = Column(String) # Motivo GTIN vacia
    gtin_product_reason = Column(String) # Motivo GTIN de producto
    gtin_reason_lower = Column(String) # motivo GTIN
    gtin_empty_reason_typo = Column(String) # Mtivo GTIN vacio
    
    equipment = Column(String) # EQUIMAPIENTO
    measure = Column(String) # MEDIDA
    union_type = Column(String) # TIPO DE UNION
    
    allow_sales_without_stock = Column(String) # ¿permitirás ventas sin stock?
    barcode = Column(String) # Código de Barras
    sku = Column(String) # SKU
    branches = Column(String) # Sucursales
    
    creation_date = Column(String) # Fecha de creacion
    variant_status = Column(String) # Estado Variante
    product_key = Column(String) # Clave de producto
    unit_of_measure = Column(String) # Unidad de medida
    
    # Metadata
    validation_status = Column(String, default="pending") # pending, valid, invalid
    normalized_json = Column(Text, nullable=True) # Store clean version here

    # Scientometric Enrichment Fields
    enrichment_doi = Column(String, nullable=True)
    enrichment_citation_count = Column(Integer, default=0)
    enrichment_concepts = Column(Text, nullable=True) # Stored as comma-separated
    enrichment_source = Column(String, nullable=True)
    enrichment_status = Column(String, default="none") # none, pending, completed, failed

class NormalizationRule(Base):
    __tablename__ = "normalization_rules"
    
    id = Column(Integer, primary_key=True, index=True)
    field_name = Column(String, index=True) # e.g., "brand_lower"
    original_value = Column(String, index=True) # e.g., "mikrosoft"
    normalized_value = Column(String) # e.g., "Microsoft"
    is_regex = Column(Boolean, default=False)


class HarmonizationLog(Base):
    __tablename__ = "harmonization_logs"

    id = Column(Integer, primary_key=True, index=True)
    step_id = Column(String, index=True)
    step_name = Column(String)
    records_updated = Column(Integer)
    fields_modified = Column(Text)
    executed_at = Column(DateTime)
    details = Column(Text, nullable=True)
    reverted = Column(Boolean, default=False)


class HarmonizationChangeRecord(Base):
    __tablename__ = "harmonization_change_records"

    id = Column(Integer, primary_key=True, index=True)
    log_id = Column(Integer, index=True)
    record_id = Column(Integer, index=True)
    field = Column(String)
    old_value = Column(Text, nullable=True)
    new_value = Column(Text, nullable=True)


class StoreConnection(Base):
    __tablename__ = "store_connections"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)                    # Human-friendly label, e.g. "Mi Tienda WooCommerce"
    platform = Column(String, index=True)                # woocommerce | shopify | bsale | custom
    base_url = Column(String)                            # e.g. https://mitienda.com
    api_key = Column(String, nullable=True)               # Consumer key / API key
    api_secret = Column(String, nullable=True)            # Consumer secret / API secret
    access_token = Column(String, nullable=True)          # For OAuth-based platforms (Shopify)
    custom_headers = Column(Text, nullable=True)          # JSON string for custom API headers
    is_active = Column(Boolean, default=True)
    last_sync_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime)
    product_count = Column(Integer, default=0)            # Cached count of mapped products
    sync_direction = Column(String, default="bidirectional")  # pull | push | bidirectional
    notes = Column(Text, nullable=True)


class StoreSyncMapping(Base):
    __tablename__ = "store_sync_mappings"

    id = Column(Integer, primary_key=True, index=True)
    store_id = Column(Integer, index=True)               # FK to store_connections.id
    local_product_id = Column(Integer, index=True)       # FK to raw_products.id
    remote_product_id = Column(String, nullable=True)    # ID in the remote store
    canonical_url = Column(String, index=True)            # The canonical URL used for mapping
    remote_sku = Column(String, nullable=True)
    remote_name = Column(String, nullable=True)
    remote_price = Column(String, nullable=True)
    remote_stock = Column(String, nullable=True)
    remote_status = Column(String, nullable=True)
    remote_data_json = Column(Text, nullable=True)       # Full remote product data snapshot
    sync_status = Column(String, default="pending")      # pending | synced | conflict | error
    last_synced_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime)


class SyncLog(Base):
    __tablename__ = "sync_logs"

    id = Column(Integer, primary_key=True, index=True)
    store_id = Column(Integer, index=True)               # FK to store_connections.id
    action = Column(String)                              # pull | push | map | unmap
    status = Column(String)                              # success | error | partial
    records_affected = Column(Integer, default=0)
    details = Column(Text, nullable=True)                # JSON with details
    executed_at = Column(DateTime)


class SyncQueueItem(Base):
    __tablename__ = "sync_queue"

    id = Column(Integer, primary_key=True, index=True)
    store_id = Column(Integer, index=True)               # FK to store_connections.id
    mapping_id = Column(Integer, nullable=True, index=True)  # FK to store_sync_mappings.id
    direction = Column(String)                            # pull | push
    product_name = Column(String, nullable=True)          # For display convenience
    canonical_url = Column(String, nullable=True)
    field = Column(String)                                # Which field changed
    local_value = Column(Text, nullable=True)
    remote_value = Column(Text, nullable=True)
    status = Column(String, default="pending", index=True) # pending | approved | rejected | applied
    created_at = Column(DateTime)
    resolved_at = Column(DateTime, nullable=True)

