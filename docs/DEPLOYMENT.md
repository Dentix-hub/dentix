# Dentix — Deployment Guide

## Required Environment Variables

| Variable | Required | Default | Description |
|---------|----------|---------|-------------|
| `DATABASE_URL` | ✅ | — | PostgreSQL connection string |
| `SECRET_KEY` | ✅ | — | JWT signing key (min 32 chars) |
| `ENCRYPTION_KEY` | ✅ | — | Fernet key for PII encryption |
| `ENVIRONMENT` | ✅ | `development` | `development` / `staging` / `production` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | ❌ | `60` | JWT access token lifetime |
| `REFRESH_TOKEN_EXPIRE_DAYS` | ❌ | `7` | JWT refresh token lifetime |
| `CLOUDINARY_URL` | ❌ | — | For file attachments |
| `GOOGLE_DRIVE_CREDENTIALS` | ❌ | — | For backup feature |

## Local Development Setup

```bash
# 1. Clone and setup
git clone <repo>
cd DENTIX

# 2. Backend
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\\Scripts\\activate
pip install -r requirements.txt

# 3. Environment
cp .env.example .env
# Edit .env with your values

# 4. Database
alembic upgrade head

# 5. Run
uvicorn backend.main:app --reload --port 8000

# Frontend (separate terminal)
cd frontend
npm install
npm run dev
```

## Production Deployment

Recommended using Docker Compose or CI/CD Pipeline as defined in `.github/workflows/ci.yml`.
