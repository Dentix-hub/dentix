# Dentix — SEO indexing baseline

Snapshot date: 2026-11-03. Evidence source: local repository inspection only; no Search Console or Bing access/results supplied.

## Confirmed indexed URLs

None confirmed by supplied evidence. This does not mean that no URLs are indexed.

## Confirmed excluded URLs

None confirmed by supplied evidence. The application root's intended noindex is a code/configuration observation, not a confirmed Google or Bing exclusion decision.

## Unknown URLs

The root /, /ar, /en and every additional URL in the [active public inventory](../../frontend/scripts/routeInventory.mjs) have UNKNOWN engine indexing status. No URLs were submitted by this executor.

| Engine / URL | Indexing | Discovery | Last crawl | Crawling allowed | Indexing allowed | User canonical | Engine canonical | Fetch | Reported errors |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Google /ar | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN |
| Google /en | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN |
| Google / | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN |
| Bing /ar | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN |
| Bing /en | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN |

## Technical blockers and limitations

The initial review reproduced mobile overflow and validation gaps. See the [technical correction report](seo-technical-implementation-report-2026-11-03.md) for corrected local verification results. Delivery on Vercel and production remains unverified until authorized deployment; do not infer live eligibility from a successful local build. The deployed root should be noindexed while public marketing remains indexable.

No engine-reported technical blocker or canonical discrepancy can be confirmed without console evidence. The domain-homepage site-name limitation remains because / serves the noindexed application shell.

## Ranking and discovery limitations

Crawl permission, sitemap inclusion and structured data do not guarantee discovery, indexing, ranking, traffic or recommendations by ChatGPT, Copilot, Gemini or another service. External profiles and directory listings require owner authorization and verification.

## Evidence to collect

The owner should verify the Domain Property with DNS, submit the deployed sitemap, inspect the URLs above and save console output. Replace UNKNOWN only with actual inspection evidence, including the inspection timestamp. Record additional public URLs using the same fields; do not invent crawl dates or modification timestamps.
