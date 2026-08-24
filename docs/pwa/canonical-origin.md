# Canonical PWA Origin

**Canonical production origin:** `https://www.dentixs.app`
**Status:** Locked invariant — verified live 2026-08-24 (Master Plan Phase 1 / PR-PWA-01).

## Why this matters

Installed web apps are **origin-bound**. `dentixs.app`, `www.dentixs.app`, and
any `*.vercel.app` alias are *different installed applications* with separate:

- Home Screen apps;
- cookie stores / login behavior;
- push subscriptions;
- Service Worker registrations;
- (future) WebAuthn / passkey Relying-Party bindings.

A user who installs Dentix from two origins gets two disconnected installs.

## Verified invariant

```text
https://dentixs.app      → 308 Permanent Redirect → https://www.dentixs.app
https://www.dentixs.app  → 200 OK
```

This matches current Vercel guidance (primary `www` domain, apex redirecting
to it). The redirect is configured at the Vercel project level, not in
`frontend/vercel.json`; any change to it requires an architecture review.

## Rules

1. All product links, emails, QR codes, docs and onboarding must reference
   `https://www.dentixs.app`.
2. Never use stale `*.vercel.app` addresses in product metadata.
3. Manifest `id` is `"/"` on the canonical origin (see `vite.config.js`);
   do not change it casually — it re-identifies the installed app.
4. Canonical metadata in `frontend/index.html` (`rel=canonical`, `og:url`,
   `twitter:url`) must keep pointing at the canonical origin.

## Legacy origins

An installed PWA on an old origin cannot be transformed into the canonical
installation automatically. If an inventory of access logs shows meaningful
legacy-origin traffic or existing installs:

1. display a migration notice on the old origin;
2. direct users to the canonical origin;
3. explain a one-time reinstall if necessary;
4. avoid forcing logout while clinical work is active.

Until such evidence exists, no runtime migration banner ships.
