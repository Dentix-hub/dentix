# DENTIX SEO Report E: Owner Action & External Visibility Report

**Document Date:** November 3, 2026  
**Project:** Dentix — Dental Clinic Management Software  
**Repository:** `https://github.com/Dentix-hub/dentix`  
**Base Branch:** `staging`  
**Production Domain:** `https://www.dentixs.app`  

---

## 1. Executive Summary

This report outlines the specific external actions, ownership verifications, and monitoring routines required by the Product Owner to complete the search visibility lifecycle for Dentix.

Code implementation and static site architecture across PR-A and PR-B are 100% complete. The remaining steps involve DNS registrar records, webmaster console registrations, third-party brand directory listings, and ongoing monitoring.

---

## 2. Google Search Console & Bing Webmaster Setup Checklist

### Step 1: Google Search Console (P0 — Immediate Action)
1. Navigate to: `https://search.google.com/search-console/`
2. Select **Add Property** -> Choose **Domain** property (enter: `dentixs.app`).
3. Google will provide a unique DNS TXT verification record (e.g., `google-site-verification=...`).
4. Log into your domain registrar / DNS provider for `dentixs.app` (e.g. Cloudflare, Namecheap, GoDaddy).
5. Add a TXT record at the apex domain (`@` or `dentixs.app`) with the verification string.
6. Return to Google Search Console and click **Verify**.
7. Once verified, navigate to **Sitemaps** in the left menu:
   - Submit: `https://www.dentixs.app/sitemap.xml`
   - Confirm status reports "Success" and reads all 18 URLs.
8. Use the **URL Inspection** tool on `https://www.dentixs.app/ar` and click **Request Indexing**.

### Step 2: Bing Webmaster Tools (P0 — Immediately following GSC)
1. Navigate to: `https://www.bing.com/webmasters/`
2. Sign in with your administrative Microsoft or Google account.
3. Select **Import your sites from GSC** (this automatically verifies ownership without editing DNS a second time).
4. Verify that `dentixs.app` and `www.dentixs.app` are correctly imported.
5. Confirm that `https://www.dentixs.app/sitemap.xml` is recognized.

---

## 3. External Brand Profiles Creation Checklist

To build strong entity authority for Dentix in Google Knowledge Graph and AI search engines (ChatGPT, Copilot, Gemini), create and link authoritative brand profiles using the approved details:

- **Official Product Name:** Dentix
- **Arabic Descriptor:** Dentix — برنامج إدارة عيادات الأسنان
- **English Descriptor:** Dentix — Dental Clinic Management Software
- **Official Support Email:** `smartsentalclinicapp@gmail.com`
- **Official WhatsApp:** `+201010285288` (`https://wa.me/201010285288`)
- **Website URL:** `https://www.dentixs.app/ar` (or `https://www.dentixs.app`)

| Platform | Recommended Handle / URL Slug | Setup Checklist |
| :--- | :--- | :--- |
| **LinkedIn Company Page** | `linkedin.com/company/dentix-app` | Set description to official descriptors; link to `https://www.dentixs.app/ar`; upload official logo. |
| **Facebook Business Page** | `facebook.com/dentixs.app` | Add WhatsApp CTA button linked to `+201010285288`; specify software service category. |
| **YouTube Channel** | `@DentixApp` | Reserve handle for future demo walkthroughs and video guides. |
| **X (Twitter) Profile** | `@DentixApp` | Link back to `https://www.dentixs.app`. |
| **GitHub Organization** | `github.com/Dentix-hub` | Ensure public repo profile links to official website. |

---

## 4. Third-Party Dental & Software Directory Submission Checklist

Submitting Dentix to authoritative software discovery platforms provides high-trust external citations and referral traffic:

1. **Capterra / Gartner Digital Markets:**
   - Submit under *Dental Practice Management Software*.
   - Use official pricing: Essential 200 EGP, Professional 400 EGP, Business 1000 EGP.
2. **Software Advice & GetApp:**
   - Synchronized automatically via Gartner Digital Markets submission.
3. **Product Hunt:**
   - Prepare a launch post highlighting bilingual dental charting and clinical workflow efficiency.
4. **Regional Egyptian & MENA Dental Directories:**
   - Register Dentix in Egyptian healthcare tech and medical equipment portals.

---

## 5. Ongoing Monitoring & Health Schedule

| Frequency | Task | Objective |
| :--- | :--- | :--- |
| **Weekly (First Month)** | GSC Coverage & Page Indexing Report | Monitor the status of the 18 submitted URLs from "Discovered - currently not indexed" to "Indexed". |
| **Weekly** | GSC URL Inspection & Crawl Errors | Check for unexpected 4xx/5xx errors or soft 404s. |
| **Bi-weekly** | Bing Webmaster Crawl Issues | Verify Microsoft Copilot indexing pipeline health. |
| **Monthly** | Search Query Impressions | Review queries in GSC (e.g. "برنامج إدارة عيادات الأسنان", "dental clinic software Egypt") to identify emerging search terms. |

---

## 6. Product Gap Resolution Recommendations (Backend Roadmap)

The SEO audit identified three technical gaps that require backend sprint planning:

1. **14-Day Professional Trial Provisioning:**
   - Update `backend/routers/auth/register.py` to explicitly attach the `pro` plan with an exact 14-day expiration timestamp (`end_date = start_date + timedelta(days=14)`).
   - Implement middleware to transition expired trials to restricted read-only mode.
2. **Database Plan Seed Synchronization:**
   - Write an Alembic database migration to update `plans` table rows to match the approved names (Essential, Professional, Business) and monthly EGP amounts (200, 400, 1000 EGP).
3. **Tenant-Scoped AI Quota Tracking:**
   - Add a daily quota counter on `TenantSubscription` or Redis cache to enforce daily AI request limits per plan.
