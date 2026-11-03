# Dentix — Technical SEO implementation and correction report

Date: 2026-11-03. The owner authorized GitHub push and pull requests after local correction. Protected-branch merge and deployment remain unauthorized; GitHub is the source of truth for delivery status.

The technical fixes were integrated locally from the existing PR-A feature branch into the existing PR-B feature branch (merge 9ae45e5); staging and main were not changed.

This replaces the initial implementation report. The six review findings are addressed in code/content below; final test results are recorded in the verification section. Runtime pricing, Vercel delivery, authenticated staging acceptance and search-engine indexing are separate outstanding evidence gates.

## Changes and reasons

| Files | Behavior / reason |
| --- | --- |
| frontend/index.html; frontend/src/pages/Login.jsx | Raw app-shell noindex and public discovery links; existing auth/PWA entry remains at / |
| frontend/scripts/generate-legal-pages.mjs; public/{ar,en}/{privacy,terms}/index.html | Generate static legal text from unchanged locale sources; remove generated trailing whitespace without editing legal wording |
| frontend/scripts/routeInventory.mjs | Single active inventory drives public page options, sitemap eligibility, required artifacts and HTTP page coverage |
| frontend/scripts/verify-marketing-artifacts.mjs | Parse case/order-independent noindex/none directives; reject SPA fallback, bad canonical, missing metadata/H1 and nonreciprocal/nonindexable alternate targets; check clean local links and retain XML, robots, assets and precache validation |
| frontend/scripts/verify-vercel-preview-routes.mjs | Validate every Arabic/English public route and aliases, X-Robots-Tag, application shells, missing paths, API liveness and PWA resources; positive status/content type alone cannot pass a guide route |
| frontend/scripts/generate-content-pages.mjs; generated trust/content HTML | Replace unverified price/tier tables with bilingual subscription inquiries; remove multi-branch, popularity, support-priority/response guarantees and unsupported chair-utilization reporting claims |
| frontend/public/{ar,en}/index.html | Navigation labels match subscription inquiries rather than implying a verified public price list |
| frontend/public/marketing/marketing.css | Allow footer link wrapping and flex shrink; fix mobile links extending outside the viewport |
| frontend/vercel.json | Add missing clean redirects for six guide index.html aliases; preserve API rewrite and app fallback |
| frontend/src/tests/seoIndexability.test.js; seoCommercialClaims.test.js | Regression coverage for forbidden commercial claims, metadata/header indexing restrictions, canonical/reciprocal targets, all public route identities and alias configuration |
| frontend/src/tests/marketingStatic.test.js | Correct a specification error: its old assertion demanded publication of unverified commercial offers. It now checks usable bilingual inquiry pages; dedicated negative tests enforce withholding amounts/tier promises. No genuine failure is hidden or skipped |
| frontend/e2e/marketing.spec.ts | Add all 16 legal/trust/content documents to every configured browser project, retaining existing homepage overflow/PWA assertions |
| docs/reports/seo-*.md; SEO_INDEXING_BASELINE.md; docs/product/CURRENT_STATE.md | Replace unsupported audit/completion claims with actual code observations, executed results and unknown runtime/console evidence |

## Routing, metadata, sitemap and schema

The [route inventory](../../frontend/scripts/routeInventory.mjs) is authoritative. The public surface has 18 Arabic/English canonical destinations, including home/legal/about/contact/subscription inquiries and the three guides. Application entry, login, registration and protected routes retain the noindexed SPA shell. Legacy /privacy and /terms use their existing Arabic fallback destination; translated canonical legal pages remain available. All public document/slash aliases are expected to redirect to clean canonicals.

Each public page has a self canonical, language/direction, title, description, H1 and reciprocal language links. The sitemap contains only active public destinations, with no invented lastmod. Robots still excludes /api/ while allowing public marketing and assets. Noindex is an indexing directive, not an authentication or privacy control.

JSON-LD is parsed as JSON and the actual generated types are Organization, WebSite, SoftwareApplication on homepages; WebPage with nested BreadcrumbList on legal pages; AboutPage and ContactPage on their respective pages; WebPage on subscription inquiries; Article on guides. Do not infer richer properties from the type name. There are **no Offer, rating, review-count or sameAs claims**. No fake publication dates or author/image properties were added to match the earlier report.

The noindexed root limits Google's domain-homepage WebSite site-name opportunity; /ar metadata does not bypass that requirement. Root migration is outside scope.

## Verification and evidence

The original review is retained outside the repository at /home/ubuntu/dentix-task-artifacts/seo-review-20261103/REVIEW.md. It recorded four real mobile failures, missing commercial verification and false-pass probes. New indexing regression tests first failed (11 failures / 1 pass) against PR-A before the fix; commercial regression tests first failed all three cases before the content correction.

PR-A correction verification: 52 targeted tests passed; frontend lint and production build passed, all exit 0. PR-B's early targeted run passed 59 tests (before the final additional routing assertion). The production build and artifact validator passed, with marketing CSS approximately 5.28 KiB gzip. Final gate outcomes and invocation limits are recorded below.

A first new browser attempt used clean URLs on Vite preview and was interrupted after diagnosing its SPA fallback: Vite does not execute vercel.json. Browser document checks now request built index.html artifacts, consistent with existing homepage tests. Clean paths remain covered by configuration regression tests and the independent HTTP verifier, which must be executed against an authorized Vercel deployment. This local test setup adjustment is not a claim that Vercel runtime verification passed.

The no-URL invocation of the HTTP verifier exits 1 with usage instructions. No deployment URL was supplied, so no remote route pass is claimed. Full backend and frontend gates are run only at the final combined boundary; no mandatory CI gate is disabled.

## Staging manual acceptance (under 15 minutes)

1. On the authorized Vercel deployment, run `node frontend/scripts/verify-vercel-preview-routes.mjs <deployment-url>`; preserve output and exit code.
2. Open /ar and /en plus each linked trust/guide/legal page. Inspect source for language, canonical, reciprocal alternates and absence of noindex on public pages.
3. Disable JavaScript and read all legal pages and representative guide/contact/subscription pages. At 390px and 320px, check all footer links remain within the viewport.
4. Follow legacy /privacy and /terms and slash/document aliases; verify clean destinations and absence of loops. Request unknown public paths and a missing marketing asset; expect 404.
5. Check both approved contact links and subscription inquiries. Confirm no active prices, numerical proposed limits, tier promises or trial offers are displayed.
6. Use an authorized staging test account to log in, reach its dashboard/protected routes, log out and inspect registration without creating an uncontrolled production clinic.
7. Check API liveness JSON, PWA manifest/service worker and existing update behavior. Do not change PWA origin/identity or authentication settings.
8. After separate production deployment approval, repeat live domain checks and collect Search Console/Bing evidence using the baseline template.

## Remaining limitations

Active plan records, currency/duration matching, tier entitlements and the approved trial lifecycle remain unverified; commercial claims are withheld. Search Console/Bing evidence is unknown, and no URL submissions or external account/profile actions were performed. Vercel runtime, authenticated staging smoke and live production acceptance cannot be claimed from local artifacts. No backend, database schema, billing, registration, clinical/financial logic, auth/RBAC/tenancy or governance/CI files were modified.

## Final frontend verification (executed)

Working directory for npm/Playwright commands: frontend.

| Command | Exit | Actual result |
| --- | ---: | --- |
| npm run build | 0 | Vite/PWA build, HTML generation and strict marketing artifact validation passed |
| node scripts/verify-marketing-artifacts.mjs dist | 0 | Public metadata/alternates, files, sitemap, robots, CSS budget and precache checks passed |
| npm run lint | 0 | Passed |
| npm run design:guardrails | 0 | Report-only inventory: 48 legacy findings; not a zero-debt claim |
| node scripts/check-design-system-guardrails.mjs --diff-base=origin/staging | 0 | No newly added guarded violations |
| npm test -- src/tests/marketingStatic.test.js src/tests/seoIndexability.test.js src/tests/seoCommercialClaims.test.js src/tests/Login.test.jsx | 0 | 60 passed, 4 files, no failures/skips |
| npx playwright test --config playwright.marketing.config.ts | 0 | 143 passed, 2 skipped, all five configured projects |
| npm test -- --reporter=verbose | 1 | 1162 passed, 3 failed, 177 files / 1165 cases. Two i18n scans exceeded the unchanged 5s timeout under combined load; one PatientDetails history-row query did not resolve |
| npm test -- src/i18n.resources.test.js | 0 | All 7 cases passed in isolation, including both timed-out scans |
| npm test -- src/pages/PatientDetails.workspace.test.jsx | 0 | All 12 cases passed in isolation, including the history refresh scenario |
| git diff --check origin/staging | 0 | No whitespace errors in the complete working diff |

The isolated reruns overlap with the broad suite; do not add their counts to 1165. Every case that failed in the combined run passed unchanged in the per-file execution style used by the current CI workflow. The combined command still exited 1 and is not reported as a clean pass. No assertion, skip, timeout or CI setting was relaxed. A prior unchanged i18n scan timeout under simultaneous build/browser load was already documented in [the November 2 report](care-session-record-submit-2026-11-02.md).

The two browser skips are existing cases in desktop-no-js: dynamic React login-language switching requires JavaScript, and service-worker lifecycle requires JavaScript. No new skips were introduced. The new 16-document browser coverage ran in every project, including no-JavaScript, 390px and 320px. All existing homepage overflow assertions and the enabled PWA lifecycle cases passed.

An earlier set of broad frontend/backend/browser attempts ended with SIGTERM (exit 143) before final summaries. They are retained as interrupted attempts, not passes. The final completed browser run and frontend results above supersede those incomplete runs. Full frontend scope is 177 files / 1165 cases, not the earlier executor-reported 47 files / 337 cases.

Raw logs are retained under /home/ubuntu/dentix-task-artifacts/seo-fixes-20261103; the before-fix review logs remain under seo-review-20261103. Deployment HTTP verification and production acceptance remain pending; no live verification result is inferred from these local commands.

## Final backend verification (executed)

Command from the repository root (existing local venv):

```bash
env -u DATABASE_URL -u TEST_DATABASE_URL -u SYSTEM_DATABASE_URL PYTHONPATH=. ENVIRONMENT=testing .venv/bin/pytest backend/tests/ --cov=backend --cov-report=xml:/tmp/dentix-seo-backend-final-coverage.xml --cov-report=term --cov-fail-under=52 --junitxml=/tmp/dentix-seo-backend-final.xml --tb=short --maxfail=0 -ra -q
```

Exit **0**: **1747 passed, 23 skipped, 0 failed**, 63 warnings, 579.58 seconds. Coverage **78.87%**, above the unchanged CI threshold used by this invocation. This is local backend verification with the existing test fixtures, not a live production or PostgreSQL-isolation certification. The pytest result includes a non-fatal Prefect temporary-server teardown logging message after the success summary; the process exit was 0.

All 23 existing skips are accounted for by the JUnit report:

| Count | Recorded reason |
| ---: | --- |
| 1 | DATABASE_URL is not PostgreSQL; skipping live PostgreSQL trigger behavior test (will execute in PostgreSQL-backed CI). |
| 10 | Production migration contract requires PostgreSQL |
| 1 | Refresh endpoint requires UserSession tracking (request.client.host unavailable in TestClient) |
| 11 | Requires a preflight-initialized PostgreSQL TEST_DATABASE_URL |

PostgreSQL-only checks still require the preflight-initialized test environment used by the existing CI jobs. The refresh-session skip is an existing TestClient limitation. No skip marker or assertion was changed. Full JUnit and coverage XML, command logs and the verified branch bundle are retained in the local evidence directory.

## Review finding closure

| Finding | Local correction | Remaining external evidence |
| --- | --- | --- |
| S1: unverified prices | Removed visible prices, tier tables and pricing metadata; inquiry pages remain useful | Active-plan snapshot and commercial reconciliation required before prices can be published |
| S2: unsupported claims | Removed tier entitlements, multi-branch, popularity, priority/fast support and chair-utilization claims | Any future commercial promise requires approval and executable evidence |
| S3: mobile overflow | Wrapped footer navigation; all 145 browser cases accounted for (143 pass / 2 existing no-JS skips) | Live deployment acceptance pending |
| S4: indexing false passes | Semantic robots, translated-target canonical/reciprocity and HTTP-header negative tests pass | Live HTTP headers pending |
| S5: incomplete route validation | Every active Arabic/English page and alias has configuration and semantic HTTP contracts; SPA fallbacks are rejected | Actual Vercel HTTP run pending deployment authorization/URL |
| G1: inaccurate reports | Replaced invented code/audit assertions and test counts; baseline statuses remain UNKNOWN | Search Console/Bing evidence and runtime product verification pending |

All six local review corrections are implemented. The original end-to-end SEO rollout remains **PARTIAL** until active commercial verification, authorized deployment/runtime acceptance and console evidence are supplied. No remote delivery was performed.

## GitHub delivery reconciliation — 2026-11-03

Before upload, origin/staging advanced from 85e0909 to e662e26 through the independently approved landing-motion PR #348. Both existing SEO branches were reconciled with that staging revision, preserving the bilingual CSS tour, screenshot visibility checks, reduced-motion behavior and both SEO scopes. There was no force push or protected-branch mutation.

Fresh verification after reconciliation:

- PR-A snapshot: 52 targeted tests in 3 files and production build/artifact validation passed, exit 0. The isolated git-archive checkout emitted a non-fatal git-metadata diagnostic because it has no .git directory.
- Combined PR-B candidate: 60 targeted tests in 4 files, production build/artifact validation, lint and diff guardrails passed, exit 0. Marketing CSS is now 6.45 KiB gzip with the inherited motion styles.
- `npx playwright test --config playwright.marketing.config.ts`: 163 passed, 2 existing no-JavaScript skips, exit 0. The extra 20 cases come from the inherited landingMotion suite; original SEO page, responsive and PWA checks remain active.
- The intervening staging change contains no backend edits. Prior full backend results and the qualified full-frontend/isolation results above are retained as dated evidence; no redundant full backend run was performed just for upload.

PR-A targets staging. PR-B also targets staging and remains a draft depending on PR-A; until PR-A is integrated its staging comparison necessarily includes the foundation changes. Its content can be reviewed separately by comparing the two feature branches. Commercial records and deployment/search-console evidence remain outstanding. No active prices or trial promises are introduced by remote delivery.

Delivery verification logs are retained under /home/ubuntu/dentix-task-artifacts/seo-fixes-20261103 with the delivery- prefix.
