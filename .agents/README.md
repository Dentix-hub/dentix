# DENTIX Agent Skills

This directory contains repository-scoped skills used by supported AI coding runtimes (including Codex and Antigravity).

## Source Priority
1. Explicit current task requirement or approved implementation plan
2. Security, tenant isolation, RBAC, data integrity, and privacy constraints
3. `PROJECT_STANDARDS.md`
4. Root `AGENTS.md`
5. Task-specific repository documentation
6. Relevant `.agents/skills/` instructions
7. General engineering conventions

## Skill Catalog (11 Native Skills)
1. `dentix-plan-execution`: Disciplined execution of approved multi-phase implementation plans without skipping steps.
2. `dentix-orchestration`: Dependency-aware orchestration of atomic tickets, isolated delegates/worktrees, independent review, and repository verification.
3. `dentix-backend-fastapi`: FastAPI / Python layered patterns (Router -> Service -> CRUD -> Database), Pydantic schemas, and async execution.
4. `dentix-frontend-react`: React 18 + Vite, Tailwind CSS, TanStack Query server state, Zustand client state, RTL/LTR layout, and accessibility.
5. `dentix-mobile-flutter`: Flutter / Dart mobile client, Riverpod state, GoRouter navigation, and Dio HTTP clients.
6. `dentix-security-tenancy-rbac`: Multi-tenant boundary isolation (`tenant_id`), role-based access control, clinical PII masking, and financial data protection.
7. `dentix-database-migrations`: SQLAlchemy async models, PostgreSQL indexing, and safe Alembic migration authoring.
8. `dentix-testing-verification`: Test-driven verification discipline across Pytest (70% CI coverage target), Vitest, and Flutter test suites.
9. `dentix-systematic-debugging`: 4-phase evidence-first root cause analysis (RCA) and minimal surgical fixing.
10. `dentix-code-review`: Structured code review with severity classification (`CRITICAL`, `HIGH`, `MEDIUM`, `LOW`, `NOTE`) and priority sequencing.
11. `dentix-performance`: Measurement-first performance profiling across database queries (N+1), backend async tasks, React rendering, and Flutter rebuilds.

## Authoring Rules
- **Focused Responsibility**: One skill = one primary responsibility.
- **DENTIX Specificity**: Do not add generic language or framework skills unless actively used by DENTIX.
- **No Duplication**: Do not duplicate core contract rules already enforced in root `AGENTS.md`.
- **High Justification Bar**: Do not add a new skill until an existing skill cannot cleanly cover the recurring need.
