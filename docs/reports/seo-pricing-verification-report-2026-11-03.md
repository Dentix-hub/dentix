# DENTIX SEO Report B: Pricing & Plan Limits Verification Report

**Document Date:** November 3, 2026  
**Project:** Dentix — Dental Clinic Management Software  
**Repository:** `https://github.com/Dentix-hub/dentix`  
**Base Branch:** `staging`  

---

## 1. Executive Summary

This report provides a strict audit and verification of commercial pricing claims, database subscription seeds, and proposed operational plan limits (user seats and daily AI request quotas) prior to public release.

In accordance with Section 2.3 and 2.4 of the Consolidated SEO Plan:
- **Commercially Approved Prices** (Essential 200 EGP, Professional 400 EGP, Business 1000 EGP) are published on the public Plans pages (`/ar/plans`, `/en/plans`) with explicit operational guidance that plan activations and renewals are managed directly via official technical support and WhatsApp (`+201010285288`).
- **Proposed Operational Limits** (2, 5, 15 users; 2, 10, 30 AI requests/day) and automated in-app checkout are **OMITTED** because the backend database schema and subscription service do not currently enforce them.

---

## 2. Comparison: Database Seed Values vs. Approved Commercial Prices

A direct audit of the codebase (`backend/models/tenant.py`, `backend/core/seeding.py`, and `backend/routers/auth/register.py`) reveals a substantial discrepancy between existing seeded development records and owner-approved commercial figures:

| Plan Identifier | Seeded Database Plan Name | Seeded Database Price | Owner-Approved Commercial Name | Owner-Approved Monthly Price | Commercial Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `trial` | Free Trial | 0.00 | — | — | Legacy seed |
| `basic` | Basic Clinic | 29.99 (USD/unspecified) | Essential — الأساسية | **200 EGP** | Approved by Owner |
| `pro` | Pro Clinic | 79.99 (USD/unspecified) | Professional — الاحترافية | **400 EGP** | Approved by Owner |
| `enterprise` | Enterprise Clinic | 199.99 (USD/unspecified) | Business — الأعمال | **1000 EGP** | Approved by Owner |

### Audit Findings:
1. The database seeds originate from early development templates with USD-style fractional pricing (29.99, 79.99, 199.99).
2. The owner-approved pricing structure is denominated in Egyptian Pounds (EGP) as whole integers (200, 400, 1000 EGP/month).
3. The database migration scripts have not yet been executed to update the `plans` table rows with the new names, EGP currencies, and integer prices.

---

## 3. Operational Limits Audit: User Seats & Daily AI Requests

Section 2.4 of the plan proposed the following limit tiers:
- **Essential:** 2 users, 2 AI requests/day.
- **Professional:** 5 users, 10 AI requests/day.
- **Business:** 15 users, 30 AI requests/day.

### Backend Code Verification:
1. **User Seat Enforcement:**
   - In `backend/routers/auth/` and `backend/services/tenant_service.py`, user creation checks tenant membership and role authorization, but does not query the active `TenantSubscription.plan` to block new user invites when a numerical user cap is reached.
2. **AI Daily Request Quota Enforcement:**
   - In `backend/routers/ai.py` and `backend/services/ai_service.py`, AI interactions exist for chat assistance and clinical summaries. However, usage counters are not scoped per clinic with daily resetting quota gates tied to `Plan` parameters.

### Product Integrity Decision:
Because advertising un-enforced seat and AI limits constitutes an unsupported commercial claim, **all proposed numerical user seat and daily AI quotas have been completely omitted from the public marketing pages**. The Plans page instead highlights verified product capabilities:
- Comprehensive patient electronic health records.
- Interactive multi-surface dental chart (odontogram).
- Appointment calendar, chairside scheduling, and SMS/WhatsApp reminders.
- Practice finance, revenue tracking, and expense management.
- Multi-user role-based clinic collaboration (Dentists, Assistants, Receptionists).

---

## 4. In-App Subscription Architecture & Support Activation Alignment

Inspection of the authenticated application's subscription settings interface (`frontend/src/features/settings/SettingsTabs/SubscriptionSettings.jsx`) reveals the established in-app subscription policy:

> *"يتم تجديد الاشتراكات حصرياً عبر التواصل المباشر مع إدارة المنظومة والدعم الفني."*  
> *(Subscriptions are renewed exclusively through direct communication with system administration and technical support.)*

### Public Display Alignment:
To maintain 100% truth-in-advertising without modifying backend billing code:
1. The public Plans pages display the approved prices (200, 400, 1000 EGP).
2. The call-to-action buttons link directly to official WhatsApp support (`https://wa.me/201010285288`) with pre-filled Arabic/English activation inquiry messages.
3. A clear policy notice is published beneath the pricing table stating:
   - *"يتم تفعيل وتجديد باقات Dentix عبر التواصل المباشر مع فريق الدعم الفني المعتمد لضمان إعداد بيانات العيادة وصلاحيات الفريق بدقة."*
4. This ensures visitors have complete pricing transparency while aligning with actual operational workflows.
