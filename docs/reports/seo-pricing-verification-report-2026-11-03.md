# Dentix — Pricing verification

Date: 2026-11-03. Runtime pricing verification: **BLOCKED — no authorized active-plan snapshot supplied or queried.**

This report replaces the earlier inaccurate audit. Seed data, code behavior and active database records are different evidence sources. No billing records, schema, registration behavior or quota enforcement were changed.

## Active commercial configuration

| Required item | Result |
| --- | --- |
| Active plan identities and names | UNKNOWN |
| Actual prices and currency | UNKNOWN; checkout code uses EGP, but this is not a runtime plan audit |
| Billing duration | UNKNOWN |
| User and patient limits | UNKNOWN |
| Daily AI limits and enabled features | UNKNOWN |
| Per-plan feature entitlement enforcement | Not verified end to end |

The owner-approved monthly proposal is Essential / الأساسية 200 EGP, Professional / الاحترافية 400 EGP, Business / الأعمال 1000 EGP. These amounts are approved commercially, not verified as active configuration. They are **omitted from public HTML and metadata**, along with numerical limits, trial promises, Offer data and tier-specific feature claims. The bilingual `/plans` pages provide subscription inquiries with the approved email and WhatsApp channels.

## Repository evidence — not live records

Sources: [SubscriptionPlan](../../backend/models/tenant.py), [seeding paths](../../backend/core/seeding.py), [standalone seed](../../backend/scripts/seeds/seed.py), [subscription service](../../backend/services/subscription_service.py), [schemas](../../backend/schemas/tenant.py), [admin APIs](../../backend/routers/admin_subscriptions.py), [subscription UI](../../frontend/src/features/settings/SettingsTabs/SubscriptionSettings.jsx).

| Seed name | Main seed price | Main duration / users / patients | Alternate seed price | Alternate duration / users / patients |
| --- | ---: | --- | ---: | --- |
| trial | 0 | 14 days / 1 / 50 | 0 | 7 days / 1 / 10 |
| basic | 29.99 | 30 days / 2 / 500 | 500 | 30 days / 1 / 100 |
| pro | 79.99 | 30 days / 5 / 2000 | 1000 | 30 days / 5 / null |
| enterprise | 199.99 | 30 days / null / null | 2500 | 30 days / null / null |

These mutually different seed paths cannot establish what an existing deployment contains. SubscriptionPlan has no currency column; checkout construction in SubscriptionService uses EGP. Do not infer USD from fractional numbers. A duration of 30 days in a seed does not establish calendar-month billing for active records.

The main seed's feature strings include BILLING/REPORTS_BASIC for basic; REPORTS_ADVANCED/LAB_INTEGRATION/MULTI_USER for pro; and AI_ASSISTANT additionally for enterprise. These strings alone do not prove usable or enforced entitlements. AI defaults in the model are is_ai_enabled=false and ai_daily_limit=0; actual values were not read.

## Enforcement findings

- [users.py](../../backend/routers/users.py) checks subscription_plan.max_users against a tenant-scoped user count on the inspected creation path. The earlier claim that user-limit enforcement is absent was incorrect. Race behavior and all creation paths were not audited here.
- [AIService._check_subscription_quota](../../backend/services/ai_service.py) checks is_ai_enabled and ai_daily_limit, and counts AIUsageLog rows filtered by the current tenant and day boundary. The earlier claim that clinic-scoped daily accounting is absent was incorrect. Complete quota correctness, concurrency and proposed values were not verified.
- A patient-limit field exists. A complete patient-limit enforcement audit has not been performed; this report does not assert that all paths enforce it or that no enforcement exists.

## Publication prerequisite

Obtain an authorized read-only export of active subscription_plans covering names, Arabic names, prices, duration_days, max_users, max_patients, features, is_ai_enabled, ai_daily_limit and ai_features, plus the effective billing currency. Compare against owner approval and verify entitlements before adding a single shared verified source for public pricing. Report mismatches for a separate owner-approved subscription task; do not modify records automatically.
