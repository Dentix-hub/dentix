# Dentix — Search visibility

Date: 2026-11-03. Search-engine indexing status: **UNKNOWN**.

No Google Search Console or Bing Webmaster evidence was supplied. No URLs were submitted and no indexing requests were made by this executor. See [SEO_INDEXING_BASELINE.md](SEO_INDEXING_BASELINE.md) for the evidence fields and unknown URL statuses.

## Technical preparation

The [active public inventory](../../frontend/scripts/routeInventory.mjs) identifies bilingual marketing, legal, about, contact, subscription-inquiry and workflow-guide pages. The app shell is intentionally noindexed; authentication continues to protect application data. Indexability is validated from page metadata, reciprocal alternates, canonical identity, local artifacts and deployment HTTP contracts.

The unchanged [robots policy](../../frontend/public/robots.txt) allows public crawling and excludes /api/. Permission to crawl does not prove a crawl occurred, a URL was indexed or an AI system recommends the product. A sitemap is a discovery aid, not automatic indexing. The pre-change /ar and /en pages already had reciprocal hreflang and structured data; this work extends that infrastructure.

## Remaining verification

- Run the [HTTP verifier](../../frontend/scripts/verify-vercel-preview-routes.mjs) against the exact authorized Vercel deployment. Vite artifact tests do not execute Vercel redirects or rewrites.
- After approved production deployment, inspect the canonical www domain, app shell, all public pages, legal aliases, assets, sitemap, robots, HTTP indexing directives, authentication and PWA behavior.
- Compare Google-selected and user-declared canonicals using Search Console evidence. These values, crawl errors, last crawl and indexing decisions are currently unknown.
- The noindexed application root limits the domain-homepage WebSite site-name opportunity. Structured data on /ar does not bypass that constraint. Moving marketing to / is outside this scope.

## Owner actions

Verify dentixs.app as a Search Console Domain Property through DNS, submit https://www.dentixs.app/sitemap.xml after it reflects deployed pages, inspect /ar, /en and /, and request eligible indexing where appropriate. Import the verified site into Bing Webmaster Tools and record its inspection results. Do not repeatedly request indexing without addressing an identified issue. Search rankings and AI recommendations remain external outcomes.
