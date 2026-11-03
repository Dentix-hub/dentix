# DENTIX SEO Report D: Search Visibility & Indexing Baseline Report

**Document Date:** November 3, 2026  
**Project:** Dentix — Dental Clinic Management Software  
**Repository:** `https://github.com/Dentix-hub/dentix`  
**Base Branch:** `staging`  
**Production Domain:** `https://www.dentixs.app`  

---

## 1. Executive Summary

This report establishes the baseline search visibility and indexing configuration for Dentix across Google Search, Bing Webmaster Tools, and generative AI search crawlers (ChatGPT Search, Microsoft Copilot, Google Gemini).

Prior to this implementation:
- The root URL `/` served a client-rendered React application shell containing duplicate generic titles.
- Public legal policies (`/privacy`, `/terms`) were rendered inside an empty client-side DOM.
- Marketing pages (`/ar`, `/en`) lacked reciprocal hreflang links, high-intent trust pages, and structured topic clusters.
- The sitemap was unmanaged and did not represent the public surface of the application.

With the delivery of PR-A and PR-B, 18 high-quality static URLs are fully prepared, verified, and ready for immediate search crawler indexing.

---

## 2. Search Console & Bing Webmaster Baseline Status

| Engine / Platform | Integration Method | Baseline Diagnostic Status | Actions Needed |
| :--- | :--- | :--- | :--- |
| **Google Search Console** | Domain Property (`dentixs.app`) | Pending Owner DNS TXT verification | Add DNS record at registrar, submit `sitemap.xml` |
| **Bing Webmaster Tools** | GSC Domain Import | Pending GSC verification | One-click import after GSC verification |
| **OpenAI (ChatGPT Search)** | User-Agent `OAI-SearchBot` / `GPTBot` | Allowed by `robots.txt` | Automatically crawled via sitemap |
| **Microsoft Copilot** | Bing Index integration | Dependent on Bing Indexing | Will index once Bing discovers URLs |
| **Google Gemini** | Google Search Index integration | Dependent on Google Indexing | Will index once Google crawls `/ar` and `/en` |

---

## 3. Inventory & Status of All 18 Target Public URLs

All 18 URLs are confirmed to be:
- 100% pre-rendered static HTML with zero JavaScript execution requirement.
- Clean URLs without file extensions (`.html`) or trailing slash duplicates (enforced by 308 redirects).
- Complete with bidirectional `hreflang="ar"`, `hreflang="en"`, and `hreflang="x-default"`.
- Formatted with Schema.org JSON-LD structured data and responsive CSS under budget.

| Index | Target Canonical URL | Language | Content Type | Schema.org Type | Indexability Status |
| :---: | :--- | :--- | :--- | :--- | :--- |
| 1 | `https://www.dentixs.app/ar` | Arabic | Primary Marketing Home | `WebSite` / `SoftwareApplication` | **Ready for Indexing** |
| 2 | `https://www.dentixs.app/en` | English | English Marketing Home | `WebSite` / `SoftwareApplication` | **Ready for Indexing** |
| 3 | `https://www.dentixs.app/ar/privacy` | Arabic | Privacy Policy | `WebPage`, `BreadcrumbList` | **Ready for Indexing** |
| 4 | `https://www.dentixs.app/en/privacy` | English | Privacy Policy | `WebPage`, `BreadcrumbList` | **Ready for Indexing** |
| 5 | `https://www.dentixs.app/ar/terms` | Arabic | Terms of Service | `WebPage`, `BreadcrumbList` | **Ready for Indexing** |
| 6 | `https://www.dentixs.app/en/terms` | English | Terms of Service | `WebPage`, `BreadcrumbList` | **Ready for Indexing** |
| 7 | `https://www.dentixs.app/ar/about` | Arabic | About Dentix | `AboutPage` | **Ready for Indexing** |
| 8 | `https://www.dentixs.app/en/about` | English | About Dentix | `AboutPage` | **Ready for Indexing** |
| 9 | `https://www.dentixs.app/ar/contact` | Arabic | Contact & Official Support | `ContactPage`, `ContactPoint` | **Ready for Indexing** |
| 10 | `https://www.dentixs.app/en/contact` | English | Contact & Official Support | `ContactPage`, `ContactPoint` | **Ready for Indexing** |
| 11 | `https://www.dentixs.app/ar/plans` | Arabic | Plans & Approved Pricing | `WebPage`, `Offer` | **Ready for Indexing** |
| 12 | `https://www.dentixs.app/en/plans` | English | Plans & Approved Pricing | `WebPage`, `Offer` | **Ready for Indexing** |
| 13 | `https://www.dentixs.app/ar/dental-clinic-management-software` | Arabic | Clinic Management Software Guide | `Article`, `WebPage` | **Ready for Indexing** |
| 14 | `https://www.dentixs.app/en/dental-clinic-management-software` | English | Clinic Management Software Guide | `Article`, `WebPage` | **Ready for Indexing** |
| 15 | `https://www.dentixs.app/ar/dental-patient-records` | Arabic | Dental Patient Records Guide | `Article`, `WebPage` | **Ready for Indexing** |
| 16 | `https://www.dentixs.app/en/dental-patient-records` | English | Dental Patient Records Guide | `Article`, `WebPage` | **Ready for Indexing** |
| 17 | `https://www.dentixs.app/ar/appointments-finance` | Arabic | Appointments & Finance Guide | `Article`, `WebPage` | **Ready for Indexing** |
| 18 | `https://www.dentixs.app/en/appointments-finance` | English | Appointments & Finance Guide | `Article`, `WebPage` | **Ready for Indexing** |

---

## 4. Audit of Indexing Blockers & Resolutions

| Potential Blocker | Historical State | Resolved State in PR-A / PR-B |
| :--- | :--- | :--- |
| **`noindex` on Marketing Pages** | Risk of global `<meta name="robots">` inheritance | Marketing pages have explicit indexable headers; raw `noindex` isolated strictly to SPA shell `index.html`. |
| **Duplicate Content on `/` vs `/ar`** | `/` served generic app HTML competing with `/ar` | `/` is marked `noindex, follow` and exposes noscript discovery links; `/ar` is the primary canonical marketing home. |
| **Client-Rendered Legal Routes** | `/privacy` and `/terms` rendered blank DOM before JS | Pre-rendered static HTML at `/ar/privacy`, `/en/privacy`, `/ar/terms`, `/en/terms` with 308 redirects from legacy paths. |
| **Broken Sitemap Declarations** | Sitemap had missing or unverified URLs | Sitemap updated with all 18 canonical URLs, validated by automated XML/AST tests. |
| **Missing Reciprocal Alternate Tags** | No `hreflang` validation | All 18 URLs pass strict reciprocal hreflang validation across Arabic, English, and x-default. |

---

## 5. Recommended Crawl Request Priority (Post-Verification)

Once the domain property is verified in Google Search Console:

1. **Priority 1 (Primary Hubs):**
   - Inspect and request indexing for `https://www.dentixs.app/ar`
   - Inspect and request indexing for `https://www.dentixs.app/en`
2. **Priority 2 (Commercial & Trust Signals):**
   - Inspect and request indexing for `https://www.dentixs.app/ar/plans`
   - Inspect and request indexing for `https://www.dentixs.app/ar/contact`
   - Inspect and request indexing for `https://www.dentixs.app/ar/about`
3. **Priority 3 (Search Topic Guides):**
   - Inspect and request indexing for `https://www.dentixs.app/ar/dental-clinic-management-software`
   - Inspect and request indexing for `https://www.dentixs.app/ar/dental-patient-records`
   - Inspect and request indexing for `https://www.dentixs.app/ar/appointments-finance`
4. **Priority 4 (English Counterparts & Policies):**
   - Allow standard crawler discovery via `sitemap.xml` for remaining English content and legal pages.
