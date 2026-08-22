# Phase 05 — Real Vercel Serving-Surface Verification

**Verification date:** 2026-08-22  
**Scope:** supplement the permanent deterministic stale-deployment recovery gate with evidence from the actual Vercel production serving surface.

## Why this verification exists

The permanent Phase 5 CI gate already proves the application-level contract by building Version A and Version B, requiring different Vite entry hashes, proving Version A's stale entry is unavailable on the Version B surface, and validating the browser `vite:preloadError` recovery/cooldown behavior.

The final acceptance re-audit asked for an additional proof that the same stale-hash condition exists on the real production hosting surface rather than only on a temporary local static server.

## Observed Vercel transition

A retained historical production deployment for repository revision `5819605dce656039974d461a85636bdc68f72dca` returned HTTP 200 for its immutable deployment root and its generated HTML referenced this Vite entry asset:

```text
/assets/index-DUKsAEeU.js
```

The current production serving surface uses a different Vite entry asset:

```text
/assets/index-DKwT6nnu.js
```

Direct checks against the current custom domain produced:

| Request on current `www.dentixs.app` | Result |
|---|---:|
| historical entry `/assets/index-DUKsAEeU.js` | **HTTP 404 NOT_FOUND** |
| current entry `/assets/index-DKwT6nnu.js` | **HTTP 200 OK** |

The old and current entry hashes are therefore different, and the current production surface does not retain the historical entry under the custom domain.

## Interpretation

This is the exact hosting-side prerequisite for the stale-tab failure class:

1. a browser that loaded the historical deployment can retain Version-A runtime state;
2. production later serves Version B;
3. a delayed/lazy request for Version A's entry/chunk namespace can resolve to a resource that is no longer present on the current custom-domain deployment;
4. Vercel returns 404 for that historical hash;
5. Dentix's `vite:preloadError` recovery path must therefore recover the client rather than allowing a broken session or reload loop.

This verification deliberately does **not** mutate production or deploy a synthetic marker build. It uses two already-existing Vercel deployments and the current public custom domain, so it demonstrates the real serving behavior without creating production risk.

## Combined Phase 5 evidence

Phase 5 acceptance is based on both layers:

- **real platform evidence (this document):** a historical Vite entry referenced by a retained Vercel production deployment is 404 on the current public production surface while the current entry is 200;
- **permanent executable regression gate:** `.github/workflows/stale-deployment-recovery.yml` deterministically reproduces A→B stale entry behavior and runs the Chromium recovery/cooldown contract on every relevant PR/push.

The platform observation proves that the stale-hash failure mode is not hypothetical on the actual hosting topology. The permanent gate proves that application recovery remains enforced as the code evolves.

## Evidence boundary

Vercel deployment URLs, asset hashes, and HTTP responses are point-in-time platform evidence. They are not configuration truth and should not be hard-coded into runtime logic. Future hosting/topology changes require re-verification, while the deterministic CI recovery contract remains the long-lived regression control.
