# DENTIX AI Agent Stack Architecture

## 1. Purpose
This document defines the architecture, governance, hierarchy, and operating standards of the DENTIX AI agent stack. It establishes a lean, native, cross-runtime standard that aligns AI coding agents directly with the actual DENTIX technology stack (FastAPI, React 18, PostgreSQL, Flutter).

## 2. Supported Tools
The DENTIX AI agent stack is designed to be natively compatible with modern AI coding environments:
- **Codex / OpenAI Agent Ecosystem**: Reads root `AGENTS.md` and discovers progressive-disclosure skills under `.agents/skills/*/SKILL.md`.
- **Antigravity IDE / Agent Ecosystem**: Operates with repository instructions and `.agents/skills/` as local workspace customizations.

## 3. Source-of-Truth Hierarchy
When instructions or design decisions interact, agents must strictly follow this precedence:
1. **Explicit Current Task / Approved Plan**: Current user prompt or approved implementation plan.
2. **Security & Compliance Constraints**: Multi-tenant isolation (`tenant_id`), RBAC permissions, clinical PII protection, and financial integrity.
3. **`PROJECT_STANDARDS.md`**: Canonical DENTIX architecture and engineering specifications.
4. **Root `AGENTS.md`**: Cross-runtime execution, safety, and completion discipline.
5. **Task-Specific Documentation**: Domain documents under `docs/` and module READMEs.
6. **Relevant `.agents/skills/`**: Progressive-disclosure guidance for specific technical domains.
7. **General Engineering Best Practices**: Clean code and standard language idioms.

`PROJECT_STANDARDS.md` defines the canonical DENTIX architecture and engineering conventions. `AGENTS.md` defines cross-runtime execution, safety, and completion discipline. If `AGENTS.md` is ever interpreted in a way that conflicts with `PROJECT_STANDARDS.md` on project architecture, `PROJECT_STANDARDS.md` wins.

## 4. Root `AGENTS.md` Purpose
Root `AGENTS.md` acts as the primary, always-active cross-runtime contract. It establishes invariant guardrails:
- Backend Router -> Service -> CRUD -> Database flow.
- Frontend React 18 + Vite + React Query + Zustand standards (no Redux).
- Flutter / Dart mobile client patterns.
- Multi-tenancy enforcement via `tenant_scope.py`.
- Strict debugging and plan execution discipline.

## 5. Skill Discovery Structure
Skills reside in the `.agents/skills/` directory. Each skill is encapsulated in its own folder containing a single `SKILL.md` with standard YAML frontmatter:
```text
.agents/
├── README.md
└── skills/
    ├── dentix-backend-fastapi/
    │   └── SKILL.md
    ├── dentix-code-review/
    │   └── SKILL.md
    ├── dentix-database-migrations/
    │   └── SKILL.md
    ├── dentix-frontend-react/
    │   └── SKILL.md
    ├── dentix-mobile-flutter/
    │   └── SKILL.md
    ├── dentix-performance/
    │   └── SKILL.md
    ├── dentix-plan-execution/
    │   └── SKILL.md
    ├── dentix-security-tenancy-rbac/
    │   └── SKILL.md
    ├── dentix-systematic-debugging/
    │   └── SKILL.md
    └── dentix-testing-verification/
        └── SKILL.md
```

## 6. The 10 Native DENTIX Skills Catalog
| Skill Name | Purpose & Trigger | Primary Files / Stack |
|:---|:---|:---|
| `dentix-plan-execution` | Multi-phase plan execution without skipping requirements | Cross-repo plans, task ledgers |
| `dentix-backend-fastapi` | FastAPI layered architecture (Router->Service->CRUD) | `backend/routers/`, `backend/services/`, `backend/crud/` |
| `dentix-frontend-react` | React 18, Vite, Tailwind CSS, TanStack Query, Zustand | `frontend/src/` |
| `dentix-mobile-flutter` | Flutter mobile client, Riverpod state, GoRouter, Dio | `dentix_mobile/lib/` |
| `dentix-security-tenancy-rbac` | Tenant boundaries, RBAC permissions, clinical PII, finance | `backend/core/tenant_scope.py`, auth |
| `dentix-database-migrations` | SQLAlchemy async models, PostgreSQL indexing, Alembic | `backend/alembic/`, `backend/models/` |
| `dentix-testing-verification` | Test runner discovery, pytest (70% CI coverage), vitest | `backend/tests/`, `frontend/src/tests/` |
| `dentix-systematic-debugging` | 4-phase evidence-first root cause analysis (RCA) | Defect resolution, error traces |
| `dentix-code-review` | Severity-graded review (`CRITICAL` to `NOTE`) & priority | Pull requests, code diffs |
| `dentix-performance` | Measurement-first query optimization, caching, rendering | SQL profiling, React memo, caching layer |

## 7. When a New Skill is Justified
A new skill may only be introduced if all the following conditions are met:
1. A new, permanent technology or major architectural subsystem is added to DENTIX (e.g. WhatsApp AI integration service, specialized DICOM medical imaging service).
2. The domain requires distinct, non-trivial recurring guidance that cannot cleanly fit into one of the existing 10 skills.
3. The skill can be expressed concisely (1-5 KB) with specific trigger descriptions.

## 8. When NOT to Add a Skill
Do NOT create a skill for:
- One-off tasks or temporary migration scripts.
- Generic language or framework tutorials already documented in public docs.
- Technologies not actively used in the DENTIX repository.
- Overlapping responsibilities that belong in an existing skill.

## 9. Plan Execution Policy
When executing multi-step tasks or implementation plans:
- Maintain an explicit task ledger with statuses (`NOT_STARTED`, `IN_PROGRESS`, `PASS`, `BLOCKED`, `N/A`).
- Never skip acceptance criteria or declare premature completion.
- Re-read remaining tasks after every phase.
- Only report `DONE` when all planned requirements pass verification.

## 10. Verification Policy
- Execute test commands before claiming success.
- Separate pre-existing baseline failures from newly introduced changes.
- Adhere to repository CI thresholds (70% backend coverage fail-under).

## 11. Security & Multi-Tenancy Policy
- Multi-tenancy is invariant: every database query touching clinic data must scope by `tenant_id`.
- RBAC is enforced server-side on every router endpoint.
- Protect sensitive financial data and clinical patient records from unauthorized exposure.

## 12. Maintenance Policy
- Review `.agents/skills/` periodically to ensure instructions match current repository code.
- Avoid bloating skills; keep instructions actionable, concise, and focused.
- Ensure all skills maintain valid YAML frontmatter and proper file sizes.

## 13. Repository Hygiene Validation
Validate that:
- Legacy agent-framework directories are absent.
- Only the native `.agents/skills/` surface is present.
- No obsolete project-level AI-tool configuration remains.
- Repository skills remain limited to the approved DENTIX catalog.

To validate the static integrity of the AI agent stack:
```bash
# Verify skill count and frontmatter
powershell -Command "Get-ChildItem .agents/skills | Measure-Object"
```
