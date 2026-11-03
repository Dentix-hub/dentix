#!/usr/bin/env node
/**
 * verify-marketing-artifacts.mjs
 * Validates production build artifacts for Dentix marketing and discovery assets.
 * Uses real DOM/XML and robots parsing to prevent false passes.
 */
import { readFileSync, existsSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { gzipSync } from 'node:zlib';
import { JSDOM } from 'jsdom';
import {
  CURRENT_ACTIVE_INDEXABLE_ROUTES,
  APPLICATION_SHELL_ROUTES,
  PROTECTED_ROUTES,
  REDIRECT_ONLY_ROUTES,
} from './routeInventory.mjs';

export const ALLOWED_SITEMAP_URLS = new Set(CURRENT_ACTIVE_INDEXABLE_ROUTES);

export function validateMarketingHtml(html, distDir = null, options = {}) {
  const {
    lang = 'ar',
    dir = 'rtl',
    canonical = 'https://www.dentixs.app/ar',
    loginTexts = ['تسجيل الدخول'],
    targetLangSwitch = '/en',
    expectedAlternates = {
      ar: 'https://www.dentixs.app/ar',
      en: 'https://www.dentixs.app/en',
      'x-default': 'https://www.dentixs.app/ar',
    },
  } = options;
  const errors = [];
  const dom = new JSDOM(html);
  const doc = dom.window.document;

  // 1. Language & Direction
  const htmlEl = doc.documentElement;
  if (!htmlEl) {
    errors.push('Missing <html> root element');
    return errors;
  }
  if (htmlEl.getAttribute('lang') !== lang) {
    errors.push(`<html> attribute lang must be '${lang}', found: '${htmlEl.getAttribute('lang')}'`);
  }
  if (htmlEl.getAttribute('dir') !== dir) {
    errors.push(`<html> attribute dir must be '${dir}', found: '${htmlEl.getAttribute('dir')}'`);
  }

  // 2. Canonical URL
  const canonicalEl = doc.querySelector('link[rel="canonical"]');
  if (!canonicalEl || canonicalEl.getAttribute('href') !== canonical) {
    errors.push(`Missing or invalid canonical link: expected '${canonical}', found: '${canonicalEl ? canonicalEl.getAttribute('href') : 'none'}'`);
  }

  // 3. Bidirectional hreflang reciprocity & validation
  const hreflangElements = Array.from(doc.querySelectorAll('link[rel="alternate"][hreflang]'));
  const foundAlternates = {};

  for (const el of hreflangElements) {
    const code = el.getAttribute('hreflang');
    const href = el.getAttribute('href') || '';

    // Validate language code
    if (!['ar', 'en', 'x-default'].includes(code)) {
      errors.push(`Invalid hreflang language code: '${code}'`);
    }

    foundAlternates[code] = href;

    // Validate alternate href is HTTPS canonical domain
    if (!href.startsWith('https://www.dentixs.app/')) {
      errors.push(`hreflang="${code}" must use canonical domain 'https://www.dentixs.app/', found: '${href}'`);
    }

    // Verify alternate target file exists on disk if distDir provided
    if (distDir && href.startsWith('https://www.dentixs.app/')) {
      const pathname = new URL(href).pathname;
      const targetRel = pathname === '/' ? 'index.html' : pathname.replace(/^\//, '');
      const possibleFile1 = path.join(distDir, targetRel, 'index.html');
      const possibleFile2 = path.join(distDir, targetRel);
      const possibleFile3 = path.join(distDir, `${targetRel}.html`);

      const targetExists = existsSync(possibleFile1) || existsSync(possibleFile2) || existsSync(possibleFile3);
      if (!targetExists) {
        errors.push(`hreflang="${code}" alternate target not found on disk: '${href}'`);
      } else {
        // Target must not be noindexed
        const targetHtmlPath = existsSync(possibleFile1) ? possibleFile1 : (existsSync(possibleFile3) ? possibleFile3 : possibleFile2);
        try {
          const targetContent = readFileSync(targetHtmlPath, 'utf8');
          if (targetContent.includes('content="noindex') || targetContent.includes("content='noindex")) {
            errors.push(`hreflang="${code}" alternate target contains noindex: '${href}'`);
          }
        } catch (_) {}
      }
    }
  }

  // Verify all expected alternates exist and match
  for (const [expCode, expHref] of Object.entries(expectedAlternates)) {
    if (!foundAlternates[expCode]) {
      errors.push(`Missing required alternate hreflang="${expCode}": expected '${expHref}'`);
    } else if (foundAlternates[expCode] !== expHref) {
      errors.push(`Mismatched alternate hreflang="${expCode}": expected '${expHref}', found '${foundAlternates[expCode]}'`);
    }
  }

  // 4. Executable Script Guard (Zero JS execution)
  const scripts = doc.querySelectorAll('script');
  for (const s of scripts) {
    const type = s.getAttribute('type');
    if (type !== 'application/ld+json') {
      errors.push(`Executable script found: ${s.outerHTML.slice(0, 80)}`);
    }
    if (s.hasAttribute('src')) {
      errors.push(`External script tag found: ${s.getAttribute('src')}`);
    }
    if (type === 'application/ld+json') {
      try {
        const parsed = JSON.parse(s.textContent);
        if (!parsed || typeof parsed !== 'object') {
          errors.push('JSON-LD content is not a valid JSON object');
        }
      } catch (err) {
        errors.push(`Invalid JSON-LD syntax: ${err.message}`);
      }
    }
  }

  // 5. Inline Event Handlers Guard
  const allElements = doc.querySelectorAll('*');
  for (const el of allElements) {
    for (const attr of el.attributes) {
      if (attr.name.toLowerCase().startsWith('on')) {
        errors.push(`Inline event handler attribute found on <${el.tagName.toLowerCase()}>: ${attr.name}="${attr.value}"`);
      }
    }
  }

  // 6. Manifest & SW Links
  if (doc.querySelector('link[rel="manifest"]')) {
    errors.push(`${lang}/index.html illegally contains PWA manifest link`);
  }

  // 7. Action Links: Login must point to / (never /login)
  const links = doc.querySelectorAll('a');
  let loginCount = 0;
  let hasLangSwitch = false;
  for (const link of links) {
    const href = link.getAttribute('href') || '';
    const text = link.textContent.trim().toLowerCase();

    if (href.startsWith('javascript:')) {
      errors.push(`Executable javascript: pseudo-protocol found in link: ${href}`);
    }

    if (loginTexts.some((lt) => text.includes(lt.toLowerCase()))) {
      loginCount++;
      if (href !== '/') {
        errors.push(`Login link must point to '/', found '${href}'`);
      }
    }

    if (href === '/login' || href.startsWith('/login?')) {
      errors.push(`Direct link to /login found: '${href}'`);
    }

    if (href === targetLangSwitch) {
      hasLangSwitch = true;
    }

    // Local static file check if distDir provided
    if (distDir && href.startsWith('/') && !href.startsWith('//') && href.includes('.')) {
      const localFile = path.join(distDir, href.replace(/^\//, ''));
      if (!existsSync(localFile)) {
        errors.push(`Broken local asset link in ${canonical}: ${href}`);
      }
    }
  }

  if (loginCount < 2) {
    errors.push(`Expected at least 2 login links pointing to '/', found ${loginCount} in ${canonical}`);
  }

  if (!hasLangSwitch) {
    errors.push(`Missing language switcher link pointing to '${targetLangSwitch}' in ${canonical}`);
  }

  // 8. Check <link> assets on disk (stylesheets, icons, touch icons)
  if (distDir) {
    const linkElements = doc.querySelectorAll('link');
    for (const linkEl of linkElements) {
      const rel = (linkEl.getAttribute('rel') || '').toLowerCase();
      const href = linkEl.getAttribute('href') || '';
      // Exclude canonical, dns-prefetch, preconnect, alternate
      if (['stylesheet', 'icon', 'apple-touch-icon', 'shortcut icon'].some((r) => rel.includes(r))) {
        if (href.startsWith('/') && !href.startsWith('//')) {
          const localFile = path.join(distDir, href.replace(/^\//, ''));
          if (!existsSync(localFile)) {
            errors.push(`Referenced <link rel="${rel}"> asset not found on disk: ${href}`);
          }
        }
      }
    }
  }

  // 9. Check <img> assets on disk
  if (distDir) {
    const images = doc.querySelectorAll('img');
    for (const img of images) {
      const src = img.getAttribute('src') || '';
      if (src.startsWith('/') && !src.startsWith('//')) {
        const localFile = path.join(distDir, src.replace(/^\//, ''));
        if (!existsSync(localFile)) {
          errors.push(`Image src not found on disk: ${src}`);
        }
      }
    }
  }

  return errors;
}

export function validateSitemapXml(xml, allowedUrls = ALLOWED_SITEMAP_URLS) {
  const errors = [];
  let doc;

  try {
    const dom = new JSDOM(xml, { contentType: 'text/xml' });
    doc = dom.window.document;
    const parserError = doc.querySelector('parsererror');
    if (parserError) {
      errors.push(`Invalid XML in sitemap.xml: ${parserError.textContent.trim()}`);
      return errors;
    }
  } catch (err) {
    errors.push(`XML parse error: ${err.message}`);
    return errors;
  }

  // Validate root element
  const root = doc.documentElement;
  if (!root || root.tagName.toLowerCase() !== 'urlset') {
    errors.push(`Invalid sitemap root element: expected '<urlset>', found '<${root ? root.tagName.toLowerCase() : 'null'}>'`);
    return errors;
  }

  // Validate xmlns namespace
  const xmlns = root.getAttribute('xmlns');
  if (xmlns !== 'http://www.sitemaps.org/schemas/sitemap/0.9') {
    errors.push(`Invalid sitemap xmlns namespace: expected 'http://www.sitemaps.org/schemas/sitemap/0.9', found '${xmlns}'`);
  }

  const locs = Array.from(doc.querySelectorAll('url > loc'));
  if (locs.length === 0) {
    errors.push('sitemap.xml contains no <url><loc> entries');
    return errors;
  }

  const extractedUrls = [];
  const seenUrls = new Set();

  for (const l of locs) {
    const url = l.textContent.trim();
    if (seenUrls.has(url)) {
      errors.push(`Duplicate URL found in sitemap.xml: ${url}`);
    }
    seenUrls.add(url);
    extractedUrls.push(url);

    // Reject non-HTTPS
    if (!url.startsWith('https://')) {
      errors.push(`HTTP or non-HTTPS URL in sitemap: ${url}`);
    }

    // Reject non-canonical domain
    if (!url.startsWith('https://www.dentixs.app/')) {
      errors.push(`Non-canonical domain in sitemap: ${url}`);
    }

    // Reject trailing slash variants of clean paths
    if (url.endsWith('/') && url !== 'https://www.dentixs.app/') {
      errors.push(`Trailing slash discrepancy in sitemap: ${url}`);
    }

    // Reject application-only or protected paths
    const pathname = new URL(url).pathname;
    if (APPLICATION_SHELL_ROUTES.includes(pathname)) {
      errors.push(`Application shell route illegally included in sitemap: ${url}`);
    }
    if (PROTECTED_ROUTES.some((pr) => pathname === pr || pathname.startsWith(`${pr}/`))) {
      errors.push(`Protected application route illegally included in sitemap: ${url}`);
    }
    if (REDIRECT_ONLY_ROUTES.includes(pathname)) {
      errors.push(`Redirect-only route illegally included in sitemap: ${url}`);
    }
  }

  // Check for disallowed/unexpected URLs
  for (const url of seenUrls) {
    if (!allowedUrls.has(url)) {
      errors.push(`Disallowed or unexpected URL in sitemap.xml: ${url}`);
    }
  }

  // Check for missing required URLs
  for (const expectedUrl of allowedUrls) {
    if (!seenUrls.has(expectedUrl)) {
      errors.push(`Required URL missing from sitemap.xml: ${expectedUrl}`);
    }
  }

  return errors;
}

export function validateRobotsTxt(robotsTxt) {
  const errors = [];
  const lines = robotsTxt.split(/\r?\n/).map((l) => l.trim()).filter((l) => l && !l.startsWith('#'));
  const groups = [];
  let current = { userAgents: [], disallows: [], allows: [], sitemaps: [] };

  for (const line of lines) {
    const idx = line.indexOf(':');
    if (idx === -1) continue;
    const key = line.slice(0, idx).trim().toLowerCase();
    const val = line.slice(idx + 1).trim();

    if (key === 'user-agent') {
      if (current.disallows.length > 0 || current.allows.length > 0) {
        groups.push(current);
        current = { userAgents: [], disallows: [], allows: [], sitemaps: [] };
      }
      current.userAgents.push(val);
    } else if (key === 'disallow') {
      current.disallows.push(val);
    } else if (key === 'allow') {
      current.allows.push(val);
    } else if (key === 'sitemap') {
      current.sitemaps.push(val);
    }
  }
  if (current.userAgents.length > 0 || current.disallows.length > 0 || current.sitemaps.length > 0) {
    groups.push(current);
  }

  const wildcard = groups.find((g) => g.userAgents.includes('*'));
  if (!wildcard) {
    errors.push('robots.txt missing User-agent: * section');
  } else {
    for (const g of groups) {
      if (g.disallows.some((p) => p === '/' || p === '/*')) {
        errors.push(`robots.txt blocks full site crawling with 'Disallow: /' for user-agent(s): ${g.userAgents.join(', ')}`);
      }
      if (g.disallows.some((p) => p === '/ar' || p.startsWith('/ar/'))) {
        errors.push(`robots.txt blocks marketing route /ar for user-agent(s): ${g.userAgents.join(', ')}`);
      }
      if (g.disallows.some((p) => p === '/en' || p.startsWith('/en/'))) {
        errors.push(`robots.txt blocks marketing route /en for user-agent(s): ${g.userAgents.join(', ')}`);
      }
      if (g.disallows.some((p) => p === '/marketing' || p.startsWith('/marketing/'))) {
        errors.push(`robots.txt blocks marketing assets for user-agent(s): ${g.userAgents.join(', ')}`);
      }
    }

    if (!wildcard.disallows.includes('/api/')) {
      errors.push("robots.txt User-agent: * must include 'Disallow: /api/'");
    }
  }

  const allSitemaps = groups.flatMap((g) => g.sitemaps);
  if (!allSitemaps.includes('https://www.dentixs.app/sitemap.xml')) {
    errors.push("robots.txt missing 'Sitemap: https://www.dentixs.app/sitemap.xml'");
  }

  return errors;
}

export function validateCssBudget(cssContent, maxGzipBytes = 25 * 1024) {
  const errors = [];
  const gzipped = gzipSync(Buffer.from(cssContent, 'utf8'));
  if (gzipped.length > maxGzipBytes) {
    errors.push(`marketing.css exceeds gzip budget: ${gzipped.length} bytes > ${maxGzipBytes} bytes`);
  }
  return { errors, gzipBytes: gzipped.length, rawBytes: cssContent.length };
}

export function validatePrecacheExclusions(swContent) {
  const errors = [];
  if (
    swContent.includes('ar/index.html') ||
    swContent.includes('"ar/index') ||
    swContent.includes('en/index.html') ||
    swContent.includes('"en/index') ||
    swContent.includes('marketing/marketing.css')
  ) {
    errors.push('sw.js precache manifest illegally contains marketing artifacts (ar/**, en/**, or marketing/**)');
  }
  return errors;
}

export function validateApplicationShellNoindex(indexHtmlContent) {
  const errors = [];
  const dom = new JSDOM(indexHtmlContent);
  const doc = dom.window.document;
  const robotsMeta = doc.querySelector('meta[name="robots"]');
  if (!robotsMeta) {
    errors.push('Application shell /index.html is missing <meta name="robots">');
  } else {
    const content = robotsMeta.getAttribute('content') || '';
    if (!content.includes('noindex')) {
      errors.push(`Application shell /index.html must include 'noindex' in meta robots, found: '${content}'`);
    }
  }
  return errors;
}

export function runVerification(distDir = 'dist') {
  const resolvedDist = path.resolve(distDir);
  console.log(`[verify-marketing] Inspecting build output at: ${resolvedDist}`);

  if (!existsSync(resolvedDist)) {
    console.error(`[verify-marketing] Error: Dist directory does not exist: ${resolvedDist}`);
    process.exit(1);
  }

  const allErrors = [];

  // Required files
  const requiredFiles = [
    'index.html',
    'ar/index.html',
    'en/index.html',
    'ar/privacy/index.html',
    'en/privacy/index.html',
    'ar/terms/index.html',
    'en/terms/index.html',
    'ar/about/index.html',
    'en/about/index.html',
    'ar/contact/index.html',
    'en/contact/index.html',
    'ar/plans/index.html',
    'en/plans/index.html',
    'ar/dental-clinic-management-software/index.html',
    'en/dental-clinic-management-software/index.html',
    'ar/dental-patient-records/index.html',
    'en/dental-patient-records/index.html',
    'ar/appointments-finance/index.html',
    'en/appointments-finance/index.html',
    'marketing/marketing.css',
    'robots.txt',
    'sitemap.xml',
    'sw.js',
  ];
  for (const rel of requiredFiles) {
    if (!existsSync(path.join(resolvedDist, rel))) {
      allErrors.push(`Missing required artifact: ${rel}`);
    }
  }

  if (allErrors.length > 0) {
    console.error('[verify-marketing] Missing files:\n' + allErrors.join('\n'));
    process.exit(1);
  }

  // 0. Validate Application Shell Noindex
  const appIndexHtml = readFileSync(path.join(resolvedDist, 'index.html'), 'utf8');
  allErrors.push(...validateApplicationShellNoindex(appIndexHtml));

  // 1. Validate Arabic Homepage
  const arHtml = readFileSync(path.join(resolvedDist, 'ar/index.html'), 'utf8');
  allErrors.push(...validateMarketingHtml(arHtml, resolvedDist, {
    lang: 'ar',
    dir: 'rtl',
    canonical: 'https://www.dentixs.app/ar',
    loginTexts: ['تسجيل الدخول'],
    targetLangSwitch: '/en',
    expectedAlternates: {
      ar: 'https://www.dentixs.app/ar',
      en: 'https://www.dentixs.app/en',
      'x-default': 'https://www.dentixs.app/ar',
    },
  }));

  // 2. Validate English Homepage
  const enHtml = readFileSync(path.join(resolvedDist, 'en/index.html'), 'utf8');
  allErrors.push(...validateMarketingHtml(enHtml, resolvedDist, {
    lang: 'en',
    dir: 'ltr',
    canonical: 'https://www.dentixs.app/en',
    loginTexts: ['log in', 'login'],
    targetLangSwitch: '/ar',
    expectedAlternates: {
      ar: 'https://www.dentixs.app/ar',
      en: 'https://www.dentixs.app/en',
      'x-default': 'https://www.dentixs.app/ar',
    },
  }));

  // 3. Validate Arabic Privacy
  const arPrivacyHtml = readFileSync(path.join(resolvedDist, 'ar/privacy/index.html'), 'utf8');
  allErrors.push(...validateMarketingHtml(arPrivacyHtml, resolvedDist, {
    lang: 'ar',
    dir: 'rtl',
    canonical: 'https://www.dentixs.app/ar/privacy',
    loginTexts: ['تسجيل الدخول'],
    targetLangSwitch: '/en/privacy',
    expectedAlternates: {
      ar: 'https://www.dentixs.app/ar/privacy',
      en: 'https://www.dentixs.app/en/privacy',
      'x-default': 'https://www.dentixs.app/ar/privacy',
    },
  }));

  // 4. Validate English Privacy
  const enPrivacyHtml = readFileSync(path.join(resolvedDist, 'en/privacy/index.html'), 'utf8');
  allErrors.push(...validateMarketingHtml(enPrivacyHtml, resolvedDist, {
    lang: 'en',
    dir: 'ltr',
    canonical: 'https://www.dentixs.app/en/privacy',
    loginTexts: ['log in', 'login'],
    targetLangSwitch: '/ar/privacy',
    expectedAlternates: {
      ar: 'https://www.dentixs.app/ar/privacy',
      en: 'https://www.dentixs.app/en/privacy',
      'x-default': 'https://www.dentixs.app/ar/privacy',
    },
  }));

  // 5. Validate Arabic Terms
  const arTermsHtml = readFileSync(path.join(resolvedDist, 'ar/terms/index.html'), 'utf8');
  allErrors.push(...validateMarketingHtml(arTermsHtml, resolvedDist, {
    lang: 'ar',
    dir: 'rtl',
    canonical: 'https://www.dentixs.app/ar/terms',
    loginTexts: ['تسجيل الدخول'],
    targetLangSwitch: '/en/terms',
    expectedAlternates: {
      ar: 'https://www.dentixs.app/ar/terms',
      en: 'https://www.dentixs.app/en/terms',
      'x-default': 'https://www.dentixs.app/ar/terms',
    },
  }));

  // 6. Validate English Terms
  const enTermsHtml = readFileSync(path.join(resolvedDist, 'en/terms/index.html'), 'utf8');
  allErrors.push(...validateMarketingHtml(enTermsHtml, resolvedDist, {
    lang: 'en',
    dir: 'ltr',
    canonical: 'https://www.dentixs.app/en/terms',
    loginTexts: ['log in', 'login'],
    targetLangSwitch: '/ar/terms',
    expectedAlternates: {
      ar: 'https://www.dentixs.app/ar/terms',
      en: 'https://www.dentixs.app/en/terms',
      'x-default': 'https://www.dentixs.app/ar/terms',
    },
  }));

  // 7. Validate Arabic About
  const arAboutHtml = readFileSync(path.join(resolvedDist, 'ar/about/index.html'), 'utf8');
  allErrors.push(...validateMarketingHtml(arAboutHtml, resolvedDist, {
    lang: 'ar',
    dir: 'rtl',
    canonical: 'https://www.dentixs.app/ar/about',
    loginTexts: ['تسجيل الدخول'],
    targetLangSwitch: '/en/about',
    expectedAlternates: {
      ar: 'https://www.dentixs.app/ar/about',
      en: 'https://www.dentixs.app/en/about',
      'x-default': 'https://www.dentixs.app/ar/about',
    },
  }));

  // 8. Validate English About
  const enAboutHtml = readFileSync(path.join(resolvedDist, 'en/about/index.html'), 'utf8');
  allErrors.push(...validateMarketingHtml(enAboutHtml, resolvedDist, {
    lang: 'en',
    dir: 'ltr',
    canonical: 'https://www.dentixs.app/en/about',
    loginTexts: ['log in', 'login'],
    targetLangSwitch: '/ar/about',
    expectedAlternates: {
      ar: 'https://www.dentixs.app/ar/about',
      en: 'https://www.dentixs.app/en/about',
      'x-default': 'https://www.dentixs.app/ar/about',
    },
  }));

  // 9. Validate Arabic Contact
  const arContactHtml = readFileSync(path.join(resolvedDist, 'ar/contact/index.html'), 'utf8');
  allErrors.push(...validateMarketingHtml(arContactHtml, resolvedDist, {
    lang: 'ar',
    dir: 'rtl',
    canonical: 'https://www.dentixs.app/ar/contact',
    loginTexts: ['تسجيل الدخول'],
    targetLangSwitch: '/en/contact',
    expectedAlternates: {
      ar: 'https://www.dentixs.app/ar/contact',
      en: 'https://www.dentixs.app/en/contact',
      'x-default': 'https://www.dentixs.app/ar/contact',
    },
  }));

  // 10. Validate English Contact
  const enContactHtml = readFileSync(path.join(resolvedDist, 'en/contact/index.html'), 'utf8');
  allErrors.push(...validateMarketingHtml(enContactHtml, resolvedDist, {
    lang: 'en',
    dir: 'ltr',
    canonical: 'https://www.dentixs.app/en/contact',
    loginTexts: ['log in', 'login'],
    targetLangSwitch: '/ar/contact',
    expectedAlternates: {
      ar: 'https://www.dentixs.app/ar/contact',
      en: 'https://www.dentixs.app/en/contact',
      'x-default': 'https://www.dentixs.app/ar/contact',
    },
  }));

  // 11. Validate Arabic Plans
  const arPlansHtml = readFileSync(path.join(resolvedDist, 'ar/plans/index.html'), 'utf8');
  allErrors.push(...validateMarketingHtml(arPlansHtml, resolvedDist, {
    lang: 'ar',
    dir: 'rtl',
    canonical: 'https://www.dentixs.app/ar/plans',
    loginTexts: ['تسجيل الدخول'],
    targetLangSwitch: '/en/plans',
    expectedAlternates: {
      ar: 'https://www.dentixs.app/ar/plans',
      en: 'https://www.dentixs.app/en/plans',
      'x-default': 'https://www.dentixs.app/ar/plans',
    },
  }));

  // 12. Validate English Plans
  const enPlansHtml = readFileSync(path.join(resolvedDist, 'en/plans/index.html'), 'utf8');
  allErrors.push(...validateMarketingHtml(enPlansHtml, resolvedDist, {
    lang: 'en',
    dir: 'ltr',
    canonical: 'https://www.dentixs.app/en/plans',
    loginTexts: ['log in', 'login'],
    targetLangSwitch: '/ar/plans',
    expectedAlternates: {
      ar: 'https://www.dentixs.app/ar/plans',
      en: 'https://www.dentixs.app/en/plans',
      'x-default': 'https://www.dentixs.app/ar/plans',
    },
  }));

  // 13. Validate Arabic Dental Clinic Management Software Guide
  const arClinicGuideHtml = readFileSync(path.join(resolvedDist, 'ar/dental-clinic-management-software/index.html'), 'utf8');
  allErrors.push(...validateMarketingHtml(arClinicGuideHtml, resolvedDist, {
    lang: 'ar',
    dir: 'rtl',
    canonical: 'https://www.dentixs.app/ar/dental-clinic-management-software',
    loginTexts: ['تسجيل الدخول'],
    targetLangSwitch: '/en/dental-clinic-management-software',
    expectedAlternates: {
      ar: 'https://www.dentixs.app/ar/dental-clinic-management-software',
      en: 'https://www.dentixs.app/en/dental-clinic-management-software',
      'x-default': 'https://www.dentixs.app/ar/dental-clinic-management-software',
    },
  }));

  // 14. Validate English Dental Clinic Management Software Guide
  const enClinicGuideHtml = readFileSync(path.join(resolvedDist, 'en/dental-clinic-management-software/index.html'), 'utf8');
  allErrors.push(...validateMarketingHtml(enClinicGuideHtml, resolvedDist, {
    lang: 'en',
    dir: 'ltr',
    canonical: 'https://www.dentixs.app/en/dental-clinic-management-software',
    loginTexts: ['log in', 'login'],
    targetLangSwitch: '/ar/dental-clinic-management-software',
    expectedAlternates: {
      ar: 'https://www.dentixs.app/ar/dental-clinic-management-software',
      en: 'https://www.dentixs.app/en/dental-clinic-management-software',
      'x-default': 'https://www.dentixs.app/ar/dental-clinic-management-software',
    },
  }));

  // 15. Validate Arabic Dental Patient Records Guide
  const arPatientRecordsHtml = readFileSync(path.join(resolvedDist, 'ar/dental-patient-records/index.html'), 'utf8');
  allErrors.push(...validateMarketingHtml(arPatientRecordsHtml, resolvedDist, {
    lang: 'ar',
    dir: 'rtl',
    canonical: 'https://www.dentixs.app/ar/dental-patient-records',
    loginTexts: ['تسجيل الدخول'],
    targetLangSwitch: '/en/dental-patient-records',
    expectedAlternates: {
      ar: 'https://www.dentixs.app/ar/dental-patient-records',
      en: 'https://www.dentixs.app/en/dental-patient-records',
      'x-default': 'https://www.dentixs.app/ar/dental-patient-records',
    },
  }));

  // 16. Validate English Dental Patient Records Guide
  const enPatientRecordsHtml = readFileSync(path.join(resolvedDist, 'en/dental-patient-records/index.html'), 'utf8');
  allErrors.push(...validateMarketingHtml(enPatientRecordsHtml, resolvedDist, {
    lang: 'en',
    dir: 'ltr',
    canonical: 'https://www.dentixs.app/en/dental-patient-records',
    loginTexts: ['log in', 'login'],
    targetLangSwitch: '/ar/dental-patient-records',
    expectedAlternates: {
      ar: 'https://www.dentixs.app/ar/dental-patient-records',
      en: 'https://www.dentixs.app/en/dental-patient-records',
      'x-default': 'https://www.dentixs.app/ar/dental-patient-records',
    },
  }));

  // 17. Validate Arabic Appointments & Finance Guide
  const arApptFinanceHtml = readFileSync(path.join(resolvedDist, 'ar/appointments-finance/index.html'), 'utf8');
  allErrors.push(...validateMarketingHtml(arApptFinanceHtml, resolvedDist, {
    lang: 'ar',
    dir: 'rtl',
    canonical: 'https://www.dentixs.app/ar/appointments-finance',
    loginTexts: ['تسجيل الدخول'],
    targetLangSwitch: '/en/appointments-finance',
    expectedAlternates: {
      ar: 'https://www.dentixs.app/ar/appointments-finance',
      en: 'https://www.dentixs.app/en/appointments-finance',
      'x-default': 'https://www.dentixs.app/ar/appointments-finance',
    },
  }));

  // 18. Validate English Appointments & Finance Guide
  const enApptFinanceHtml = readFileSync(path.join(resolvedDist, 'en/appointments-finance/index.html'), 'utf8');
  allErrors.push(...validateMarketingHtml(enApptFinanceHtml, resolvedDist, {
    lang: 'en',
    dir: 'ltr',
    canonical: 'https://www.dentixs.app/en/appointments-finance',
    loginTexts: ['log in', 'login'],
    targetLangSwitch: '/ar/appointments-finance',
    expectedAlternates: {
      ar: 'https://www.dentixs.app/ar/appointments-finance',
      en: 'https://www.dentixs.app/en/appointments-finance',
      'x-default': 'https://www.dentixs.app/ar/appointments-finance',
    },
  }));

  // 19. Validate Sitemap
  const sitemapXml = readFileSync(path.join(resolvedDist, 'sitemap.xml'), 'utf8');
  allErrors.push(...validateSitemapXml(sitemapXml));

  // 8. Validate Robots.txt
  const robotsTxt = readFileSync(path.join(resolvedDist, 'robots.txt'), 'utf8');
  allErrors.push(...validateRobotsTxt(robotsTxt));

  // 9. Validate CSS Budget
  const cssContent = readFileSync(path.join(resolvedDist, 'marketing/marketing.css'), 'utf8');
  const cssResult = validateCssBudget(cssContent);
  allErrors.push(...cssResult.errors);
  console.log(`[verify-marketing] marketing.css raw size: ${(cssResult.rawBytes / 1024).toFixed(2)} KiB, gzip: ${(cssResult.gzipBytes / 1024).toFixed(2)} KiB`);

  // 10. Validate Precache
  const swContent = readFileSync(path.join(resolvedDist, 'sw.js'), 'utf8');
  allErrors.push(...validatePrecacheExclusions(swContent));

  if (allErrors.length > 0) {
    console.error('\n[verify-marketing] Validation FAILED with errors:');
    for (const err of allErrors) {
      console.error(`  - ${err}`);
    }
    process.exit(1);
  }

  console.log('[verify-marketing] All marketing artifact checks PASSED successfully (strict semantic parsing).');
}

// CLI entry point
const isCli = process.argv[1] && fileURLToPath(import.meta.url) === path.resolve(process.argv[1]);
if (isCli) {
  runVerification(process.argv[2] || 'dist');
}
