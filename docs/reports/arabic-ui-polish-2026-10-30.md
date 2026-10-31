<!-- CLASSIFICATION: ACTIVE -->
# Arabic UI polish — local verification

Status: DONE locally on `fix/arabic-ui-polish`, based on `origin/staging` at `126638e`. GitHub delivery authorized on 2026-10-31; staging acceptance pending.

Password visibility and patient-search icons now have separate flex layout slots, preventing overlap with either Arabic or Latin text. Search retains its searchbox semantics and search keyboard, using one explicit clear button without a browser-native duplicate. Remember-me has a 44px label target and a visible 20px checkbox; existing server persistence behavior is retained. Username/current-password autocomplete metadata is explicit; no credentials are stored in browser storage.

Dashboard charts load complete components with direct Recharts children: the old lazy wrappers around individual series/axes concealed their types from Recharts. Real revenue curves, axes, status sectors and legend now render; zero-revenue and empty-status responses show messages. The existing financial values, efficiency calculation, API endpoints and permissions are unchanged. The quick-start widget is temporarily unmounted from Dashboard; its progress and backend remain intact.

The picker localizes Arabic month names, weekday labels and morning/evening controls, uses a Saturday-first RTL calendar and ascending LTR time grids, and stays centered on desktop/tablet RTL screens (`right:auto` removes conflicting positional constraints). Date, month and datetime callbacks retain their existing ISO formats and timezone behavior.

Verification executed:

- `npm run test -- --run src/tests/Login.test.jsx src/shared/ui/DateTimePicker.test.jsx src/features/dashboard/DashboardCharts.test.jsx src/tests/AuthProvider.test.jsx src/tests/AuthProvider.loginLifecycle.test.jsx src/tests/AuthProvider.2fa.test.jsx src/tests/api.test.js`: exit 0; 44 passed in 7 files.
- `/home/ubuntu/dentix/.venv/bin/python -m pytest backend/tests/test_remember_me.py -q`: exit 0; 5 passed. Existing tests cover persistent/session cookies, refresh rotation and 2FA choice propagation. Existing deprecation/tracer warnings do not affect the result.
- Chart regression experiment: temporarily used the previous individual-lazy-component import pattern; both new real-Recharts regression tests failed (missing curve, zero sectors). Restored the identical fixed source afterward. No test assertions were weakened.
- Chromium with real components and synthetic query/API fixtures: 8 scenarios passed across ar/en × 320/390/768/1440px, with dark mode at 390px. Each checks password visibility, icon bounds, remember-me label/keyboard/submitted value, search/result/clear behavior, populated/empty charts, absent quick-start widget, localized picker, time order, dialog/page bounds and canonical datetime callback; zero page errors. Additional scrolled chart inspection confirmed the rendered curve and numeric axes. These are local component/browser checks, not live-clinic acceptance.
- `npm run lint`, `npm run build`, `npm run design:guardrails` and `git diff --check`: exit 0. Guardrails retain existing report-only legacy findings; no governance or CI files changed.

Browser scripts, temporary harness copies and screenshots are in `/tmp/dentix-ui-polish-evidence/`; the harness was removed from the application source before delivery.

Manual acceptance (under 10 minutes):

1. In Arabic login, enter a long password, toggle visibility, and select remember-me by clicking its label and pressing Space. Repeat in English. With remember-me selected, sign in, restart the browser with normal session restoration disabled, and verify recovery; repeat unselected to verify session-cookie behavior. Explicit logout must still end the session.
2. In the header, type an Arabic name and Latin text. Confirm the lens/text/clear button never overlap, exactly one clear button appears, results navigate, and clear empties the search. Repeat on mobile search sheet.
3. Open Dashboard with appointments/payments. Verify both charts and the status legend, today's appointments and efficiency. Test an empty clinic: explanatory messages appear. Quick-start guide stays hidden.
4. Create/edit an appointment in Arabic. Verify Arabic month/weekday/period names, calendar and hour order, change day/time and confirm; re-open and confirm the stored value. Repeat in English and on tablet/mobile. No production deployment or live data writes were performed by this task.
