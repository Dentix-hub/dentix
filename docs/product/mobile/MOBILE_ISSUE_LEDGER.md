# DENTIX Mobile UX / Responsive Issue Ledger

**Source baseline:** `staging`  
**Implementation branch:** `fix/mobile-ux-responsive-forensic`  
**Status vocabulary:** `OPEN`, `IMPLEMENTED_PENDING_VERIFICATION`, `VERIFIED`, `BLOCKED`.

An item is not `VERIFIED` until the relevant build, regression suite, responsive viewport and direction checks pass.

## Root Cause Map

| Root cause | Observed impact | Owner / remediation |
|---|---|---|
| fixed viewport height (`h-screen`) | browser chrome and software keyboard can reduce the visible viewport without updating layout | application shell uses dynamic `dvh` + flex/min-height |
| page-level `overflow-x-hidden` | masks real overflow and makes clipped content inaccessible | removed from shell/body; added document-overflow test |
| banners positioned outside normal shell flow | header/content can be covered on short phones | banners now consume layout height normally |
| desktop-width overlays | clipping/off-screen controls at compact widths | canonical responsive Modal/Dialog/BottomSheet contract |
| fixed-width date picker | 320px picker cannot fit inside a 320px viewport once page padding is included | picker converted to full-width mobile surface with dynamic max height |
| route-local desktop tables | excessive lateral scrolling / hidden actions | shared `AdvancedTable` mobile-card fallback + module-specific cards |
| multi-row tab wrapping | unreadable patient/settings/finance navigation | contained horizontal `TabGroup` scroller |
| hover-revealed controls | required functions unavailable on touch | actions remain visible or move to explicit menus |
| drag-only state transitions | appointment status change inaccessible to non-drag users | explicit status select added to list and Kanban cards |
| dense icon clusters | accidental destructive actions and poor touch ergonomics | 44px targets + primary/secondary action separation |
| spatial clinical UI leaking width | dental chart can force whole page horizontal scroll | chart retains contained 2D scroll only |
| clickable non-semantic containers | keyboard and assistive-tech interaction gaps | dashboard KPIs / chart teeth converted to buttons |
| duplicate local page padding | cramped compact screens | removed/normalized in touched high-risk routes |

## P0 / P1 Ledger

| ID | Route / viewport / language | Severity | Evidence / root cause | Owning component | Fix approach | Verification | Status |
|---|---|---:|---|---|---|---|---|
| MOB-FND-001 | global shell / all compact widths | P0 | `Layout.jsx` used `h-screen`; viewport height could be stale when browser chrome or keyboard changes | `Layout.jsx` | `100dvh` shell with min-height flex contract | build + mobile projects + keyboard/manual pass | IMPLEMENTED_PENDING_VERIFICATION |
| MOB-FND-002 | global shell / 320–430 | P0 | main/body horizontal clipping was used as a bug mask | `Layout.jsx`, `index.css` | remove page-level `overflow-x-hidden`; fix owners; assert document width | `mobile-responsive.spec.ts` overflow helper | IMPLEMENTED_PENDING_VERIFICATION |
| MOB-SHELL-001 | mobile header | P1 | persistent search field competed with menu, clinic title and notifications | `GlobalSearch.jsx`, `Layout.jsx` | compact 44px trigger -> search bottom sheet | responsive route sweep + manual keyboard test | IMPLEMENTED_PENDING_VERIFICATION |
| MOB-SHELL-002 | mobile notifications | P1 | anchored surface and tiny dismiss controls risked clipping/touch errors | `NotificationBell.jsx` | bottom sheet on phone; bounded desktop popover; 44px dismiss | overlay bounds/manual list test | IMPLEMENTED_PENDING_VERIFICATION |
| MOB-SHELL-003 | short phone heights | P0 | fixed banners could collide with sticky header/content | `GlobalBanner.jsx`, `SubscriptionBanner.jsx`, `Layout.jsx` | move banners into shell flow; wrap long copy; touch actions | 320×640 + short landscape manual | IMPLEMENTED_PENDING_VERIFICATION |
| MOB-UI-001 | shared legacy modal consumers | P0 | many feature modals inherited desktop dialog behavior | `Modal.jsx`, `DentixDialog.jsx`, `DentixBottomSheet.jsx` | phone defaults to canonical sheet; desktop dialog remains | existing overlay regression updated + responsive overlay assertions | IMPLEMENTED_PENDING_VERIFICATION |
| MOB-DATE-001 | date/time picker / 320px | P0 | panel used fixed `w-[320px]`; available inner width can be ~288px | `DateTimePicker.jsx` | viewport-contained full-width mobile picker; `dvh` max-height; internal scroll | appointment picker responsive test | IMPLEMENTED_PENDING_VERIFICATION |
| MOB-APT-001 | `/appointments` / phone | P1 | desktop weekly calendar was the initial experience | `Appointments.jsx` | phone initial view is operational list; desktop retains calendar | mobile projects | IMPLEMENTED_PENDING_VERIFICATION |
| MOB-APT-002 | `/appointments` / phone | P1 | six-column list table had no semantic phone fallback | `Appointments.jsx` | appointment cards below `md`; desktop table retained | route overflow + visual/manual | IMPLEMENTED_PENDING_VERIFICATION |
| MOB-APT-003 | Kanban / touch | P0 | status transition depended heavily on drag; no phone status control in board/list | `Appointments.jsx` | status select on cards and board; backend status API unchanged | non-drag status regression | IMPLEMENTED_PENDING_VERIFICATION |
| MOB-APT-004 | Kanban / touch | P1 | card deletion was hover-revealed; whole card drag increased accidental gestures | `Appointments.jsx` | visible delete + dedicated drag handle + activation distance | touch/manual + E2E presence | IMPLEMENTED_PENDING_VERIFICATION |
| MOB-APT-005 | create appointment / phone keyboard | P0 | create flow could outgrow viewport and hide confirm | `Appointments.jsx`, shared `Modal`, `DateTimePicker` | sheet + internal sticky action footer + responsive picker | mobile overlay/picker + keyboard manual | IMPLEMENTED_PENDING_VERIFICATION |
| MOB-INV-001 | `/inventory` / <1024 | P1 | stock experience relied on multi-column desktop table | `StockList.jsx` | semantic material cards below `lg`; table only desktop | inventory card regression + overflow sweep | IMPLEMENTED_PENDING_VERIFICATION |
| MOB-INV-002 | `/inventory` / phone | P1 | edit/delete/smart/session actions were dense inline controls | `StockList.jsx` | session action promoted; secondary actions behind explicit More surface | touch/manual | IMPLEMENTED_PENDING_VERIFICATION |
| MOB-INV-003 | `/inventory` / phone | P1 | search/filter/receive/new controls competed in one toolbar | `StockList.jsx` | full-width search + stacked/grid controls | 320/390 sweep | IMPLEMENTED_PENDING_VERIFICATION |
| MOB-INV-004 | add material | P0 | feature used custom fixed overlay and dense two-column mobile fields | `AddMaterialModal.jsx` | migrate to shared responsive Modal; one-column phone form; sticky actions | overlay bounds + keyboard manual | IMPLEMENTED_PENDING_VERIFICATION |
| MOB-INV-005 | receive stock | P0 | custom fixed overlay + date input risked clipping / keyboard obstruction | `ReceiveStockModal.jsx` | shared Modal + responsive month picker + sticky actions | overlay/date picker/manual | IMPLEMENTED_PENDING_VERIFICATION |
| MOB-TABLE-001 | dashboard/admin/feature table consumers | P1 | `AdvancedTable` always rendered desktop table | `AdvancedTable.jsx` | default mobile semantic cards below `md`; contained table above | route sweep + consumer regression | IMPLEMENTED_PENDING_VERIFICATION |
| MOB-DASH-001 | dashboard phone | P1 | KPI cards used clickable `div`, large fixed padding/type and hover affordances | `Dashboard.jsx` | semantic buttons; compact responsive composition | visual + accessibility/manual | IMPLEMENTED_PENDING_VERIFICATION |
| MOB-DASH-002 | dashboard chart | P1 | desktop-oriented fixed 320px chart height/margins/tick density | `Dashboard.jsx` | responsive 230→320 height, compact margins/ticks | visual matrix | IMPLEMENTED_PENDING_VERIFICATION |
| MOB-DASH-003 | dashboard timeline | P1 | timeline items were clickable containers with hover styling | `Dashboard.jsx` | full tappable buttons with safe wrapping | visual/manual | IMPLEMENTED_PENDING_VERIFICATION |
| MOB-TABS-001 | patient details/settings/finance/inventory | P1 | shared tabs wrapped into multiple rows and could hide active context | `TabGroup.jsx` | contained horizontal scroller; active tab scrolls into view | RTL/LTR manual + responsive route sweep | IMPLEMENTED_PENDING_VERIFICATION |
| MOB-PD-001 | `/patients/:id` | P1 | patient identity/action block could become cramped with long content | `PatientInfoCard.jsx` | safe wrapping + mobile action grid + 44px targets | long-content/manual | IMPLEMENTED_PENDING_VERIFICATION |
| MOB-PD-002 | dental chart | P1 | spatial surface has 700px minimum width and clickable non-semantic tooth nodes | `DentalChartSVG.jsx` | explicitly contained horizontal scroll; intentional LTR anatomy island; tooth buttons | page overflow check on representative patient fixture + touch/manual | IMPLEMENTED_PENDING_VERIFICATION |
| MOB-PD-003 | tooth selection overlay | P1 | route-local fixed overlay still uses `max-h-[95vh]` and local close/action geometry | `PatientDetails.jsx` | migrate to canonical responsive overlay | overlay bounds/manual | OPEN |
| MOB-LAB-001 | `/labs` add/edit | P1 | hand-built fixed modal, `max-h-[90vh]`, phone/email forced into two columns | `Labs.jsx` | migrate to shared responsive Modal and one-column compact fields | overlay bounds + keyboard manual | OPEN |
| MOB-LAB-002 | `/labs` stats/cards | P1 | clickable `div` stat cards and lab card semantics are pointer-centric | `Labs.jsx` | semantic buttons/details trigger + touch-sized management controls | keyboard/touch/manual | OPEN |
| MOB-TEST-001 | responsive regression | P0 release gate | previous visual suite covered narrow patient baseline only | `playwright.config.ts`, `mobile-responsive.spec.ts` | 320, AR 390, EN 412, tablet projects + overflow/overlay assertions | GitHub Actions | IMPLEMENTED_PENDING_VERIFICATION |
| MOB-TEST-002 | existing overlay regression | P0 release gate | test assumed every Modal stays centered dialog on phone | `ui-regression.spec.ts` | selector now follows responsive dialog/sheet contract | GitHub Actions | IMPLEMENTED_PENDING_VERIFICATION |
| MOB-CI-001 | release gate | P0 | current CI visual step does not yet invoke new responsive project matrix | `.github/workflows/ci.yml` | add responsive Playwright execution before container release | GitHub Actions | OPEN |
| MOB-VIS-001 | visual baselines | P0 release gate | shell/search/table changes intentionally alter mobile snapshots | Playwright snapshot artifacts | run CI, inspect diffs, update only expected baselines | GitHub Actions artifact review | BLOCKED until PR CI run |

## P2 / P3 Follow-Up Areas

These remain in scope for the final acceptance matrix even where no current P0/P1 evidence has been proven yet:

- Analytics/report chart label density and short-height landscape.
- Users and Super Admin action density.
- Support/profile long-form keyboard behavior.
- Finance sub-route consistency after shared Tab/Modal/Table/DatePicker propagation.
- AI chat keyboard + safe-area behavior.
- Long Arabic/English stress strings across clinic name, patient name, procedure names and financial values.
- Remaining physical `left/right` Tailwind utilities that are intentional vs. those that should become logical start/end.
- Exact touch-target audit for all low-frequency icon actions.

## Release Verification Requirements

Before any item can move from `IMPLEMENTED_PENDING_VERIFICATION` to `VERIFIED`:

1. frontend production build passes;
2. lint and design-system guardrails pass or pre-existing failures are recorded separately;
3. frontend unit tests pass;
4. existing critical-path E2E passes;
5. existing desktop/mobile visual regressions are reviewed;
6. the responsive Playwright matrix passes at 320, Arabic phone, English phone and tablet;
7. representative manual RTL/LTR and keyboard flows are reviewed on staging;
8. final diff confirms no API, schema, RBAC, tenant-isolation, financial or clinical business-rule changes.
