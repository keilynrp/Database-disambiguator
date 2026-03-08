"""
Column mapping dictionaries for import/export operations.
Extracted from main.py so that both ingest.py and harmonization.py
share the same mutable dict object.
"""

COLUMN_MAPPING = {
    "Nombre del Producto": "entity_name",
    "Clasificación": "classification",
    "Tipo de Producto": "entity_type",
    "¿Posible vender en cantidad decimal?": "is_decimal_sellable",
    "¿Controlarás el stock del producto?": "control_stock",
    "Estado": "status",
    "Impuestos": "taxes",
    "Variante": "variant",
    "Código universal de producto": "entity_code_universal_1",
    "Codigo universal": "entity_code_universal_2",
    "Codigo universal del producto": "entity_code_universal_3",
    "CODIGO UNIVERSAL DEL PRODRUCTO ": "entity_code_universal_4",
    "marca": "brand_lower",
    "Marca": "brand_capitalized",
    "modelo": "model",
    "GTIN": "gtin",
    "Motivo de GTIN": "gtin_reason",
    "Motivo de GTIN vacío": "gtin_empty_reason_1",
    "Motivo GTIN vacío ": "gtin_empty_reason_2",
    "Motivo GTIN vacia": "gtin_empty_reason_3",
    "Motivo GTIN de producto": "gtin_entity_reason",
    "motivo GTIN": "gtin_reason_lower",
    "Mtivo GTIN vacio": "gtin_empty_reason_typo",
    "EQUIMAPIENTO": "equipment",
    "MEDIDA": "measure",
    "TIPO DE UNION": "union_type",
    "¿permitirás ventas sin stock?": "allow_sales_without_stock",
    "Código de Barras": "barcode",
    "SKU": "sku",
    "Sucursales": "branches",
    "Fecha de creacion": "creation_date",
    "Estado Variante": "variant_status",
    "Clave de producto": "entity_key",
    "Unidad de medida": "unit_of_measure",
}

# Reverse mapping: model_field -> original excel header
EXPORT_COLUMN_MAPPING: dict[str, str] = {v: k.strip() for k, v in COLUMN_MAPPING.items()}

# Fix typos in export column headers
EXPORT_COLUMN_MAPPING.update({
    "equipment": "EQUIPAMIENTO",
    "gtin_empty_reason_typo": "Motivo GTIN vacio",
    "entity_code_universal_4": "CODIGO UNIVERSAL DEL PRODUCTO",
})

# Corrections applied by the fix_export_typos harmonization step
EXPORT_COLUMN_CORRECTIONS = {
    "equipment": "EQUIPAMIENTO",
    "gtin_empty_reason_typo": "Motivo GTIN vacio",
    "entity_code_universal_4": "CODIGO UNIVERSAL DEL PRODUCTO",
}
