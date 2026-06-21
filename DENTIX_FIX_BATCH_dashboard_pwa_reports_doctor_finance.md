# Dentix — Fix & Enhancement Batch
**Scope:** 4 independent issues across dashboard, PWA shell, invoice reporting, and cross-doctor patient finance visibility.
**Target agent:** Gemini / Hermes (direct local codebase access, repo root `/c/Users/es/DENTIX`)
**Mode:** Self-contained. Assume zero prior context beyond this document. Do not ask the user for clarification — if something is ambiguous, follow the STOP instructions in that task and report back instead of guessing.

---

## Project Context (read once, applies to all tasks below)

Dentix is a multi-tenant SaaS dental clinic platform.
- **Backend:** FastAPI + SQLAlchemy 2.0 async (`AsyncSession` only), PostgreSQL via Supabase, shared DB + Row-Level Security (RLS) via `DelfinaCare/rls` for tenant isolation, `pycasbin` / `fastapi-authz` for RBAC, Prefect for background jobs.
- **Frontend:** React 18 + Vite + Tailwind CSS, `i18next` for Arabic (RTL) / English (LTR), `vite-plugin-pwa` for PWA support, Zustand for state (in-memory only, no localStorage).
- **Known recurring bug pattern:** `MissingGreenlet` errors caused by lazy-loaded ORM attributes (e.g. a `patient_name` hybrid/property) being accessed after the session context that loaded them has closed, typically inside a `try` block after a partial rollback. The established fix is to extract needed scalar values into local variables *before* the `try` block — keep this pattern in mind if Task 3 touches patient/payment serialization.
- **Tenant isolation pattern:** belt-and-suspenders — RLS at the DB layer, plus explicit `tenant_id` checks in routers/CRUD. Do not weaken or bypass any of these layers while fixing the tasks below.

## Global Execution Rules
1. Run the **Discovery** commands for a task before touching any code. Do not guess file paths — confirm them via grep/find first; the paths suggested in this doc are best-guesses from prior sessions and may have moved.
2. **Mandatory pre-edit safety scan — perform this for every single file you are about to change or add code to, no exceptions:**
   - **Read the entire file**, top to bottom, before editing it — not just the lines a grep match pointed you to. You need the full current behavior in your head before changing any of it.
   - **Find every other consumer** of the function/component/endpoint/model field you're about to touch before touching it:
     ```bash
     grep -rn "<exact_function_or_component_or_field_name>" backend frontend/src 2>/dev/null
     ```
     If it's used in more than one place, treat every one of those call-sites as something your change must not silently break. List them in your output report (see "PRE-EDIT CHECK" field below).
   - **Confirm you're editing the right file**, not just the first plausible match. If grep returns multiple similarly-named files, similarly-named functions, or similar-looking logic in different routers/components, verify — by reading the actual code, not by the filename alone — which one is genuinely wired to the feature described in the task before changing anything.
   - **Prefer additive, backward-compatible changes** over changing shared default behavior. If a function/endpoint/component is used by more than one feature, add a new optional parameter, a new conditional branch, or a separate function rather than altering its existing default output — unless the task explicitly requires changing that default for everyone.
   - **Never copy-paste a fix into a similarly-named file "just in case."** Edit only the file(s) you confirmed are actually responsible for the behavior in question.
   - If, after this scan, you're not confident a change is safe (e.g. the function is called from 6 places and you can't confirm all 6 still behave correctly), treat this as a STOP condition for that task rather than pushing the change anyway.
3. If a task hits a **STOP condition**, stop work on that task only, document exactly what you found and why it's ambiguous, and move to the next task. Do not improvise a fix for an ambiguous case.
4. Keep each fix **surgical** — do not refactor unrelated code, do not "improve" adjacent logic that wasn't asked for. If you spot an unrelated bug while in a file, note it in the output report under "Incidental findings" — do not fix it silently.
5. After each fix, run `git diff` for the touched files and include the relevant hunks in your final report.
6. Do not add `psutil` (or any package) to `requirements.txt` as a side effect of any of these tasks.
7. Use the **Mandatory Output Format** at the end of this document for your final reply — one block per task.

---

## TASK 1 — Dashboard "Upcoming/Deferred Dues" widget shows ALL dues instead of TODAY's dues only

### Problem
On the main dashboard page, the dues/receivables widget (Arabic: "المستحقات الآجلة") currently lists every outstanding/deferred due regardless of date. It should only show dues that are due **today** (server date, tenant-aware if the clinic has a timezone setting — otherwise use server local date).

### Discovery
```bash
# Backend — find the endpoint/service powering this widget
grep -rln "dashboard" backend/routers/ 2>/dev/null
grep -rni "مستحق\|upcoming_due\|deferred_due\|due_today\|pending_due\|outstanding_balance\|outstanding_due" backend/routers/ backend/services/ backend/crud/ backend/schemas/ 2>/dev/null

# Frontend — find the widget component
grep -rli "مستحقات\|upcomingdues\|deferreddues\|duestoday\|outstanding" frontend/src 2>/dev/null
```
If `frontend/src` doesn't exist, locate the actual frontend root via `find . -maxdepth 2 -name "package.json" | grep -v node_modules` and adjust.

### Decision Criteria
- Identify the exact backend query feeding this widget (likely in a dashboard/stats router or service, possibly joining `payments`/`invoices`/installment records).
- Identify which date field represents "due date" for this data (e.g. `due_date`, `installment_due_date`, `next_payment_date`). There may be more than one candidate table (e.g. invoice-level due date vs. installment-level due date) — confirm which one the widget is actually querying.
- **STOP condition:** if the underlying model has no explicit due-date field at all (i.e. "deferred due" is computed purely as "any unpaid balance" with no date concept), do not invent a date field. Report this back with the model/table you found and ask for the correct semantics before changing behavior.

### Fix Instructions
- Add a filter so the query only returns rows where the relevant due-date column equals today's date (`DATE(due_date) = CURRENT_DATE` server-side, or equivalent SQLAlchemy `func.date(...) == date.today()`).
- Preserve existing tenant_id / RLS filtering exactly as-is — only add the date condition.
- If the widget has its own dedicated endpoint, fix it there. If it shares a generic "get all outstanding dues" endpoint with another feature (e.g. the Reports section in Task 3), do **not** change the shared endpoint's default behavior — instead either add a query parameter (e.g. `?due_filter=today`) consumed only by the dashboard widget, or create a dedicated lightweight endpoint. Do not break other consumers of the shared endpoint.

### Verification
- `git diff` on the touched backend file(s) and frontend widget file.
- Confirm via a manual query/log that a due dated yesterday or tomorrow no longer appears, and a due dated today still does.

---

## TASK 2 — PWA installed on tablet is locked to portrait orientation, does not rotate to landscape

### Problem
When Dentix is installed as a PWA (Add to Home Screen) on a tablet, the app launches and stays in portrait mode and refuses to rotate to landscape.

### Discovery
```bash
# Locate the PWA manifest config (vite-plugin-pwa usually configures this inside vite.config.*)
grep -rn "VitePWA\|vite-plugin-pwa" frontend/vite.config.* 2>/dev/null
grep -rn "orientation" frontend/vite.config.* frontend/public/manifest*.json frontend/**/manifest.webmanifest 2>/dev/null

# Also check for any JS-level orientation lock and any CSS hard-locking layout to portrait
grep -rn "screen.orientation\|orientation.lock\|lockOrientation" frontend/src 2>/dev/null
grep -rln "@media (orientation" frontend/src 2>/dev/null
```

### Decision Criteria
- If `manifest.orientation` (inside the `VitePWA({ manifest: { ... } })` config, or a standalone `manifest.json`/`manifest.webmanifest`) is explicitly set to `"portrait"` or `"portrait-primary"`, this is the root cause — the manifest is instructing the OS to lock the installed app's orientation.
- If no manifest orientation lock is found but a `screen.orientation.lock(...)` call exists in app JS, that is the root cause instead.
- **STOP condition:** if neither is found (no manifest orientation key, no JS lock call), do not guess — report that the lock is likely happening at the OS/device level or via a service worker config you couldn't locate, and list what you checked.

### Fix Instructions
- Change the manifest `orientation` value to `"any"` (recommended — allows the OS to rotate freely based on physical device orientation) rather than forcing `"landscape"`, since the goal is "let it rotate," not "force landscape always."
- Remove any `screen.orientation.lock('portrait')` call if found, unless it's conditionally scoped to a specific narrow mobile-phone breakpoint (in which case, scope the lock removal to tablet/larger breakpoints only — confirm the breakpoint logic before editing).
- After unlocking orientation, do a quick sanity grep for landscape-tablet responsive coverage:
  ```bash
  grep -rn "md:\|lg:\|landscape:" frontend/src/pages/Dashboard* 2>/dev/null
  ```
  If the dashboard/main layout has no tablet-landscape-specific Tailwind classes at all, note this in "Incidental findings" — it's a follow-up task, not part of this fix, unless rotating actually breaks the layout visibly (in which case flag it clearly as a blocking issue, don't silently fix the CSS).

### Verification
- `git diff` on the manifest config file.
- Confirm the built manifest (`dist/manifest.webmanifest` or equivalent after `vite build`) reflects `"orientation": "any"`.

---

## TASK 3 — Invoices page → Reports section: shallow, no patient filter, no deferred-dues filter, no per-patient detail

### Problem
The Reports tab/section inside the Invoices page currently shows only surface-level numbers. It is missing:
1. A filter to scope the report to a specific patient.
2. A filter/view to isolate only deferred/outstanding (unpaid) dues, separate from paid amounts.
3. A per-patient detail breakdown (drill-down) — currently there's no way to see an individual patient's full financial picture (total invoiced, total paid, outstanding balance, payment history, last/next payment dates) from this report.

### Discovery
```bash
# Frontend — locate the Reports section inside the Invoices page
grep -rln "Reports\|التقارير" frontend/src/pages 2>/dev/null
grep -rln "Invoices\|الفواتير" frontend/src/pages 2>/dev/null

# Backend — locate the endpoint(s) currently feeding this report
grep -rn "def.*report" backend/routers/payments.py backend/routers/invoices.py backend/routers/ 2>/dev/null
grep -rln "reports" backend/routers/ 2>/dev/null
```
Read the current report component and its backend response shape fully before changing anything — document the current fields returned (this is the "analysis" Eslam asked for) as part of your final report, not just the diff.

### Required Enhancements (explicit spec — implement all three)

**A. Patient filter**
- Add a patient selector (searchable dropdown, consistent with how patient search is implemented elsewhere in the app — reuse the existing patient-search component/endpoint if one exists rather than building a new one) that scopes all report numbers/lists to the selected patient. Must remain tenant-scoped (RLS-respecting) as-is.

**B. Deferred/outstanding dues filter**
- Add a toggle or filter control to switch the report between "all" and "outstanding/deferred only" (i.e. unpaid balance > 0). This should reuse the same due-amount logic as Task 1 where applicable, but is **not** date-scoped to "today" — this is the full outstanding-balance view, just filterable by status, independent of Task 1's dashboard widget.

**C. Per-patient detail view**
- Add a drill-down (expandable row, modal, or dedicated detail panel — match whatever UI pattern is already used elsewhere in the app for "view details") showing, per patient: total invoiced, total paid, total outstanding balance, full payment history (date, amount, method if tracked), and next due date if applicable.
- If implementing this surfaces the known `patient_name` `MissingGreenlet` pattern (lazy-loaded relationship accessed after session/rollback), apply the established fix — extract the needed scalar values before any `try` block — and explicitly call this out in your report as "applied known MissingGreenlet pattern fix," do not silently bundle it in as an unrelated change.

### Decision Criteria / STOP conditions
- If the existing Reports UI is built around a single non-paginated bulk query that would become very expensive once per-patient drill-down is added (e.g. N+1 risk), prefer a dedicated summary endpoint + a separate on-demand detail endpoint (called only when a patient row is expanded) over loading all patient details eagerly. If you're unsure which approach fits the existing codebase's conventions, report both options with your recommendation rather than picking silently.
- **STOP condition:** if there is no existing "outstanding balance" calculation anywhere in the codebase to reuse (i.e. you'd have to invent the business logic for what counts as "outstanding" from scratch), stop and report the exact payment/invoice schema you found so the calculation logic can be confirmed before implementing, rather than risking an incorrect financial figure being shipped.

### Fix Instructions
- Implement backend filter parameters (`patient_id`, `status=outstanding|all`) on the reports endpoint, or new endpoints if you determined that's cleaner per the decision criteria above.
- Implement the corresponding frontend filter controls and the per-patient detail view.
- Respect i18next — add Arabic and English strings for any new UI labels, do not hardcode either language.

### Verification
- `git diff` on all touched backend and frontend files.
- Confirm filters compose correctly (e.g. patient filter + outstanding-only filter together return the correct narrowed set).

---

## TASK 4 — Patient added by clinic admin to another doctor: patient is visible, but that patient's financial data is NOT visible to the doctor, even with the relevant permission enabled

### Problem
Flow: a clinic admin adds/assigns an existing patient to a doctor who didn't originally create that patient record. The patient then correctly appears in that doctor's patient list. However, that patient's financial data (payments/invoices) does **not** appear for the doctor — even when the permission/feature that's supposed to grant doctors visibility into patient finances is enabled for that doctor's role.

### Discovery
```bash
# Find the doctor-patient relationship field(s) on the patient model
grep -rn "doctor_id\|assigned_doctor\|primary_doctor" backend/models/*.py 2>/dev/null

# Find the permission/policy name controlling doctor visibility into patient finances
grep -rni "view_finance\|view_payment\|can_view_payments\|finance_permission\|view_patient_finance" backend -r 2>/dev/null

# Find where casbin policies / role permissions are defined and enforced
grep -rln "casbin\|enforce(" backend 2>/dev/null
grep -rn "def get_patient_payments\|def create_payment\|def list_payments" backend/routers/payments.py backend/crud/*.py 2>/dev/null
```

### Decision Criteria
- Determine which field the financial endpoints actually filter/check against when deciding whether a doctor can see a patient's payments: is it the patient's `assigned_doctor_id` (which the admin updates when reassigning), or is it something else entirely — e.g. `treatment_sessions.doctor_id` (only the doctor who actually performed a treatment), or the `created_by` field from when the patient was first registered?
- The bug is almost certainly one of:
  (a) the financial endpoint's permission check never consults the casbin "view finance" permission at all and instead hard-requires doctor == treatment-session doctor / created-by doctor, or
  (b) the permission check is correct but it's reading the wrong doctor-reference field (a stale one from creation time, not the current admin-assigned one).
- **STOP condition:** if you find the financial query is correctly scoped by `assigned_doctor_id` AND the permission check correctly checks the casbin policy, but it still fails — this means the bug is in policy *data* (the permission isn't actually being persisted/applied when the admin enables it for that doctor's role), not in the query logic. In that case, trace where the admin's "enable this permission for doctor" action writes data, and report exactly what's being written vs. what's being read at enforcement time, rather than changing the query logic.
- Do **not** weaken or bypass the RLS tenant-isolation layer to fix this — this bug is about doctor-level (intra-tenant) visibility, not tenant isolation. Keep both layers intact.

### Fix Instructions
- Align the financial endpoints' doctor-visibility check with the same field used to determine "this patient is assigned to this doctor" elsewhere in the app (the same field that already correctly drives the patient list visibility), gated by the existing casbin "view finance" permission check.
- Apply the fix consistently to all financial read endpoints involved (payments list, payment detail, invoices for patient, and the dashboard/reports endpoints if they're independently doing their own doctor-scoping — cross-check against Task 1 and Task 3 endpoints if they overlap, but do not refactor those tasks' code from here; just flag the overlap in your report if found).

### Verification
- `git diff` on all touched files.
- Confirm via test: doctor without the permission still cannot see another doctor's-originated patient's finances (negative case); doctor with the permission enabled, for a patient admin-assigned to them, now CAN see finances (positive case — this is the reported bug).

---

## Mandatory Output Format

For **each task**, reply with this block (do not omit any field, write "N/A" if genuinely not applicable):

```
### TASK <N> — <short title>
STATUS: [FIXED | STOPPED — needs input | PARTIALLY FIXED]
ROOT CAUSE: <one to three sentences>
PRE-EDIT CHECK: <for each file you changed — every other call-site/consumer you found via grep, and confirmation that each one still behaves correctly after your change. If a file has zero other consumers, state that explicitly.>
FILES CHANGED:
- <path> — <one-line summary of the change>
GIT DIFF:
<relevant diff hunks, trimmed to what matters>
TESTING PERFORMED: <what you checked, and the result>
INCIDENTAL FINDINGS: <anything unrelated you noticed but did NOT fix>
OPEN QUESTIONS (if STOPPED): <exact ambiguity, and the options you see>
```

Do not summarize all four tasks in prose at the end — the four structured blocks above are the deliverable.
