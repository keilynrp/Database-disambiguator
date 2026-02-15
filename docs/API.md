# API Reference

Base URL: `http://localhost:8000`

---

## Health

### `GET /health`

Health check endpoint.

**Response:**

```json
{ "status": "ok" }
```

---

## Products

### `GET /products`

List products with optional search and pagination.

| Parameter | Type   | Default | Description                            |
|-----------|--------|---------|----------------------------------------|
| `skip`    | int    | 0       | Number of records to skip              |
| `limit`   | int    | 100     | Maximum number of records to return    |
| `search`  | string | null    | Search across name, brand, model, SKU  |

**Response:** `Product[]`

```json
[
  {
    "id": 1,
    "product_name": "Cable HDMI 2m",
    "brand_capitalized": "Generic",
    "model": "HDMI-2M",
    "sku": "SKU-001",
    "product_type": "Cables",
    "validation_status": "pending",
    ...
  }
]
```

---

### `PUT /products/{product_id}`

Update a product by ID. Accepts partial updates (only the fields sent will be changed).

**Path Parameters:**

| Parameter    | Type | Description |
|--------------|------|-------------|
| `product_id` | int  | Product ID  |

**Request Body:** `ProductBase` (all fields optional)

```json
{
  "product_name": "Cable HDMI 3m",
  "brand_capitalized": "Belkin"
}
```

**Response:** `Product` (the updated record)

---

### `DELETE /products/{product_id}`

Delete a single product.

**Response:**

```json
{ "message": "Product deleted", "id": 42 }
```

---

### `DELETE /products/all`

Purge all product records from the database. Optionally also delete normalization rules.

| Parameter       | Type | Default | Description                       |
|-----------------|------|---------|-----------------------------------|
| `include_rules` | bool | false   | Also delete all normalization rules |

**Response:**

```json
{
  "message": "Database purged successfully",
  "products_deleted": 5430,
  "rules_deleted": 0
}
```

---

## Import / Export

### `POST /upload`

Upload an Excel file (`.xlsx`) to import product data.

**Content-Type:** `multipart/form-data`

| Field  | Type | Description          |
|--------|------|----------------------|
| `file` | File | Excel file (.xlsx)   |

**Response:**

```json
{
  "message": "Successfully imported 5430 rows",
  "total_rows": 5430,
  "matched_columns": ["Nombre del Producto", "Marca", ...],
  "unmatched_columns": ["Custom Column"]
}
```

---

### `GET /export`

Export products to Excel format. Returns a downloadable `.xlsx` file with the original Spanish column headers.

| Parameter | Type   | Default | Description                         |
|-----------|--------|---------|-------------------------------------|
| `search`  | string | null    | Filter exported data by search term |

**Response:** Binary `.xlsx` file (`application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`)

---

## Analytics

### `GET /stats`

Retrieve aggregated statistics about the product database.

**Response:**

```json
{
  "total_products": 5430,
  "unique_brands": 120,
  "unique_models": 340,
  "unique_product_types": 25,
  "validation_status": {
    "pending": 5000,
    "valid": 400,
    "invalid": 30
  },
  "identifier_coverage": {
    "with_sku": 3200,
    "with_barcode": 1500,
    "with_gtin": 800,
    "total": 5430
  },
  "top_brands": [
    { "name": "Samsung", "count": 320 }
  ],
  "type_distribution": [
    { "name": "Electronics", "count": 1200 }
  ],
  "status_distribution": [
    { "name": "Activo", "count": 5000 }
  ]
}
```

---

## Disambiguation

### `GET /disambiguate/{field}`

Find groups of similar values in a field using fuzzy string matching.

**Path Parameters:**

| Parameter | Type   | Description                                                     |
|-----------|--------|-----------------------------------------------------------------|
| `field`   | string | One of: `brand_capitalized`, `product_name`, `model`, `product_type` |

**Query Parameters:**

| Parameter   | Type | Default | Description                    |
|-------------|------|---------|--------------------------------|
| `threshold` | int  | 80      | Fuzzy match threshold (0–100)  |

**Response:**

```json
{
  "groups": [
    {
      "main": "Samsung Electronics",
      "variations": ["Samsung Electronics", "SAMSUNG", "Samsnug"],
      "count": 3
    }
  ],
  "total_groups": 15
}
```

---

## Authority Control

### `GET /authority/{field}`

Combined view: disambiguation groups annotated with existing normalization rules.

**Path Parameters:** Same as `/disambiguate/{field}`

**Response:**

```json
{
  "groups": [
    {
      "main": "Samsung Electronics",
      "variations": ["Samsung Electronics", "SAMSUNG", "Samsnug"],
      "count": 3,
      "has_rules": true,
      "resolved_to": "Samsung"
    }
  ],
  "total_groups": 15,
  "total_rules": 8,
  "pending_groups": 7
}
```

---

## Normalization Rules

### `GET /rules`

List all normalization rules, optionally filtered by field.

| Parameter    | Type   | Default | Description          |
|--------------|--------|---------|----------------------|
| `field_name` | string | null    | Filter by field name |

**Response:** `Rule[]`

```json
[
  {
    "id": 1,
    "field_name": "brand_capitalized",
    "original_value": "Samsnug",
    "normalized_value": "Samsung",
    "is_regex": false
  }
]
```

---

### `POST /rules/bulk`

Create normalization rules for a group of variations mapping to a single canonical value.

**Request Body:**

```json
{
  "field_name": "brand_capitalized",
  "canonical_value": "Samsung",
  "variations": ["Samsung", "SAMSUNG", "Samsnug"]
}
```

**Response:**

```json
{
  "message": "Rules saved for 'Samsung'",
  "variations": 2
}
```

---

### `DELETE /rules/{rule_id}`

Delete a single normalization rule.

**Response:**

```json
{ "message": "Rule deleted" }
```

---

### `POST /rules/apply`

Apply all normalization rules to the product database, updating matching records.

| Parameter    | Type   | Default | Description                     |
|--------------|--------|---------|---------------------------------|
| `field_name` | string | null    | Apply only rules for this field |

**Response:**

```json
{
  "message": "Applied 12 rules",
  "rules_applied": 12,
  "records_updated": 340
}
```

---

## Data Models

### Product

| Field                    | Type   | Description                            |
|--------------------------|--------|----------------------------------------|
| `id`                     | int    | Auto-increment primary key             |
| `product_name`           | string | Product name                           |
| `classification`         | string | Product classification                 |
| `product_type`           | string | Product type / category                |
| `brand_capitalized`      | string | Brand name                             |
| `model`                  | string | Model identifier                       |
| `sku`                    | string | Stock Keeping Unit                     |
| `barcode`                | string | Barcode value                          |
| `gtin`                   | string | Global Trade Item Number               |
| `status`                 | string | Product status                         |
| `validation_status`      | string | One of: `pending`, `valid`, `invalid`  |
| `variant`                | string | Variant description                    |
| `variant_status`         | string | Variant status                         |
| ...                      | string | Additional mapped fields (see models.py) |

### NormalizationRule

| Field              | Type   | Description                        |
|--------------------|--------|------------------------------------|
| `id`               | int    | Auto-increment primary key         |
| `field_name`       | string | Target field (e.g. `brand_capitalized`) |
| `original_value`   | string | Value to match                     |
| `normalized_value` | string | Canonical replacement value        |
| `is_regex`         | bool   | Whether `original_value` is a regex |
