# DENTIX Human Developer Onboarding Guide

## 1. Prerequisites
- **Python**: 3.11.x (managed via `uv`)
- **Node.js**: >= 18.x with `npm`
- **Database**: PostgreSQL 15+ (with Row Level Security support) or local SQLite during unit testing.

---

## 2. Quickstart Setup

### Backend Setup
1. Clone repository and navigate to root:
   ```bash
   git clone <repo_url>
   cd DENTIX
   ```
2. Sync dependencies:
   ```bash
   uv sync
   ```
3. Run Alembic migrations:
   ```bash
   uv run alembic -c backend/alembic.ini upgrade head
   ```
4. Start dev server:
   ```bash
   uv run uvicorn backend.main:app --reload --port 8000
   ```

### Frontend Setup
1. Navigate to frontend:
   ```bash
   cd frontend
   npm install
   ```
2. Start Vite dev server:
   ```bash
   npm run dev
   ```

---

## 3. Verification & Linting
- **Python Lint**: `uv run ruff check --config ruff.toml backend/`
- **Backend Tests**: `uv run pytest backend/tests/`
- **Frontend Tests**: `npm test` inside `frontend/`
