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

### Official environments

| Git branch | Environment | Platform | Deployment |
|------------|-------------|----------|------------|
| `main` | Production | DigitalOcean Droplet | SSH + Docker Compose |
| `staging` | Staging | Hugging Face Space | Git push to the Space |

The authoritative pipelines are `.github/workflows/ci.yml` and
`.github/workflows/cd.yml`. CI builds the production image once, pushes immutable
`ghcr.io/<owner>/<repo>:<git-sha>` and `:main` tags, and exports BuildKit cache to
GHCR. CD deploys only the matching SHA after the entire CI workflow succeeds.

The Droplet never runs `docker build`. It downloads the tested image, verifies its
`org.opencontainers.image.revision` label, tags it locally, and starts it with
Docker Compose. A small configuration release is extracted into
`<DO_APP_PATH>/releases/<git-sha>` and the stable Compose project name is `dentix`,
so named volumes survive releases.

### GitHub environments and secrets

Create protected GitHub environments named `production` and `staging`. Production
should require a reviewer. Configure these secrets:

| Environment | Secret | Purpose |
|-------------|--------|---------|
| Production | `DO_HOST` | Droplet hostname or IP |
| Production | `DO_USER` | Restricted SSH deployment user (`root` only for the current legacy setup) |
| Production | `DO_SSH_PORT` | SSH port; defaults to `22` |
| Production | `DO_SSH_PRIVATE_KEY` | Private key dedicated to deployment |
| Production | `DO_SSH_KNOWN_HOSTS` | Optional pinned, verified Droplet host key; defaults to the reviewed `.github/droplet_known_hosts` file |
| Production | `DO_APP_PATH` | Absolute app root; falls back to legacy `DO_DEPLOY_PATH`, then `/root/dentix` |
| Production | `BACKEND_URL` | Public production URL used by the health check |
| Staging | `HF_TOKEN` | Hugging Face write token |
| Staging | `HF_STAGING_SPACE` | Space identifier, for example `org/dentix-staging` |
| Staging | `STAGING_BACKEND_URL` | Public staging URL used by the health check |

Never use `HF_SPACE` for production. Production is not pushed to Hugging Face.
No permanent GHCR credential is required: GitHub Actions uses its short-lived
`GITHUB_TOKEN` to publish and to authenticate the Droplet for the single pull.

### One-time Droplet preparation

1. Install Docker Engine, the Docker Compose plugin, `curl`, and `tar`. BuildKit,
   Node.js, Python compilers, and application source code are not required there.
2. Create `<DO_APP_PATH>/releases` and `<DO_APP_PATH>/.env`, owned by the deployment user.
3. Populate `.env` using `.env.example`, including database TLS, application secrets,
   public URLs, Cloudinary, the payment webhook secret, and
   `DENTIX_IMAGE=dentix-app:production`.
4. Allow inbound SSH, HTTP, and HTTPS. Port `7860` is bound to localhost by Compose
   and must not be exposed publicly.
5. Pin the Droplet SSH host key in `DO_SSH_KNOWN_HOSTS` after verifying its fingerprint.

The backend container applies Alembic migrations and checks migration health before
serving traffic. The pipeline stops workers during that step, waits for the backend
health endpoint, then starts workers and Caddy. If health verification fails, the
deployment job fails and prints the backend logs.

### Dependency and image policy

- `requirements.txt` is the human-maintained production input.
- `requirements.lock` is resolved specifically for Python 3.11 on Linux and is the
  only Python dependency file installed in production images.
- `requirements.dev.txt` adds test and security tools and is never copied into the
  runtime image.
- RAG uses Chroma's ONNX default embedding function. Do not add
  `sentence-transformers` or GPU-enabled PyTorch to the shared API image.
- Chroma is temporarily constrained below 1.0 because the audited 1.x Python
  server line has an unpatched RCE advisory. Dentix uses only `PersistentClient`;
  do not expose or start a Chroma HTTP server from this image.
- JWT signing uses PyJWT's cryptography backend; do not restore `python-jose`,
  which pulls the unpatched pure-Python `ecdsa` implementation.

Regenerate the production lock deliberately after changing `requirements.txt`:

```bash
uv pip compile requirements.txt \
  --python-version 3.11 \
  --python-platform x86_64-manylinux_2_28 \
  --output-file requirements.lock \
  --no-emit-index-url \
  --no-annotate
```
