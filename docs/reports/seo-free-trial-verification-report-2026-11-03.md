# Dentix — Free trial verification

Date: 2026-11-03. Overall result: **NOT VERIFIED**. Trial marketing claims remain omitted.

The approved policy is a 14-day Professional trial without a payment card. No production clinic was created and no registration or billing behavior was changed.

## Executable evidence

The actual endpoint is `POST /api/v1/auth/register_clinic` in [register.py](../../backend/routers/auth/register.py). It uses async SQLAlchemy selects of SubscriptionPlan: it first looks for is_default, then falls back to the first returned plan. It sets the new Tenant.plan_id and creates the first admin account. It does not explicitly select Professional, set a trial start timestamp, or compute a 14-day subscription expiration.

[Tenant](../../backend/models/tenant.py) has subscription_end_date and a legacy plan default of trial. [SubscriptionService.check_subscription_status](../../backend/services/subscription_service.py) returns active if no end date is present and evaluates active/grace/expired states when dates are present. This code observation is not proof of end-to-end behavior for a newly registered clinic.

The earlier report's db.query(Plan), TenantSubscription construction and claimed line range were not executable evidence from this repository and have been removed.

## Required results

| Requirement | Result | Evidence / limitation |
| --- | --- | --- |
| Professional plan assigned | NOT VERIFIED | Assignment depends on database default; active plan identity was not supplied |
| Trial duration equals 14 days | NOT VERIFIED | Endpoint does not explicitly create that duration; seed paths disagree |
| Correct start and expiration | NOT VERIFIED | No explicit trial start or expiration is assigned by the inspected registration path |
| No payment card required | VERIFIED at endpoint input level only | Form fields are clinic_name, admin_username, admin_email, admin_password and contact_phone; no card input. No authorized runtime registration was executed |
| Correct post-expiration behavior | NOT VERIFIED | Status service exists, but the approved trial lifecycle was not exercised in an isolated staging environment |

## Separate product gap

The approved trial policy needs a separately scoped registration/subscription task, starting with runtime configuration evidence and isolated tests. Its design must establish plan identity, start/expiry, expiration behavior and clinical record access. This SEO change does not prescribe a schema migration or modify those mechanisms.
