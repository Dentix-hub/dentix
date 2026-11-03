/**
 * routeInventory.mjs
 * Authoritative single inventory of routes for Dentix.
 *
 * Distinguishes:
 * - Public indexable marketing pages
 * - Public indexable legal pages
 * - Application-only pages (noindex)
 * - Protected application pages (noindex, auth required)
 * - Redirect-only routes (must NEVER appear in sitemap)
 */

export const CANONICAL_ORIGIN = 'https://www.dentixs.app';

// 1. Authoritative public indexable routes in PR-A
export const PR_A_INDEXABLE_ROUTES = [
  'https://www.dentixs.app/ar',
  'https://www.dentixs.app/en',
  'https://www.dentixs.app/ar/privacy',
  'https://www.dentixs.app/en/privacy',
  'https://www.dentixs.app/ar/terms',
  'https://www.dentixs.app/en/terms',
];

// 2. Authoritative public indexable routes added in PR-B
export const PR_B_INDEXABLE_ROUTES = [
  'https://www.dentixs.app/ar/about',
  'https://www.dentixs.app/en/about',
  'https://www.dentixs.app/ar/contact',
  'https://www.dentixs.app/en/contact',
  'https://www.dentixs.app/ar/plans',
  'https://www.dentixs.app/en/plans',
  'https://www.dentixs.app/ar/dental-clinic-management-software',
  'https://www.dentixs.app/en/dental-clinic-management-software',
  'https://www.dentixs.app/ar/dental-patient-records',
  'https://www.dentixs.app/en/dental-patient-records',
  'https://www.dentixs.app/ar/appointments-finance',
  'https://www.dentixs.app/en/appointments-finance',
];

// Current full active indexable routes for sitemap
export const CURRENT_ACTIVE_INDEXABLE_ROUTES = [
  ...PR_A_INDEXABLE_ROUTES,
];

// Page identity and translation expectations come from the active inventory.
export function publicPageOptions(canonical) {
  if (!CURRENT_ACTIVE_INDEXABLE_ROUTES.includes(canonical)) {
    throw new Error(`Not an active indexable public URL: ${canonical}`);
  }
  const pathname = new URL(canonical).pathname;
  const lang = pathname.split('/')[1];
  const suffix = pathname.slice(lang.length + 1);
  const expectedAlternates = {};
  for (const code of ['ar', 'en']) {
    const alternate = `${CANONICAL_ORIGIN}/${code}${suffix}`;
    if (CURRENT_ACTIVE_INDEXABLE_ROUTES.includes(alternate)) expectedAlternates[code] = alternate;
  }
  const fallback = expectedAlternates.ar || expectedAlternates.en;
  expectedAlternates['x-default'] = fallback;
  const otherLanguage = lang === 'ar' ? 'en' : 'ar';
  return {
    lang,
    dir: lang === 'ar' ? 'rtl' : 'ltr',
    canonical,
    loginTexts: lang === 'ar' ? ['تسجيل الدخول'] : ['log in', 'login'],
    targetLangSwitch: new URL(expectedAlternates[otherLanguage] || fallback).pathname,
    expectedAlternates,
  };
}

// 3. Application-only routes (entry point, noindex in raw HTML)
export const APPLICATION_SHELL_ROUTES = [
  '/',
  '/login',
  '/register',
];

// 4. Protected clinical & administrative routes (noindex, auth-required)
export const PROTECTED_ROUTES = [
  '/dashboard',
  '/patients',
  '/appointments',
  '/dental-chart',
  '/finance',
  '/analytics',
  '/labs',
  '/inventory',
  '/settings',
  '/users',
  '/admin',
];

// 5. Redirect-only routes (must NEVER appear in sitemap)
export const REDIRECT_ONLY_ROUTES = [
  '/ar/',
  '/en/',
  '/ar/index.html',
  '/en/index.html',
  '/privacy',
  '/terms',
  '/ar/privacy/',
  '/en/privacy/',
  '/ar/terms/',
  '/en/terms/',
  '/ar/privacy/index.html',
  '/en/privacy/index.html',
  '/ar/terms/index.html',
  '/en/terms/index.html',
];
