# DB Disambiguator

A full-stack tool for importing, browsing, and cleaning product catalog data. It detects inconsistencies in key fields (brands, models, product types) using fuzzy string matching, and provides an authority-control workflow to normalize values across the entire database.

## Features

- **Product Catalog** -- Browse, search, inline-edit, and delete product records. Now features **separate SKU/GTIN columns** and **dynamic pagination** (10-100 rows).
- **Excel Import / Export** -- Upload `.xlsx` files preserving the original Spanish column format; export filtered results back to Excel.
- **Data Disambiguation** -- Fuzzy matching groups similar values (typos, casing, synonyms) so you can spot inconsistencies at a glance.
- **Authority Control** -- Define canonical values and create normalization rules; apply them in bulk to harmonize the database. Includes **client-side pagination** for efficient handling of large variation groups.
- **Analytics Dashboard** -- Key metrics: total products, unique brands/models, validation status, identifier coverage, top brands, and type distribution.
- **Database Purge** -- Start fresh by deleting all records (with optional rule cleanup) from the Import / Export page.

## Tech Stack

| Layer    | Technology                          |
|----------|-------------------------------------|
| Backend  | Python 3.10+, FastAPI, SQLAlchemy, SQLite |
| Frontend | Next.js 16, React 19, TypeScript 5, Tailwind CSS 4 |
| Fuzzy matching | thefuzz (token_sort_ratio) + python-Levenshtein |

## Quick Start

### Prerequisites

- Python 3.10+
- Node.js 18+
- npm 9+

### 1. Clone the repository

```bash
git clone https://github.com/<your-user>/DBDesambiguador.git
cd DBDesambiguador
```

### 2. Backend

```bash
# Create and activate virtual environment
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Start the API server (default: http://localhost:8000)
uvicorn backend.main:app --reload
```

### 3. Frontend

```bash
cd frontend
npm install
npm run dev
```

Open **http://localhost:3004** in your browser.

### 4. Import data

You can import data through the UI (Import / Export page) or via CLI:

```bash
# Place your .xlsx file in data/, then:
python -m scripts.import_data
```

## Project Structure

```
DBDesambiguador/
├── backend/                # FastAPI application
│   ├── main.py             # API routes & business logic
│   ├── models.py           # SQLAlchemy models (RawProduct, NormalizationRule)
│   ├── schemas.py          # Pydantic schemas
│   └── database.py         # Engine & session configuration
│
├── frontend/               # Next.js application
│   ├── app/
│   │   ├── page.tsx                    # Product Catalog (home)
│   │   ├── layout.tsx                  # Root layout (sidebar + header)
│   │   ├── globals.css                 # Global styles
│   │   ├── analytics/page.tsx          # Analytics dashboard
│   │   ├── disambiguation/page.tsx     # Disambiguation tool
│   │   ├── authority/page.tsx          # Authority control
│   │   ├── import-export/page.tsx      # Import / Export + Purge
│   │   └── components/
│   │       ├── Sidebar.tsx             # Navigation sidebar
│   │       ├── Header.tsx              # Page header
│   │       ├── ProductTable.tsx        # Product CRUD table
│   │       ├── DisambiguationTool.tsx  # Fuzzy-match viewer
│   │       └── MetricCard.tsx          # Stat card widget
│   ├── package.json
│   └── tsconfig.json
│
├── scripts/                # Utility CLI scripts
│   ├── analyze_excel.py    # Extract column names from .xlsx
│   └── import_data.py      # Bulk import from .xlsx
│
├── data/                   # Data files (gitignored .xlsx)
│   ├── columns.txt         # Reference: original Excel column names
│   └── README.md
│
├── docs/                   # Documentation
│   ├── API.md              # Full API reference
│   └── CONTRIBUTING.md     # Contribution guidelines
│
├── .gitignore
├── requirements.txt        # Python dependencies
├── LICENSE
└── README.md               # This file
```

## API Overview

The backend exposes a REST API at `http://localhost:8000`. Interactive docs are available at `/docs` (Swagger UI) and `/redoc`.

| Method   | Endpoint                | Description                          |
|----------|-------------------------|--------------------------------------|
| `GET`    | `/health`               | Health check                         |
| `GET`    | `/products`             | List products (search, pagination)   |
| `PUT`    | `/products/{id}`        | Update a product                     |
| `DELETE` | `/products/{id}`        | Delete a product                     |
| `DELETE` | `/products/all`         | Purge all products                   |
| `POST`   | `/upload`               | Import Excel file                    |
| `GET`    | `/export`               | Export to Excel                      |
| `GET`    | `/stats`                | Aggregated statistics                |
| `GET`    | `/disambiguate/{field}` | Fuzzy-match groups for a field       |
| `GET`    | `/authority/{field}`    | Disambiguation + rule annotations    |
| `GET`    | `/rules`                | List normalization rules             |
| `POST`   | `/rules/bulk`           | Create rules from a variation group  |
| `DELETE` | `/rules/{id}`           | Delete a rule                        |
| `POST`   | `/rules/apply`          | Apply rules to normalize the DB      |

For detailed request/response schemas, see [docs/API.md](docs/API.md).

## Workflow

```
 Excel file
     │
     ▼
  ┌──────────┐     ┌──────────────┐     ┌─────────────────┐
  │  Import   │────▶│  Product DB  │────▶│  Disambiguation │
  └──────────┘     └──────────────┘     └────────┬────────┘
                          │                      │
                          │                      ▼
                          │              ┌───────────────┐
                          │              │   Authority    │
                          │              │   Control      │
                          │              └───────┬───────┘
                          │                      │
                          │            Create normalization
                          │                 rules
                          │                      │
                          ▼                      ▼
                   ┌──────────────┐     ┌───────────────┐
                   │   Analytics  │     │  Apply Rules   │
                   └──────────────┘     └───────────────┘
                                               │
                                               ▼
                                        Normalized DB
                                               │
                                               ▼
                                        ┌──────────┐
                                        │  Export   │
                                        └──────────┘
```

1. **Import** your product catalog from Excel.
2. **Browse** and review data in the Product Catalog.
3. **Disambiguate** key fields to find typos, duplicates, and variations.
4. **Define canonical values** in Authority Control and save normalization rules.
5. **Apply rules** to update all matching records in the database.
6. **Export** the cleaned data back to Excel.

## License

This project is licensed under the Apache License 2.0. See [LICENSE](LICENSE) for details.
