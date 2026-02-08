# 🚀 Smart Clinic Deployment Guide

> **Environments**: HuggingFace Spaces (Backend) + Vercel (Frontend)

---

## Prerequisites

- Python 3.11+
- Node.js 18+
- PostgreSQL database
- Redis (optional, for caching)
- Groq API key

---

## Environment Variables

### Backend (Required)

```bash
# Database
DATABASE_URL=postgresql://user:pass@host:5432/dbname
DB_SSL_MODE=require

# Security (GENERATE NEW ONES!)
SECRET_KEY=<generate-32-char-random>
ENCRYPTION_KEY=<generate-fernet-key>

# AI
GROQ_API_KEY=<your-groq-key>

# App
BACKEND_PUBLIC_URL=https://your-backend.hf.space
ENVIRONMENT=production
```

### Frontend

```bash
VITE_API_URL=https://your-backend.hf.space
```

---

## Generate Security Keys

```bash
# SECRET_KEY
python -c "import secrets; print(secrets.token_urlsafe(32))"

# ENCRYPTION_KEY
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

---

## Backend Deployment (HuggingFace)

1. **Create Space**
   - Go to huggingface.co/spaces
   - Create new Space (Docker SDK)

2. **Configure Secrets**
   - Go to Space Settings → Variables
   - Add all required environment variables

3. **Push Code**
   ```bash
   git remote add hf https://huggingface.co/spaces/YOUR_SPACE
   git push hf main
   ```

4. **Verify**
   ```bash
   curl https://your-space.hf.space/health
   ```

---

## Frontend Deployment (Vercel)

1. **Connect Repository**
   - Link GitHub repo to Vercel

2. **Configure**
   - Framework: Vite
   - Build Command: `npm run build`
   - Output: `dist`

3. **Environment**
   - Add `VITE_API_URL`

4. **Deploy**
   - Push to main branch

---

## Database Setup

```sql
-- Create database
CREATE DATABASE smart_clinic;

-- Run migrations (automatic on startup)
-- Or manually:
python -c "from backend.database import Base, engine; Base.metadata.create_all(engine)"
```

---

## Health Check

```bash
# Basic
curl https://your-backend/health

# Detailed (requires auth)
curl -H "Authorization: Bearer TOKEN" https://your-backend/health/detailed
```

---

## Rollback

```bash
# Backend
git revert HEAD
git push hf main

# Frontend
# Use Vercel dashboard → Deployments → Rollback
```

---

## Monitoring

- `/metrics` - Prometheus metrics
- `/health/detailed` - Component status
- Logs: HuggingFace Space logs tab
