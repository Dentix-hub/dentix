<!-- CLASSIFICATION: ACTIVE -->
# DENTIX AI Agent Stack Architecture

## Purpose

This document defines the architecture of the DENTIX AI agent stack: how optional planning, optional delegated execution, and native project-specific safety skills relate to each other.

## Components

```text
Matt       = optional planning methodology (clarification, specification, decomposition)
Delegate   = optional delegated execution transport (bounded task handoff)
DENTIX     = project-specific safety and architecture protection
```

**Matt thinks when needed. Delegate executes when useful. DENTIX protects.**

## Supported Runtimes

- **Codex / OpenAI Agent Ecosystem**: Reads root `AGENTS.md` and discovers skills under `.agents/skills/*/SKILL.md`.
- **Antigravity IDE**: Operates with repository instructions and `.agents/skills/` as local workspace customizations.

## Canonical Authorities

| Concern | Owner |
|---|---|
| Architecture & engineering | `PROJECT_STANDARDS.md` |
| Development lifecycle | `docs/engineering/DEVELOPMENT_WORKFLOW.md` |
| Safety invariants & execution routing | `AGENTS.md` |
| Product requirements | Active product / domain specifications |
| CI thresholds & commands | `.github/workflows/ci.yml` |

External skills (Matt, Delegate) are optional methodology or transport helpers. They are never repository authorities and cannot override DENTIX HARD invariants.

## Native DENTIX Skills (4)

| Skill | Classification | Purpose |
|---|---|---|
| `dentix-security-tenancy-rbac` | HARD / HIGH_RISK specialist | Tenant isolation, RLS, RBAC, auth, clinical/finance access |
| `dentix-database-migrations` | HARD / HIGH_RISK specialist | PostgreSQL schema safety, Alembic migrations, data integrity |
| `dentix-testing-verification` | Verification gate selector | Minimum sufficient verification for a diff |
| `dentix-code-review` | HIGH_RISK review | Severity-graded code review for sensitive changes |

Skills are loaded on-demand via progressive disclosure, not preloaded.

## Execution Routing

```text
Clear task              → execute directly
Unclear task            → use relevant planning skill when it adds value
Delegate                → only when delegation is materially cheaper or safer
NORMAL work             → targeted verification, one diff inspection, commit
HIGH_RISK work          → relevant safety skill + verification + independent review
```

## When a New Skill is Justified

A new skill may be introduced only when:
1. A new, permanent technology or major subsystem is added to DENTIX.
2. The domain requires distinct, non-trivial recurring guidance not covered by existing skills.
3. The skill can be expressed concisely with specific activation triggers.

## Maintenance

- Review `.agents/skills/` periodically to ensure instructions match current code.
- Keep skills actionable, concise, and focused.
- Do not bloat skills with generic framework tutorials.
