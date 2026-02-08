# PLAN: AI Governance & Architecture Hardening
> **Goal**: Stabilize the system, enforce strict AI governance, and refactor architecture for scalability and security.

## 🧠 Strategic Objectives
1.  **Safety First**: Prevent unsafe AI actions via strict Policy Engine.
2.  **Architecture**: Decouple Router/AI from Logic (Service Layer Pattern).
3.  **Security**: Rule-based access (RBAC) and Audit Logs.
4.  **Observability**: Traceability for every AI decision.

---

## 🧱 Phase 0: Stabilization (Prerequisite)
> **Status**: 🛑 BLOCKER for all other phases.
- [ ] **0.1. Freeze & Snapshot**
    - [ ] Stop all feature development.
    - [ ] Create DB Snapshot (tag: `backend-baseline-safe`).
    - [ ] Backup current system prompts (`backend/ai/prompts_backup/`).

---

## 🔥 Phase 1: AI Governance (Critical)
> **Focus**: Preventing the AI from doing harm.

### 1.1. AI Execution Policy Engine
- **File**: `backend/ai/policy/execution_policy.py`
- **Logic**:
    - Map `Intent` -> `Allowed Tools`.
    - Map `Intent` -> `RequiresConfirmation` (Boolean).
    - Map `Intent` -> `AllowedRoles` (List).
    - Map `Intent` -> `AllowedFields` (Whitelist).
- **Example**: `UPDATE_PATIENT` requires `doctor` role and explicit confirmation.

### 1.2. AI Read-Only Mode
- **File**: `backend/core/config.py`
- **Logic**: Add `AI_READ_ONLY` flag (env var).
- **Enforcement**: If `true`, block all `POST/PUT/DELETE` tool calls in `ToolExecutor`.

### 1.3. AI Audit Ledger
- **File**: `backend/models/ai_audit.py`
- **Table**: `ai_action_log` (`tenant_id`, `user_id`, `mid`, `intent`, `tool`, `payload`, `result`, `timestamp`).
- **Hook**: Log *every* attempt in `ToolExecutor`, even blocked ones.

---

## 🧩 Phase 2: Architectural Refactor (Decoupling)
> **Focus**: Separating concerns. "Routers should not think".

### 2.1. Service Layer Implementation
- **Files**:
    - `backend/services/patient_service.py`
    - `backend/services/appointment_service.py`
    - `backend/services/billing_service.py`
- **Refactor**: Move logic from `routers/` to `services/`.
- **Rule**: Routers only handle validation and HTTP response.

### 2.2. Unify AI & API Paths
- **Refactor**: Update `backend/ai/tools/` to call `Services` instead of `Models/DB` directly.
- **Benefit**: API and AI use *exact same* logic and guards.

---

## 🔐 Phase 3: Enhanced Security (RBAC)
> **Focus**: Granular access control.

### 3.1. Advanced RBAC
- **Roles**: `super_admin`, `clinic_admin`, `doctor`, `assistant`, `receptionist`.
- **File**: `backend/core/permissions.py`.
- **Integration**: Enforce permissions in `Service` layer (so it applies to both AI and API).

### 3.2. Confirmation Layer
- **Logic**: Middleware/Service check for sensitive actions.
- **Flow**: Action -> Check Sensitivity -> If Sensitive -> Require OTP/Password/Explicit "Yes".

### 3.3. Security Events Log
- **Table**: `security_events` (`event_type`, `severity`, `user_id`, `details`, `ip`).
- **Events**: Failed logins, blocked AI intents, RBAC violations.

---

## 🧪 Phase 4: Debug & Testing
### 4.1. Regression Suite
- **Rule**: Lock main branch. No merge without passing tests.
- **Action**: Expand `tests/` coverage for critical paths.

### 4.2. AI Decision Tracing
- **Feature**: Add `X-AI-Trace-ID` headers and log logic flow (`Score`, `PolicyCheck`, `ToolSelection`).
- **Output**: JSON Structure for debugging "Why did AI do this?".

---

## 📊 Phase 5: Observability
- **Slow Query Logger**: Middleware to log queries > 500ms.
- **AI Monitor**: Track token usage and "Time to Intent" per tenant.

---

## 🤖 Phase 6: AI Maturity
- **Confidence Thresholds**: Enforce strict cutoffs (e.g. < 0.7 = Ask User).
- **Feedback Loop**: API for users to thumbs-up/down AI responses.

---

## 🧼 Phase 7: Developer Experience
- **Docs**: Auto-generate API Docs and AI Intent Matrix.
- **Dev Rules**: Script to prevent schema changes without migration files.

---

## 📋 Verification Plan
1.  **Phase 1 Check**:
    - Try to update patient as "Assistant". -> Should FAIL (RBAC).
    - Try to delete record in Read-Only mode. -> Should FAIL.
2.  **Phase 2 Check**:
    - Call API endpoint vs AI Tool -> Should result in IDENTICAL DB state.
3.  **Phase 3 Check**:
    - Verify `ai_action_log` populates correctly after intent execution.
