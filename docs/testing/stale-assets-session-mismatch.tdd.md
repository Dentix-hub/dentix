# Stale assets and session mismatch — TDD evidence

## User journeys

- A user with an older deployed tab receives an explicit update prompt, or one guarded reload when a Vite chunk preload fails.
- Missing JavaScript, PWA, icon, and Workbox files return a real missing-file response instead of the SPA HTML shell.
- A session mismatch immediately blocks stale authenticated UI, ends the server session on a best-effort basis, clears tenant/auth/query/session state, and explains why the user was returned to login.
- Patient images are not retained by a broad service-worker cache; the legacy `images-cache` is removed before the app renders.

## Red evidence

The focused tests were first added against the previous behavior and failed for the intended reasons:

- PWA/deployment suite: 8 failures covering stale asset routing, update handling, missing recovery helper, and invalid/missing icon delivery.
- Icon tracking contract: 1 failure showing the public icons were still ignored by Git.
- Workbox routing contract: 1 failure showing a missing hashed Workbox file matched the SPA fallback.
- Legacy image cache suite: failures showing broad `CacheFirst` image caching remained and startup cleanup was absent or ordered after rendering.
- Preload cooldown and localization suite: 4 failures showing cooldown events were swallowed and the update prompt was hard-coded.
- Session mismatch suite: 3 interceptor failures plus 1 login-message failure.
- Session teardown security suite: 4 failures covering loading state, query cancellation, cleanup after logout failure, and tenant reset.

## Green evidence

- Focused PWA/deployment suite: 4 files, 15 tests passed.
- Broader auth/API suite: 26 tests passed.
- Complete frontend suite: 36 files, 164 tests passed.
- Production build: passed; Vite processed 4,162 modules and generated the service worker and Workbox bundle.
- Generated service worker inspection: API requests remain `NetworkOnly`; no broad image matcher, `CacheFirst`, or `images-cache` remains.
- Scoped ESLint for all touched JavaScript/JSX files: passed.
- `git diff --check`: passed.

## Coverage and remaining validation

The repository does not include a Vitest coverage provider, so no percentage claim is made. The behavior is covered by focused regression tests and the full frontend suite. Live verification on the production deployment remains a post-deploy check because the fixed assets and routing rules are not active until the commit is deployed.

## Merge evidence

No commit was created during the red/green cycle. Commit and push are intentionally held behind the final approval gate, with this report preserving the test evidence.
