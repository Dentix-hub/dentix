# DENTIX SEO Report C: Free Trial Verification Report

**Document Date:** November 3, 2026  
**Project:** Dentix — Dental Clinic Management Software  
**Repository:** `https://github.com/Dentix-hub/dentix`  
**Base Branch:** `staging`  

---

## 1. Executive Summary & Verification Result

| Inspection Target | Commercial Policy Proposal | Verification Result | Final Marketing Action |
| :--- | :--- | :--- | :--- |
| **Free Trial Policy** | 14-day duration, Professional plan, No credit card required | **NOT VERIFIED** | **OMITTED** from all public marketing copy, buttons, and metadata |

Under Section 2.5 of the Consolidated SEO Plan, advertising a free trial is strictly contingent upon proving that the runtime codebase automatically provisions a 14-day Professional trial upon user registration.

Following a thorough audit of the registration routers, tenant creation services, and subscription database models, **the free trial could NOT be confirmed**. 

As mandated by project integrity rules, all references to a "14-day free trial" have been omitted from public marketing pages and pricing tables, and the gap has been logged as a separate backend product requirement.

---

## 2. Code-Level Evidence

An inspection of `backend/routers/auth/register.py` demonstrates the exact execution path when a new clinic registers:

```python
# File: backend/routers/auth/register.py (Lines 112-140)

# Fetch the default plan:
default_plan = db.query(Plan).filter(Plan.is_active == True).order_by(Plan.id.asc()).first()
if not default_plan:
    # Fallback to creating a plan or raising an error
    default_plan = create_default_plan(db)

# Create subscription:
subscription = TenantSubscription(
    tenant_id=tenant.id,
    plan_id=default_plan.id,
    status="active",
    start_date=datetime.utcnow(),
    end_date=None,  # <-- GAP: end_date is None, no 14-day duration is calculated
    is_auto_renew=False
)
db.add(subscription)

# Assign tenant attributes:
tenant.subscription_status = "active"
tenant.plan = "trial"  # Legacy enum string in tenant model
db.commit()
```

### Specific Technical Gaps Identified:
1. **No Plan Selection for Professional:**  
   The code executes `.order_by(Plan.id.asc()).first()`, picking the first seeded plan in the database (which is `trial` or `basic` with id 1). It does NOT select the `pro` or `Professional` plan.
2. **No Duration or Expiration Date:**  
   `subscription.end_date` is assigned as `None`. There is no calculation of `start_date + timedelta(days=14)`.
3. **No Expiration Enforcement Middleware:**  
   There is no active middleware or periodic background worker that checks `datetime.utcnow() > subscription.end_date` and transitions `subscription_status` from `"active"` to `"expired"`.
4. **Subscription Status Remains Indefinitely Active:**  
   Because `end_date` is `None` and `status` is `"active"`, registered accounts effectively obtain an unrestricted active basic subscription rather than an automated 14-day Professional trial.

---

## 3. Marketing & Public Pages Audit

To prevent misleading dental practitioners and maintain absolute trust:
- **Hero CTA:** Changed from generic trial claims to direct clinic onboarding and registration (`انضم إلى Dentix` / `Get Started`).
- **Pricing Tables:** The plans display approved monthly pricing (Essential 200 EGP, Professional 400 EGP, Business 1000 EGP) without false claims of automatic 14-day Professional provisioning.
- **Support Consultation:** Prospective clinics are invited to contact the team via WhatsApp (`+201010285288`) for live demos, custom onboarding, and trial activations.

---

## 4. Product Gap Resolution Recommendations (For Future Backend Sprint)

To safely implement and advertise the owner's approved 14-day Professional trial policy in a future release:

1. **Database Migration:**
   - Ensure the `pro` plan exists and is consistently identifiable via an immutable slug (`slug = "professional"`).
2. **Registration Router Modification (`backend/routers/auth/register.py`):**
   ```python
   # Recommended implementation:
   trial_plan = db.query(Plan).filter(Plan.slug == "professional", Plan.is_active == True).first()
   trial_duration_days = 14
   now = datetime.utcnow()

   subscription = TenantSubscription(
       tenant_id=tenant.id,
       plan_id=trial_plan.id,
       status="trial",
       start_date=now,
       end_date=now + timedelta(days=trial_duration_days),
       is_auto_renew=False
   )
   tenant.subscription_status = "trial"
   ```
3. **Subscription Expiration Guard:**
   - In `backend/middleware/auth.py` or tenant context loaders, verify:
     ```python
     if tenant.subscription_status == "trial" and subscription.end_date < datetime.utcnow():
         tenant.subscription_status = "expired"
     ```
   - Provide a read-only lock or redirect to subscription renewal when trial expires.
4. **Owner Review & Validation:**
   - Test end-to-end trial registration on staging before reinstating public marketing trial claims.
