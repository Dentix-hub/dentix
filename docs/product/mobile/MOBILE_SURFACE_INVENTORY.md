# DENTIX Mobile Surface Inventory

**Baseline branch:** `staging`  
**Implementation branch:** `fix/mobile-ux-responsive-forensic`  
**Scope:** frontend mobile UX, responsive layout, touch ergonomics, overlays, RTL/LTR, accessibility, visual regression, and mobile-specific perceived responsiveness.

## Responsive Contract

- Base styles target compact phones first.
- `sm` is used for larger-phone/narrow-landscape enhancements.
- `md` is the main tablet/dense-layout transition.
- `lg` is the desktop application-shell transition.
- `xl+` is reserved for wide-screen enhancements.
- Document-level horizontal scrolling is not an accepted responsive strategy.
- Dental chart and Kanban are approved contained 2D surfaces; their parent document must still remain within the viewport.
- Shared `Modal` consumers use a bottom sheet below 640 CSS px and the canonical dialog above that breakpoint unless explicitly opted out.
- Shared tabs use contained horizontal scrolling instead of wrapping into unreadable multi-row navigation.

## Route and Surface Inventory

| Route / surface | Primary owner | Shared / major UI | Mobile table/list behavior | Overlay / special surface | Main mobile / RTL / touch risk | Current implementation status |
|---|---|---|---|---|---|---|
| `/login` | authentication page | form controls | N/A | authentication form | keyboard, 320px reflow, input semantics | audit required in final matrix |
| `/register` | registration page | form controls | N/A | registration form | long form + keyboard | audit required in final matrix |
| `/forgot-password` | auth recovery | form controls | N/A | recovery form | keyboard / long translated copy | audit required in final matrix |
| `/reset-password` | auth recovery | form controls | N/A | recovery form | keyboard / confirmation reachability | audit required in final matrix |
| `/terms` | terms page | document content | N/A | none | long copy / RTL | low risk |
| `/privacy` | privacy page | document content | N/A | none | long copy / RTL | low risk |
| `/` | `frontend/src/pages/Dashboard.jsx` | `PageHeader`, `Card`, `AdvancedTable`, shared `Modal`, charts | KPI cards + timeline; detail tables reflow through `AdvancedTable` | revenue/debtor details | clickable cards, fixed chart heights, number wrapping | responsive pass implemented; pending CI/matrix verification |
| `/appointments` | `frontend/src/pages/Appointments.jsx` | `PageHeader`, `Modal`, `DateTimePicker`, `PatientSelect`, DnD | semantic phone cards; desktop table | weekly calendar; contained Kanban; create appointment sheet/dialog | desktop-only list, drag-only state transition, hover actions, calendar density | phone list + non-drag status + bounded Kanban implemented; pending verification |
| `/patients` | patients directory page | `PageHeader`, patient search/filter primitives, shared overlays | existing mobile patient cards + desktop table | add/edit patient | dense row actions, search/filter fit | shared shell/overlay/tab fixes apply; route included in regression matrix |
| `/patients/:id` | `frontend/src/pages/PatientDetails.jsx` | `PatientInfoCard`, `TabGroup`, treatment/payment/Rx overlays | tab-specific | `DentalChartSVG` contained 2D; treatment/Rx/payment/edit flows | clinical density, tab overflow, tooth selection, long patient identity | tabs, identity card and dental chart hardened; tooth-selector overlay still requires canonical migration |
| `/inventory` | `frontend/src/pages/Inventory.jsx` + `features/inventory/StockList.jsx` | `PageHeader`, `TabGroup`, shared `Modal` | semantic cards below `lg`; contained table at desktop | Add Material, Receive Stock, smart/session/details | desktop-only stock table, dense actions, raw overlays | cards/action simplification + two critical write-flow overlays implemented; pending verification |
| `/finance` / overview | finance module | finance shell, tabs, date range, tables/charts | route-specific cards/tables + shared `AdvancedTable` where used | date range / write flows | tab density, money isolation, date picker | prior staging mobile fixes + shared Tab/Modal/Table/DatePicker improvements; full acceptance matrix pending |
| `/finance/patient-accounts` | finance module | tables/search/filters | shared responsive table behavior where `AdvancedTable` is used | account details | dense financial columns | pending matrix verification |
| `/finance/payments` | finance module | finance filters/table | mobile card strategy where route/shared table supports it | payment write flow | amount/action reachability | pending matrix verification |
| `/finance/expenses` | finance module | finance filters/table | route mobile layout + shared primitives | expense write flow | date filter + keyboard | representative responsive test route |
| `/finance/compensation` | finance module | tabs/table/forms | shared responsive primitives | compensation settings | wide values / actions | pending matrix verification |
| `/finance/doctors/:id/payroll` | finance module | payroll tables/forms | shared responsive primitives | payroll actions | large financial values / contained details | pending matrix verification |
| `/finance/activity` | finance module | activity list/table | shared responsive table behavior where applicable | details | timestamp + RTL | pending matrix verification |
| `/finance/reports` | finance module | filters/charts | responsive chart/table contract | report filters | chart axis density | pending matrix verification |
| `/billing` | legacy redirect | redirect to finance | N/A | N/A | route preservation | preserved |
| `/expenses` | legacy redirect | redirect to finance expenses | N/A | N/A | route preservation | preserved |
| `/labs` | `frontend/src/pages/Labs.jsx` | lab cards, lab details/orders | existing lab cards | add/edit lab + details + global orders | raw add/edit overlay, clickable-card semantics, dense form | P1 migration still open; included in responsive route matrix |
| `/analytics` | analytics page | charts/tables/filters | shared responsive primitives | filters/details | fixed chart height / legends | lower-priority final matrix pending |
| `/users` | users page | tables/forms | shared responsive table behavior where applicable | user create/edit | dense role/action controls | lower-priority final matrix pending |
| `/settings` | settings page | `TabGroup`, forms | N/A / settings lists | settings editors | tabs, long labels, form keyboard | shared tabs/overlays apply; representative responsive test route |
| `/settings/price-lists` | price-list settings | table/forms | shared responsive primitives | price list editor | money / long procedures | final matrix pending |
| `/settings/insurance` | insurance settings | table/forms | shared responsive primitives | insurance editor | long labels / money | final matrix pending |
| `/admin` | Super Admin dashboard | admin cards/charts | route-specific | admin details | dense admin dashboard | lower-priority final matrix pending |
| `/admin/tenants` | Super Admin tenants | tables/actions | shared responsive table behavior where applicable | tenant edit/actions | dense action clusters | final matrix pending |
| `/admin/users` | Super Admin users | tables/actions | shared responsive table behavior where applicable | user actions | role/action density | final matrix pending |
| `/admin/finance` | Super Admin finance | tables/charts | shared responsive primitives | finance details | wide financial values | final matrix pending |
| `/admin/messages` | Super Admin support | lists/detail | list/detail | message detail | split-pane/dense action risk | final matrix pending |
| `/admin/settings` | Super Admin settings | forms | N/A | settings editors | keyboard / long copy | final matrix pending |
| `/admin/system/logs` | Super Admin error log | data-heavy table | contained/shared responsive strategy | details | inherently wide log content | final matrix pending |
| `/ai/stats` | AI stats | charts/tables | shared responsive primitives | details | charts / long tokens | final matrix pending |
| `/support` | support page | forms/messages | list/form | support composer | keyboard | final matrix pending |
| `/profile` | profile page | forms | N/A | profile editors | keyboard | final matrix pending |
| global shell | `frontend/src/layouts/Layout.jsx` | sidebar, header, search, notifications, banners, AI trigger | N/A | mobile sidebar, global search sheet, notification sheet | `h-screen`, page clipping, banner collision, background interaction | dynamic-viewport shell implemented; pending CI/matrix verification |
| global search | `frontend/src/shared/ui/GlobalSearch.jsx` | search results | list | compact search bottom sheet | wide header field / keyboard / result clipping | mobile sheet implemented |
| notifications | `frontend/src/shared/ui/NotificationBell.jsx` | notification list | list | mobile sheet / desktop popover | viewport clipping, hover-only dismiss | mobile sheet + touch actions implemented |
| date/time picker | `frontend/src/shared/ui/DateTimePicker.jsx` | calendar/time controls | N/A | responsive bottom-aligned picker | fixed 320px width, short-height clipping | responsive dynamic-viewport picker implemented |
| shared tables | `frontend/src/shared/ui/AdvancedTable.jsx` | TanStack table | semantic cards below `md`, table above | N/A | desktop-only horizontal tables | mobile card fallback implemented |
| shared tabs | `frontend/src/shared/ui/TabGroup.jsx` | pill/underline/vertical tabs | N/A | contained tab scroller | multi-row wrapping, active tab visibility | contained horizontal scroller implemented |
| dental chart | `frontend/src/features/dental/DentalChartSVG.jsx` | SVG teeth | N/A | approved contained 2D surface | touch semantics, page overflow, anatomical direction | contained scroll + real tooth buttons + intentional LTR island implemented |
| print invoice | `/print/invoice/:patientId` | print layout | print-specific | separate from main Layout | mobile is not primary; print regression | out of main responsive shell scope unless used interactively |
| print Rx | `/print/rx/:patientId` | print layout | print-specific | separate from main Layout | mobile is not primary; print regression | out of main responsive shell scope unless used interactively |

## Representative Acceptance Matrix

The strategic automated matrix is intentionally risk-based rather than combinatorial:

- `mobile-compact-320`: 320 × 640, compact reflow and overflow safety.
- `mobile-ar`: 390 × 844, Arabic RTL, light.
- `mobile-en`: 412 × 915, English LTR, dark strategic subset.
- `tablet`: 768 × 1024.
- Existing `visual-desktop` and `visual-mobile` projects remain the visual-regression references.

The automated responsive route sweep includes Dashboard, Appointments, Patients, Inventory, Finance Expenses, Labs, and Settings. Remaining routes are tracked for manual/follow-up verification in the issue ledger and release report.
