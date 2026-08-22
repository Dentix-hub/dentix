# Phase 05 — Stale Asset / PWA Verification

**Date:** 2026-08-21  
**Closeout matrix extended:** 2026-08-22  
**Canonical public frontend:** Vercel (`smartclinic-v2plus`)  
**Canonical production API:** Hugging Face production backend via `frontend/vercel.json`

## Problem contract

A browser can retain Version A HTML/runtime state while a later Version B deployment no longer serves Version A's content-hashed JavaScript asset. A request for the stale Version A asset then returns 404. Vite surfaces failed dynamic-preload resolution through the cancelable `vite:preloadError` event.

The production recovery contract therefore has two independent requirements:

1. each deployed build must reference only its own current content-hashed assets and must not retain outdated Workbox precache entries; and
2. a stale-client preload failure must trigger one controlled page reload, with a cooldown preventing a reload loop.

## Existing runtime controls

The application installs `installPreloadRecovery()` from `frontend/src/main.jsx` before rendering the React application.

`frontend/src/pwa/preloadRecovery.js`:

- listens for `vite:preloadError`;
- prevents the stale preload error when recovery is allowed;
- stores the reload timestamp in session storage;
- reloads the page;
- suppresses another reload within the 30-second cooldown.

`frontend/vite.config.js` configures Workbox with `cleanupOutdatedCaches: true`, precaches content-hashed static assets, uses `/index.html` for SPA navigation, denies `/api/` from the navigation fallback, and keeps API requests `NetworkOnly`.

The service-worker update contract is intentionally prompt-driven: `registerType: 'prompt'`, `skipWaiting: false`, and `clientsClaim: false`. `frontend/src/components/InstallPrompt.jsx` calls `updateServiceWorker(true)` only when the user accepts the update and calls `setNeedRefresh(false)` when the user defers it.

## Deterministic Version A -> Version B reproduction

`frontend/scripts/verify-stale-deployment-recovery.mjs` turns the production failure mechanism into a repeatable CI contract using the real frontend build:

1. build the unmodified application as Version A;
2. make a disposable entry-code change in the CI checkout and build Version B;
3. restore the source file immediately after the second build;
4. extract the Vite module-entry hashes from both generated `index.html` files;
5. require the Version A and Version B entry hashes to differ;
6. require Version B to contain its own entry asset but not the Version A entry asset;
7. require Version B's generated service worker to reference the current entry and exclude the stale Version A entry;
8. serve the Version B output through a temporary static server;
9. request the Version A asset from the Version B surface and require HTTP 404;
10. request the Version B asset and require HTTP 200.

This reproduces the stale deployment condition without depending on retention of a specific historical Vercel preview URL and without introducing a backend `/assets/*` MIME/JSON 404 workaround.

## Browser lifecycle recovery matrix

`frontend/e2e/stale-deployment-recovery.spec.ts` now exercises the real application-level `vite:preloadError` recovery after each browser lifecycle that can leave a client on an older runtime:

| Lifecycle | Permanent assertion |
|---|---|
| Existing stale session | First preload error performs one controlled reload; a second error inside the cooldown does not loop. |
| Soft navigation | `history.pushState` changes the active SPA URL without a document request; a later preload failure reloads that exact route. |
| Hard navigation | A fresh document navigation is completed before the stale preload failure; recovery still reloads successfully. |
| Manual refresh | A user refresh is completed before the stale preload failure; recovery remains armed. |
| Close / reopen | The old tab is closed after recovery; a newly opened app tab has a fresh session-storage cooldown scope and can recover independently. |
| Update accepted | `InstallPrompt.test.jsx` proves confirmation calls `updateServiceWorker(true)`. |
| Update deferred | `InstallPrompt.test.jsx` proves Later clears the refresh prompt with `setNeedRefresh(false)` and does not call `updateServiceWorker`. |

The accepted/deferred assertions are intentionally tied to the actual `virtual:pwa-register/react` API used by the production component rather than an invented service-worker test API.

## Permanent CI gate

`.github/workflows/stale-deployment-recovery.yml` runs independently on pull requests and pushes to `staging` / `main` and requires all of the following on the same tested revision:

- the production-build Version A -> Version B stale-asset reproduction;
- the update-accepted/update-deferred component contracts;
- the preload recovery unit contract; and
- the Chromium browser lifecycle matrix for normal, soft-navigation, hard-navigation, refresh, and close/reopen flows.

Phase 05 is considered closed only after this workflow and the repository's existing required gates are green on the same pull-request head. The fix remains frontend/PWA-scoped; there is no FastAPI-side `/assets/*` 404 handler used as the primary recovery mechanism.
