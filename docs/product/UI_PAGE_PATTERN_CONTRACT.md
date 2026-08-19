# Dentix Page Pattern Contract — Plan 02 Phase 10

Status: **TARGET CONTRACT — layout implementation pending**

Page patterns standardize hierarchy and responsive behavior; they do not force identical pages or new product features.

## 1. ResourceIndex

Use for directories/lists such as Patients, Users, inventory resources and admin entities.

Order:
1. PageHeader (title/context + primary action)
2. optional summary/status strip
3. search/filter controls
4. table/list content
5. pagination/secondary actions

Mobile: keep primary action obvious; filters collapse intentionally; preserve all essential row actions.

## 2. ObjectWorkspace

Use for one entity with multiple related sections, such as patient details.

Order:
1. identity/header + high-value status/actions
2. local navigation/tabs
3. primary object content
4. contextual side/secondary panels where space allows

Avoid turning every section into an elevated card. On mobile, linearize sections and keep critical actions reachable.

## 3. SchedulingWorkspace

Use for Appointments/calendar surfaces.

Order:
1. date/range/navigation + primary scheduling action
2. resource/status filters
3. calendar/agenda workspace
4. contextual appointment details/editing through canonical overlay pattern

Desktop can prioritize calendar density; mobile may prioritize agenda/day flow. Existing appointment capability remains unchanged.

## 4. FinancialWorkspace

Use for `/finance/*`.

Order:
1. financial scope/date context
2. headline metrics/obligations
3. local Finance navigation
4. filter/action bar
5. dense table/chart/report content

Money values use consistent numeric hierarchy. Avoid decorative color that can be mistaken for profit/loss/status meaning.

## 5. SettingsWorkspace

Use for clinic settings and configuration.

Order:
1. PageHeader
2. settings navigation/category context
3. grouped form sections
4. save/status/error affordance

Long settings forms should prefer sections and sticky save affordance over nested cards/modals.

## 6. AdminDataWorkspace

Use for Super Admin tenants/users/finance/system data.

Order:
1. system context + high-risk scope marker
2. filters/search/actions
3. dense data table/workspace
4. contextual details via canonical drawer when appropriate

High-risk/destructive actions require explicit permissions and confirmation; visual redesign must not weaken backend authorization.

## Shared page rules

- One page-level `h1`.
- Primary action placement is predictable.
- PageHeader is preferred over local title reinvention.
- Filters sit near the data they affect.
- Loading/empty/error patterns are consistent.
- Tabs represent local workspace navigation, not arbitrary button groups.
- Opaque content surfaces by default.
- Do not wrap every section in a card.
- Desktop density and mobile adaptation are designed deliberately.
- RTL reverses logical layout while preserving domain reading conventions for phone, IDs, money/numbers where appropriate.

## Rollout

Patterns may begin as documentation and small layout primitives. Existing pages migrate when already being audited/refactored; Plan 02 must not churn every route simply to achieve visual uniformity.

Phase 10 becomes DONE when these patterns are documented (this file), canonical shell/layout helpers exist where justified, and representative ResourceIndex/ObjectWorkspace/Financial or Scheduling pages demonstrate the system.