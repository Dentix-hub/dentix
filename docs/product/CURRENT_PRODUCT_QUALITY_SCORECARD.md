# Dentix Current Product Quality Scorecard

**Plan:** DENTIX PLAN 03 — EXISTING PRODUCT FORENSIC IMPROVEMENT  
**Baseline:** `staging` after Plan 02 merge on 2026-08-18  
**Scoring:** 0–10, where 10 means the current evidence supports a mature accepted baseline.  
**Purpose:** rapid prioritization only; module audit evidence may revise a score.

## Evidence model

Scores use current executable ownership/routes/tests from `MODULE_REGISTRY.md` and `CURRENT_PRODUCT_CAPABILITIES.md`, plus Plan 02 shared-UI forensic findings and regression evidence. They are intentionally conservative where a capability is only `PARTIAL` or where direct performance/accessibility measurement is not yet available.

The scorecard does **not** treat the current Vercel staging build-rate-limit status as a module defect.

## Scores

| Module | Correctness | UX | Visual maturity | Consistency | Performance | Accessibility | Mobile | RTL | Security / RBAC | Test confidence | Daily importance | Blast radius | Known pain / regression signal |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---|---|
| Patients | 9 | 8 | 7 | 7 | 8 | 8 | 8 | 8 | 9 | 9 | Very high | Very high | Recent Patient Workspace V2 is strong, but patient details remains a broad multi-workflow surface and was listed among local overlay migration candidates. |
| Appointments | 8 | 6 | 6 | 5 | 7 | 6 | 6 | 7 | 8 | 8 | Very high | Very high | `Appointments.jsx` remains large; FullCalendar has a separate style system; date/time overlays require strict timezone/mobile/keyboard regression. |
| Clinical / Dental | 7 | 5 | 5 | 4 | 6 | 5 | 5 | 6 | 8 | 7 | Very high | Very high | `TreatmentModal` is a large, business-heavy workflow with nested overlays; clinical capability is distributed and only PARTIAL in inventory. |
| Finance / Billing / Expenses | 9 | 8 | 8 | 7 | 8 | 7 | 7 | 8 | 9 | 9 | High | Very high | Finance V2 and financial truth tests provide a strong baseline; a small number of feature-local drawers/modals remain migration candidates. |
| Dashboard | 8 | 6 | 5 | 5 | 7 | 6 | 6 | 7 | 8 | 7 | High | High | Large page and decorative/card-heavy legacy patterns may compete with operational hierarchy; metric semantics must remain backend-owned. |
| Analytics | 7 | 6 | 5 | 5 | 6 | 6 | 6 | 7 | 8 | 6 | Medium | Medium | Capability and metric inventory are PARTIAL; performance/readability need direct evidence. |
| Labs | 7 | 5 | 4 | 4 | 6 | 5 | 5 | 6 | 8 | 7 | Medium | High | Several lab-specific modal surfaces remain outside the canonical overlay boundary; lifecycle inventory is PARTIAL. |
| Inventory | 8 | 5 | 4 | 4 | 6 | 5 | 5 | 6 | 8 | 7 | High | Very high | Multiple inventory modals remain local overlay implementations; stock/cost/usage correctness gives the module a large data blast radius. |
| Users / RBAC | 8 | 5 | 4 | 4 | 7 | 5 | 5 | 6 | 9 | 8 | Medium | Very high | `UsersManager` remains an overlay migration candidate; permission UX is safety-sensitive even when server checks are authoritative. |
| Settings | 7 | 5 | 5 | 5 | 7 | 6 | 6 | 7 | 8 | 7 | Medium | High | Several capability surfaces are PARTIAL; validation/save/destructive-setting consistency needs module proof. |
| AI | 8 | 7 | 7 | 7 | 7 | 6 | 6 | 7 | 9 | 8 | Medium | High | Governance/security stack is strong; existing action inventory remains PARTIAL and all UI must stay role-aware. |
| Super Admin | 8 | 5 | 4 | 4 | 7 | 5 | 5 | 6 | 9 | 8 | Low daily / high admin importance | Very high | High-density admin surfaces plus local command-palette/tenant overlays create UX/accessibility debt; platform blast radius is very high. |
| Auth / Public / PWA | 9 | 8 | 8 | 8 | 8 | 8 | 8 | 8 | 9 | 9 | Very high entry-point importance | Very high | Current auth/PWA evidence is comparatively mature; avoid disturbing session/CSRF/service-worker contracts without a proven defect. |

## Rapid findings

### P0

None established by current evidence.

### P1

None established by the rapid pass. A module audit may promote a finding after reproduction.

### P2 candidates

1. Clinical/Dental: nested/local overlay architecture around a large treatment workflow; keyboard/mobile regression risk.
2. Appointments: date/time + calendar interaction consistency, responsive scheduling, and overlay modernization.
3. Inventory: many feature-local overlays around stock/usage workflows; dense mobile and accessibility risk.
4. Users/RBAC: permission-sensitive UX and local modal implementation.
5. Labs: local modal stack and dense workflow consistency.
6. Dashboard/Analytics: hierarchy/readability and possible decorative competition with operational content.
7. Patients: patient-details consolidation/performance/accessibility despite a strong directory baseline.
8. Settings/Super Admin: high-density forms/tables and local overlay debt.

### P3 candidates

- Remaining legacy arbitrary radius/shadow/z-index usage where it does not create interaction correctness problems.
- Cosmetic alignment with semantic tokens after functional/accessibility issues are resolved.

## Prioritized execution order

The rapid pass intentionally changes the plan's default order because current scores are not similar: Patients and Finance recently received stronger foundations, while Clinical/Appointments/Inventory retain higher interaction and workflow risk.

1. **Clinical / Dental** — daily clinical importance + nested workflow/overlay risk + PARTIAL capability inventory.
2. **Appointments** — daily scheduling importance + date/time/calendar/mobile risk.
3. **Inventory** — correctness-sensitive stock/cost data + multiple legacy overlays.
4. **Patients** — very high daily importance, then close remaining patient-details gaps on top of strong recent V2 baseline.
5. **Users / RBAC** — platform safety sensitivity + permission UX.
6. **Labs** — workflow density + modal debt.
7. **Dashboard / Analytics** — operational hierarchy, chart/readability and performance evidence.
8. **Settings** — form grouping/save/validation/destructive-action consistency.
9. **Super Admin** — high-density platform administration with very high blast radius.
10. **Finance / Billing / Expenses** — strong recent V2 baseline; audit for residual consistency/regression debt rather than broad redesign.
11. **AI** — preserve existing policy/tool boundaries; improve only proven current UX defects.
12. **Auth / Public / PWA** — mature high-risk boundary; audit late to minimize needless session/PWA churn.

## Foundation status

Plan 02 foundation is usable:

- canonical dialog/drawer/bottom-sheet/popover/menu primitives exist;
- semantic tokens exist for surfaces, text, borders, radii, shadows, spacing, type, motion and z layers;
- overlay keyboard/focus/scroll behavior has regression coverage;
- reviewed patient visual baselines exist for AR light desktop, EN dark desktop and AR light mobile;
- design guardrails prevent newly-added raw overlay/z/radius/shadow debt.

The requested precondition file `DENTIX_UI_PRINCIPLES.md` is absent. This scorecard therefore uses executable tokens/shared UI and current Plan 02 contracts as the UI authority, with `frontend/DESIGN.md` only as non-conflicting supporting guidance.
