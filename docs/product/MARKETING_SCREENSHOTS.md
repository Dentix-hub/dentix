# Marketing product screenshots

The `/ar` and `/en` pages use screenshots of the actual React application, not
illustrations or a re-created interface. All names, identifiers, amounts, and
clinical examples are fictional. The public pages explicitly disclose this.

To refresh the screenshots when the application UI changes, use the existing
frontend dependencies:

1. In `frontend/`, run `npm run dev -- --host 127.0.0.1 --port 5178 --strictPort`.
2. In another terminal in `frontend/`, run
   `node scripts/capture-marketing-screenshots.mjs`.
3. Review all six images in `frontend/public/marketing/screens/` before committing.

The capture script uses a fresh browser context per language and intercepts all
API requests with local fictional fixtures, including automatic onboarding events.
It never signs into a live service. Unexpected API requests fail the capture.
Only local frontend resources and the application's existing Google Fonts hosts
can load. No application code, permissions, or database settings are changed.
Screenshots are encoded as WebP without changing the rendered interface. The
dashboard capture shows the top 620 pixels; patient and chart captures are 1000
pixels high. All captures are 1440 pixels wide and can be opened at full size
from the public page.

The public marketing pages themselves have no executable JavaScript, external
font requests, or API calls. They self-host Cairo (the application's Arabic font)
under `frontend/public/marketing/fonts/`, with its SIL Open Font License in
`OFL.txt`. The Arabic and Latin variable-font subsets were retrieved from Google
Fonts' Cairo v31 distribution. License source:
https://github.com/google/fonts/blob/main/ofl/cairo/OFL.txt

Keep all screenshots and fonts under `marketing/` so existing service-worker and
precache exclusions continue to apply. Font binaries are tracked directly through
the narrowly scoped `.gitattributes` exception, allowing Git bundles to contain
the complete public-page assets without separate Git LFS objects.
