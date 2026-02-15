# Contributing

Thank you for your interest in contributing to DB Disambiguator!

## Development Setup

### Prerequisites

- Python 3.10+
- Node.js 18+
- npm 9+

### Backend

```bash
# Create virtual environment
python -m venv .venv

# Activate it
# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Start the API server
uvicorn backend.main:app --reload
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

The frontend runs at `http://localhost:3004` and the backend at `http://localhost:8000`.

## Project Structure

```
DBDesambiguador/
├── backend/          # FastAPI application
│   ├── main.py       # API routes and business logic
│   ├── models.py     # SQLAlchemy ORM models
│   ├── schemas.py    # Pydantic validation schemas
│   └── database.py   # Database engine configuration
├── frontend/         # Next.js application
│   └── app/          # App Router pages and components
├── scripts/          # Utility CLI scripts
├── data/             # Data files (gitignored .xlsx)
├── docs/             # Documentation
└── requirements.txt  # Python dependencies
```

## Code Style

### Backend (Python)

- Follow PEP 8 conventions.
- Use type hints where practical.
- Keep endpoints in `main.py` unless the file grows significantly.

### Frontend (TypeScript / React)

- Use functional components with hooks.
- Follow the existing Tailwind CSS patterns (rounded-2xl cards, consistent color palette).
- Place reusable components in `frontend/app/components/`.
- Page routes go in their own directory under `frontend/app/`.

## Making Changes

1. Create a branch from `main`.
2. Make your changes with clear, descriptive commits.
3. Test both backend and frontend manually:
   - Backend: verify endpoints via `http://localhost:8000/docs` (Swagger UI).
   - Frontend: navigate through all pages and verify functionality.
4. Open a pull request with a summary of what changed and why.

## Reporting Issues

Open an issue on GitHub with:
- Steps to reproduce the problem.
- Expected vs actual behavior.
- Browser / OS / Python / Node versions if relevant.
