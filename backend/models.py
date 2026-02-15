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

class NormalizationRule(Base):
    __tablename__ = "normalization_rules"
    
    id = Column(Integer, primary_key=True, index=True)
    field_name = Column(String, index=True) # e.g., "brand_lower"
    original_value = Column(String, index=True) # e.g., "mikrosoft"
    normalized_value = Column(String) # e.g., "Microsoft"
    is_regex = Column(Boolean, default=False)
