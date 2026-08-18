# DENTIX UI PRINCIPLES

Status: **CANONICAL UI GOVERNANCE**  
Direction: **Dentix Clinical Workspace**  
Established by: DENTIX Plan 02 — Design System V2 + UI Regression Foundation

These principles govern new UI work and gradual migration of existing UI. They do not authorize product-feature changes, API/schema changes, business-rule changes or mass rewrites. When prose conflicts with executable behavior, `PROJECT_TRUTH.md` precedence applies.

## 1. Content before decoration.

Clinical, operational and financial information must remain the visual priority. Decoration may support hierarchy but must not compete with content.

## 2. Clinical clarity before novelty.

Prefer predictable, readable and low-friction interaction patterns over visually novel patterns. Users must be able to scan and act quickly under routine clinical pressure.

## 3. Semantic color.

Color communicates meaning first: primary action/selection, success, warning, danger, information, focus and disabled states. Decorative color must be restrained and must not conflict with semantic status.

## 4. One canonical interaction pattern per action.

Equivalent actions should use the same primitive and interaction model. Do not create local modal, select, date-picker, toast, menu, drawer or button patterns when a canonical primitive exists.

## 5. Dense but breathable.

Dentix is a professional workspace. Optimize for information density without crowding: compact rows and controls, consistent rhythm, enough separation for safe scanning.

## 6. Progressive disclosure.

Show the information/actions required for the current decision. Reveal advanced details when needed instead of presenting all controls at once.

## 7. Functional motion only.

Motion should explain change, preserve spatial context, indicate loading or support disclosure. Avoid decorative bounce, rotation, lift or infinite animation when it does not communicate state. Respect reduced-motion preferences.

## 8. Opaque content surfaces by default.

Dialogs, menus, popovers, selects, date pickers, tables, forms and primary content panels must remain readable without depending on background artwork. Translucency is an exception, not the default.

## 9. Restrained glass/blur.

Backdrop blur may support an overlay backdrop or rare shell chrome. Do not use glassmorphism as the default content-container treatment.

## 10. Accessibility is structural.

Keyboard navigation, focus order, focus visibility, accessible names, semantic roles, focus trapping/return, error association and reduced motion are part of component architecture—not final polish.

## 11. Arabic/English parity.

Every canonical primitive must support Arabic and English with equivalent capability, readable typography, logical-direction layout and intentional RTL behavior. Do not hardcode page direction inside reusable components unless the content itself requires it.

## 12. Intentional mobile adaptation.

Do not merely shrink desktop UI. Choose the appropriate mobile form—responsive layout, drawer, bottom sheet, full-screen workflow or horizontally scrollable data—while preserving capability.

## 13. Design-system primitives are mandatory.

New UI must use canonical Dentix primitives/tokens when they exist. Feature code must not introduce a second implementation of a solved shared interaction without documented justification.

## 14. Page patterns are mandatory.

Pages should converge on documented workspace patterns for resource indexes, object workspaces, scheduling, finance, settings and administration instead of inventing a unique shell for every route.

## 15. Complex workflows should not default to modal dialogs.

Confirmation and small contextual tasks may use dialogs. Complex forms, multi-step clinical work and large editing experiences should be evaluated for drawers, bottom sheets, dedicated pages or full-screen mobile layouts. Route/behavior semantics must not change silently during migration.

## 16. Forms optimize correctness.

Forms must make labels, help, required state, validation, units, dates, money, read-only state, save progress, dirty state, cancellation and double-submit protection predictable. Correct data entry outranks visual novelty.

## 17. Data pages optimize scanability.

Tables, lists and dashboards must make comparison, status, sorting/filtering, loading, empty state and row actions easy to scan. Avoid decorative cardification that fragments related data.

---

## Enforcement model

Plan 02 introduces these rules gradually:

1. detect existing violations;
2. report them without breaking CI;
3. migrate representative/high-risk consumers;
4. warn on new violations;
5. enforce only after the canonical replacement path is proven.

Existing legacy code is migration debt, not automatic permission to duplicate the pattern.