# DENTIX landing motion

A 12-second bilingual Remotion authoring preview, using the existing synthetic
product screenshots and local Cairo font. It is independent of the application
and is not imported by the production landing pages.

```sh
cd frontend/landing-motion
npm ci
npm run dev
```

Open `http://localhost:3100/DentixLandingArabic` or
`http://localhost:3100/DentixLandingEnglish`, then press Play.
`npm run lint` checks TypeScript and Remotion rules; `npm run build` bundles the
Studio preview without producing a video.

The website uses native CSS for its three-screen tour, patient journey progress,
headline entrance, and scroll entrance effects. This preserves the public pages'
zero-script contract. The CSS tour and Remotion composition are independently
authored versions of the same concept; changing one does not regenerate the other.
The Remotion project is optional authoring tooling and does not add dependencies
to the main frontend package or require a video export for the landing animation.

Manual acceptance (Arabic and English):

1. Open `/ar` or `/en`; watch the appointments, records, and chart scenes cycle.
2. Use the pause control, then use Tab and Space to resume it. Focusing a screenshot
   also pauses the tour so its full-size link stays stable during keyboard use.
3. Check at 320px, 390px, 768px, and desktop widths; scroll to the feature cards.
4. Enable the OS/browser reduced-motion setting. The first screenshot and all
   journey labels stay readable with no entrance, scrolling, or loop animations.
5. Disable JavaScript and repeat the tour, pause, registration, and full-size links.

The authoring preview does not deploy the website. Website changes are delivered
through a PR targeting staging. No video export was performed.

Local verification on the isolated staging base (2026-11-03): 24 static contract
tests and 30 browser scenarios passed (ar/en, 320–1440px, no-JS/reduced-motion).
Frontend lint and production build, Remotion lint/TypeScript and preview bundle
all exited 0. Footer navigation also wraps on narrow screens.
