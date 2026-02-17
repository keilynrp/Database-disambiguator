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

### HarmonizationLog

| Field              | Type     | Description                            |
|--------------------|----------|----------------------------------------|
| `id`               | int      | Auto-increment primary key             |
| `step_id`          | string   | Pipeline step identifier               |
| `step_name`        | string   | Human-readable step name               |
| `records_updated`  | int      | Number of records affected             |
| `fields_modified`  | string   | JSON array of field names modified     |
| `executed_at`      | datetime | Timestamp of execution                 |
| `details`          | string   | JSON with sample changes (first 20)    |
| `reverted`         | bool     | Whether the operation has been undone  |

### HarmonizationChangeRecord

| Field       | Type   | Description                                    |
|-------------|--------|------------------------------------------------|
| `id`        | int    | Auto-increment primary key                     |
| `log_id`    | int    | Foreign key to `HarmonizationLog.id`           |
| `record_id` | int    | Foreign key to the affected `RawProduct.id`    |
| `field`     | string | Column name that was modified                  |
| `old_value` | string | Value before harmonization (for undo)          |
| `new_value` | string | Value after harmonization (for redo)           |

---

## Harmonization Pipeline

### `GET /harmonization/steps`

List all pipeline steps with their execution status.

**Response:**

```json
{
  "steps": [
    {
      "step_id": "consolidate_brands",
      "name": "Consolidate Brand Columns",
      "description": "Merge brand_lower into brand_capitalized when empty...",
      "order": 1,
      "status": "pending",
      "last_run": null,
      "last_records_updated": null
    }
  ],
  "total_products": 5430
}
```

---

### `POST /harmonization/preview/{step_id}`

Dry-run a pipeline step. Returns proposed changes without applying them.

**Path Parameters:**

| Parameter | Type   | Description                                                              |
|-----------|--------|--------------------------------------------------------------------------|
| `step_id` | string | One of: `consolidate_brands`, `clean_product_names`, `standardize_volumes`, `consolidate_gtin`, `fix_export_typos` |

**Response:**

```json
{
  "step_id": "consolidate_brands",
  "step_name": "Consolidate Brand Columns",
  "total_affected": 120,
  "changes": [
    { "record_id": 42, "field": "brand_capitalized", "old_value": null, "new_value": "Samsung" }
  ],
  "sample_changes": [...]
}
```

---

### `POST /harmonization/apply/{step_id}`

Execute a pipeline step and commit changes. Logs execution to `harmonization_logs` and stores every individual field change to `harmonization_change_records` for undo/redo support.

**Response:**

```json
{
  "step_id": "consolidate_brands",
  "step_name": "Consolidate Brand Columns",
  "records_updated": 120,
  "fields_modified": ["brand_capitalized"],
  "log_id": 1
}
```

---

### `POST /harmonization/apply-all`

Run all 5 pipeline steps sequentially. Each step stores its full change history.

**Response:**

```json
{
  "results": [
    { "step_id": "consolidate_brands", "step_name": "...", "records_updated": 120, "fields_modified": ["brand_capitalized"], "log_id": 1 },
    { "step_id": "clean_product_names", "step_name": "...", "records_updated": 45, "fields_modified": ["product_name"], "log_id": 2 }
  ],
  "total_steps": 5
}
```

---

### `GET /harmonization/logs`

Return execution history (last 50 entries), including undo/redo status.

**Response:**

```json
[
  {
    "id": 1,
    "step_id": "consolidate_brands",
    "step_name": "Consolidate Brand Columns",
    "records_updated": 120,
    "fields_modified": ["brand_capitalized"],
    "executed_at": "2026-02-15T01:23:45",
    "reverted": false
  }
]
```

---

### `POST /harmonization/undo/{log_id}`

Revert all changes from a specific harmonization execution. Restores the previous (old) values for every record affected by that operation.

**Path Parameters:**

| Parameter | Type | Description                         |
|-----------|------|-------------------------------------|
| `log_id`  | int  | ID of the harmonization log entry   |

**Response:**

```json
{
  "log_id": 1,
  "action": "undo",
  "records_restored": 120,
  "step_id": "consolidate_brands",
  "step_name": "Consolidate Brand Columns"
}
```

**Errors:**
- `404` — Log entry not found
- `400` — Already reverted, or no change records available

---

### `POST /harmonization/redo/{log_id}`

Re-apply a previously reverted harmonization operation.

**Path Parameters:**

| Parameter | Type | Description                         |
|-----------|------|-------------------------------------|
| `log_id`  | int  | ID of the harmonization log entry   |

**Response:**

```json
{
  "log_id": 1,
  "action": "redo",
  "records_restored": 120,
  "step_id": "consolidate_brands",
  "step_name": "Consolidate Brand Columns"
}
```

**Errors:**
- `404` — Log entry not found
- `400` — Not reverted (cannot redo an active operation)

### Pipeline Steps Reference

| Step ID               | Name                          | Fields Affected                          |
|-----------------------|-------------------------------|------------------------------------------|
| `consolidate_brands`  | Consolidate Brand Columns     | `brand_capitalized` (from `brand_lower`) |
| `clean_product_names` | Clean Product Names           | `product_name`                           |
| `standardize_volumes` | Standardize Volume/Units      | `product_name`, `measure`                |
| `consolidate_gtin`    | Consolidate GTIN Columns      | `gtin`, `gtin_reason`                    |
| `fix_export_typos`    | Fix Export Column Name Typos  | Export headers (not product data)        |
