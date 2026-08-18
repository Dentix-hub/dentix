# Dentix Module Audit Template

Use this template for module-by-module audits. Evidence paths are mandatory. Do not turn a UX audit into an unapproved feature project.

## Module purpose

- User problem:
- Primary users/roles:
- Current entry points:
- Evidence:

## Existing capabilities

| Capability | Evidence path | Status (VERIFIED/PARTIAL/UNKNOWN) | Notes |
|---|---|---|---|
| | | | |

## Current behavior contract

Document behavior that must remain stable unless a separate product/backend change is explicitly approved:

- Routes:
- API contracts:
- Business rules:
- Data ownership/tenant rules:
- Permission rules:
- Side effects/background work:

## What works

Evidence-backed strengths only.

## What is broken

For each defect include reproducible evidence, affected role/environment, severity, and test coverage.

## What is functionally correct but UX-poor

Separate usability friction from functional defects.

## What is visually outdated / inconsistent

Compare against `frontend/DESIGN.md` and current `frontend/src/shared/ui/` primitives.

## Security / RBAC

- Required permissions:
- Route-level guard:
- Server-side guard:
- Tenant isolation implications:
- Sensitive data concerns:
- Evidence/tests:

## Performance

- Measured bottleneck:
- Baseline:
- Query/network/render evidence:
- Regression budget:

## Accessibility

- Keyboard/focus:
- Labels/names:
- Contrast/state not conveyed by color alone:
- Screen-reader semantics:
- Reduced motion:

## Mobile

- Breakpoints/layout:
- Touch targets:
- Dense tables/forms:
- PWA/native considerations:

## RTL

- Arabic layout direction:
- Logical spacing/alignment:
- Icons/chevrons:
- Numbers/dates/mixed-direction text:

## Tests

- Existing unit/integration/E2E:
- Missing regression coverage:
- Required tests before merge:

## Proposed improvement class

Choose one or more:

- `BUG_FIX`
- `UX_REFINEMENT`
- `VISUAL_SYSTEM_ALIGNMENT`
- `ACCESSIBILITY`
- `PERFORMANCE`
- `TEST_GAP`
- `DOCUMENTATION`
- `NEW_FEATURE` — requires separate explicit approval and must not be smuggled into the module audit.

## New-feature boundary

List requested ideas that are not verified current capabilities. Do not implement them under an audit/refactor scope.

## Acceptance criteria

Each criterion must be observable/testable and preserve verified API/schema/business behavior unless a separate approved change states otherwise.

- [ ] Existing verified capability preserved.
- [ ] RBAC and tenant isolation preserved.
- [ ] No unapproved API/schema/business-rule change.
- [ ] Relevant unit/integration/E2E checks pass.
- [ ] Desktop/mobile and Arabic/English states reviewed where applicable.
- [ ] Accessibility requirements reviewed.
- [ ] Performance does not regress against the captured baseline.
