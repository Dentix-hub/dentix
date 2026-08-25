# DENTIX Safe Demo & Onboarding Flow

## 1. Safety Guardrails
- Demo mode operates on synthetic clinic fixtures (`MockTenant`, `DemoPatient`, `DemoProcedure`).
- Zero real patient clinical data or production financial records are used.
- Demo accounts are strictly isolated within `tenant_id = 9999` with isolated RLS constraints.

---

## 2. Onboarding Workflow
1. Clinic owner registers at `POST /api/v1/auth/register-clinic`.
2. Initial clinic setup wizard guides setting default currency (`EGP`), working hours, and doctor accounts.
3. Guided interactive tour walks through:
   - Patient registration and search normalization
   - Interactive dental chart and treatment recording
   - Automated inventory stock consumption tracking
   - Daily financial cash register closeout
