import os
import re

DIRS = [
    r"d:\universal-knowledge-intelligence-platform\backend",
    r"d:\universal-knowledge-intelligence-platform\frontend\app",
    r"d:\universal-knowledge-intelligence-platform\scripts",
]

# Ordered by longest first or specificity
replacements = {
    "RawProduct": "RawEntity",
    "raw_products": "raw_entities",
    "ProductBase": "EntityBase",
    "ProductCreate": "EntityCreate",
    "ProductSchema": "EntitySchema",
    "RemoteProduct": "RemoteEntity",
    "ProductGroup": "EntityGroup",
    "ProductTable": "EntityTable",
    "ProductVariantView": "EntityVariantView",
    "local_product_id": "local_entity_id",
    "remote_product_id": "remote_entity_id",
    "product_name": "entity_name",
    "product_type": "entity_type",
    "product_key": "entity_key",
    "product_count": "entity_count",
    "gtin_product_reason": "gtin_entity_reason",
    "product_code_universal_1": "entity_code_universal_1",
    "product_code_universal_2": "entity_code_universal_2",
    "product_code_universal_3": "entity_code_universal_3",
    "product_code_universal_4": "entity_code_universal_4",
    "get_products": "get_entities",
    "delete_product": "delete_entity",
    "enrichProduct": "enrichEntity",
    "enrich_product": "enrich_entity",
    "fetchProducts": "fetchEntities",
    "setSelectedProduct": "setSelectedEntity",
    "selectedProduct": "selectedEntity",
    "deleteProduct": "deleteEntity",
    
    "schemas.Product": "schemas.Entity",
    "models.RawProduct": "models.RawEntity",
    "Product):": "Entity):",
    "def get_products": "def get_entities",
    "def get_product(": "def get_entity(",
    
    "\"/products\"": "\"/entities\"",
    "\"/products/grouped\"": "\"/entities/grouped\"",
    "\"/products/{": "\"/entities/{",
    "\"/products/?": "\"/entities/?",
    
    "localhost:8000/products": "localhost:8000/entities",
    
    "interface Product ": "interface Entity ",
    "Product[]": "Entity[]",
    "product: Product": "entity: Entity",
    "product.id": "entity.id",
    "product.product_name": "entity.entity_name",
    "product.brand_capitalized": "entity.brand_capitalized",
    "product.model": "entity.model",
    "product.sku": "entity.sku",
    "product.classification": "entity.classification",
    "product.product_type": "entity.entity_type",
    "product.variant": "entity.variant",
    "product.gtin": "entity.gtin",
    "product.barcode": "entity.barcode",
    "product.status": "entity.status",
    "product.validation_status": "entity.validation_status",
    
    "setProducts(": "setEntities(",
    "products.length": "entities.length",
    "products.map": "entities.map",
    "products, setProducts": "entities, setEntities",
    "products =": "entities =",
    "products.filter": "entities.filter",
    "Product | null": "Entity | null",
    "product =": "entity =",
    
    "productGroups": "entityGroups",
    "setProductGroups": "setEntityGroups",
    
    # Python generic vars
    "db_product": "db_entity",
    "product_id": "entity_id",
}

def refactor():
    exts = [".py", ".tsx", ".ts"]
    for d in DIRS:
        for root, dirs, files in os.walk(d):
            if "node_modules" in root or ".next" in root or ".git" in root or "__pycache__" in root or ".gemini" in root:
                continue
            for file in files:
                if file == "refactor_product_to_entity.py": continue
                if any(file.endswith(ext) for ext in exts):
                    path = os.path.join(root, file)
                    try:
                        with open(path, "r", encoding="utf-8") as f:
                            content = f.read()
                        
                        new_content = content
                        for old, new in replacements.items():
                            new_content = new_content.replace(old, new)
                            
                        if new_content != content:
                            with open(path, "w", encoding="utf-8") as f:
                                f.write(new_content)
                            print(f"Updated {path}")
                    except Exception as e:
                        print(f"Error reading {path}: {e}")

if __name__ == "__main__":
    refactor()
