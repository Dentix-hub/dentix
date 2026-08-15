# Diagnostic: Stale Asset 404 (`index-BLKNZtVt.css`) + `/api/auth/session` 401

## Confirmed so far
`https://dentixs.app/assets/index-BLKNZtVt.css` returns a genuine 404 right now
(verified by direct fetch, not just a browser console read). Whatever `index.html`
the reporting browser had loaded references a CSS bundle that no longer exists on
the server. This is a *discovery* pass only — do not change any config yet.

## Step 1 — What does the server currently have vs. what does index.html ask for?
```bash
docker exec -it <backend_container> sh -c "ls -la /app/static/assets/ | grep 'index-.*\.css'"
docker exec -it <backend_container> sh -c "grep -o 'index-[A-Za-z0-9]*\.css' /app/static/index.html"
```
Compare the two hashes. If they differ, that confirms a stale-`index.html`-vs-current-assets
mismatch left over from a prior deploy (expected with the manual build/copy/bake process).
If they match, the bug is something else — stop and report back before continuing.

## Step 2 — Is the PWA service worker configured to force updates?
```bash
grep -n "VitePWA(\|registerType\|skipWaiting\|clientsClaim" frontend/vite.config.*
```
Report the current `registerType` value (`'autoUpdate'` vs `'prompt'` vs unset) and whether
`skipWaiting`/`clientsClaim` are set under `workbox`. This tells us whether already-open
tabs are expected to self-heal on next reload, or can get stuck indefinitely on an old
app shell after a deploy.

## Step 3 — Why is a missing static file returning JSON instead of a normal 404?
```bash
grep -n "StaticFiles\|@app.get(\"/{full_path" backend/main.py backend/app.py 2>/dev/null
grep -rn "StaticFiles(" backend/
```
Confirm: (a) where the `/assets` StaticFiles mount is registered relative to any SPA
catch-all route, and (b) whether there's a global exception handler that serializes
JSON for *all* unmatched paths, including ones under `/assets/*` that should just 404
as a static file. Report the route registration order as found — don't reorder anything yet.

## Step 4 — Is the 401 related or a red herring?
Reproduce in a clean incognito window (no cookies) vs. reload the *same already-open* tab
that showed the original errors.
- 401 in incognito with no session → expected/benign, unrelated to the CSS issue.
- 401 in an already-logged-in tab that was previously working → note it, and check JWT
  expiry duration and cookie `Domain`/`Path` settings for any recent change, but do not
  modify auth config in this pass.

## STOP conditions
- Do not change `registerType` or workbox cache strategy in `vite.config` based on this
  pass alone — report Step 2's findings first, changing PWA caching blind can trade one
  stale-cache bug for a different one.
- Do not reorder FastAPI routes or touch the exception handler without reading the full
  route table in context — report Step 3's findings first.

## Required output
For each step: the exact command run and its raw output (not a paraphrase), plus a
one-line verdict (matches / doesn't match / needs follow-up).
