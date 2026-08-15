# Handoff: Frontend Lint Cleanup — Phase 1 (Unused Vars/Imports Only)

## Context
`cd frontend && npm run lint` fails in CI because `eslint --max-warnings 250` sees 295
total warnings (0 errors). Breakdown, confirmed by counting the CI log:

- `no-unused-vars`: 268
- `react-hooks/exhaustive-deps`: 24
- `react-refresh/only-export-components`: 3

**This handoff covers ONLY the 268 `no-unused-vars` warnings.** Deleting all of them
drops the total to 27, well under the 250 threshold — no `package.json` changes needed.

**Do NOT touch `react-hooks/exhaustive-deps` or `react-refresh/only-export-components`
warnings in this pass.** They require manual behavioral review and are out of scope here.
If you find yourself wanting to "fix" one to be thorough — don't. Leave it exactly as is.

## Step 1 — Discovery (machine-readable source of truth)
Do not work from the pasted CI log. Regenerate a fresh, precise list:

```bash
cd frontend
npx eslint . --ext js,jsx --format json > /tmp/eslint-report.json
```

Then filter to only `no-unused-vars` messages (ruleId === "no-unused-vars") per file,
with line, column, and the exact identifier name from the message text.

## Step 2 — Categorize every warning before touching anything
For each `no-unused-vars` warning, classify it as one of:

- **A — Unused import specifier**: e.g. `import { Sparkles, Filter } from 'lucide-react'`
  where `Sparkles` is never referenced. Remove just that specifier (or the whole `import`
  line if it's the only specifier left, or the whole statement if it was already a
  single default import like `import React from 'react'`).
- **B — Unused local variable / destructured value**: e.g. `const [loading, setLoading] = useState(...)`
  where `loading` is never read. Safe to delete ONLY if the right-hand side has no side
  effects. If the declaration's initializer is a function call that does something
  (mutates, subscribes, calls an API, dispatches), do NOT delete it — see Step 4.
- **C — Unused function parameter**: message says "Allowed unused args must match /^_/u".
  Rename the parameter to `_paramName` (do not delete it — deleting can break positional
  call sites or arity-sensitive callback signatures like `(row, index) => ...`).

## Step 3 — Per-file execution
1. `grep -n '<IdentifierName>'` the full file first. If the identifier appears anywhere
   ESLint's static analysis might have missed (JSX prop shorthand, template literal,
   comment describing intended future use), STOP on that one warning — do not guess,
   log it in the "Flagged" table (Step 6) instead.
2. Make the edit (delete import specifier / delete unused declaration / rename param to `_name`).
3. Re-run `npx eslint <file> --ext js,jsx` on just that file. Confirm the specific
   `no-unused-vars` warning is gone and no new errors were introduced.

## Step 4 — STOP conditions (do not fix, flag instead)
- Any Category B variable whose initializer is a function call with plausible side
  effects (not just `useState`/plain destructuring) — flag it.
- `frontend/src/utils.js:34` (`refreshToken`) and `frontend/src/tests/utils.test.js:2`
  (`logout`) — before touching either, run:
  ```bash
  grep -rn "refreshToken" frontend/src
  grep -rn "logout" frontend/src/tests
  ```
  to confirm these aren't consumed elsewhere in a way the local-file lint scope can't see.
- Any unused state/setter pair in `frontend/src/features/admin/SuperAdmin/` or
  `frontend/src/pages/admin/` (e.g. `showPaymentModal`/`setShowPaymentModal`,
  `paymentForm`/`setPaymentForm`, `overrideTenant`/`setOverrideTenant`). These look like
  half-wired features (state declared, never rendered). Do not delete — flag as
  "possibly unfinished feature, needs Eslam's call," not dead code.
- If a file has both a `no-unused-vars` warning and unrelated pre-existing bugs you
  notice while reading it — do not fix the unrelated bug. Flag it separately. Scope
  discipline: this pass is lint-only.

## Step 5 — Full verification
```bash
cd frontend
npm run lint
```
Confirm:
- 0 errors
- `no-unused-vars` count is 0 (or matches exactly the count of items you flagged and
  intentionally left, per Step 4)
- `react-hooks/exhaustive-deps` count is still 24 (unchanged)
- `react-refresh/only-export-components` count is still 3 (unchanged)
- Total warning count is well under 250

## Step 6 — Required output format
Two tables, code-quoted evidence for every row (no summary-only claims):

**Table 1 — Fixed**
| File | Line | Identifier | Category (A/B/C) | Action | Before → After (code snippet) |

**Table 2 — Flagged / Not Touched**
| File | Line | Identifier | Reason flagged |

Plus: `git diff --stat frontend/src` output, and confirmation that every hunk in
`git diff frontend/src` is one of: deleted import specifier, deleted unused declaration,
or parameter renamed to `_name`. Nothing else should appear in the diff.
