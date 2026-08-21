# Phase 1 — Live Production Surface Status

- Status: **PASS**
- Verified: 2026-08-21
- Case: **A — public SPA/assets on Vercel; API on Hugging Face**
- Production custom domains: `dentixs.app`, `www.dentixs.app`
- Production Vercel project: `smartclinic-v2plus`
- Canonical API rewrite source: `frontend/vercel.json`

Connected Vercel verification on 2026-08-21 confirmed the production custom domains are assigned to `smartclinic-v2plus`, while the separate `dentix-staging` project has only Vercel-managed staging domains. Repository routing sends `/api/:path*` to the production Hugging Face backend.

This status is evidence for the production-architecture normalization program. External hosting bindings remain mutable and must be reverified before future routing changes.
