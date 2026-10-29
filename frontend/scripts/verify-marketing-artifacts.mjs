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

export const ALLOWED_SITEMAP_URLS = new Set([
  'https://www.dentixs.app/ar',
]);

export function validateMarketingHtml(html, distDir = null) {
  const errors = [];
  const dom = new JSDOM(html);
  const doc = dom.window.document;

  // 1. Language & Direction
  const htmlEl = doc.documentElement;
  if (htmlEl.getAttribute('lang') !== 'ar') {
    errors.push(`<html> attribute lang must be 'ar', found: '${htmlEl.getAttribute('lang')}'`);
  }
  if (htmlEl.getAttribute('dir') !== 'rtl') {
    errors.push(`<html> attribute dir must be 'rtl', found: '${htmlEl.getAttribute('dir')}'`);
  }

  // 2. Canonical URL
  const canonical = doc.querySelector('link[rel="canonical"]');
  if (!canonical || canonical.getAttribute('href') !== 'https://www.dentixs.app/ar') {
    errors.push(`Missing or invalid canonical link: expected 'https://www.dentixs.app/ar', found: '${canonical ? canonical.getAttribute('href') : 'none'}'`);
  }

  // 3. Executable Script Guard (Zero JS execution)
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

  // 4. Inline Event Handlers Guard
  const allElements = doc.querySelectorAll('*');
  for (const el of allElements) {
    for (const attr of el.attributes) {
      if (attr.name.toLowerCase().startsWith('on')) {
        errors.push(`Inline event handler attribute found on <${el.tagName.toLowerCase()}>: ${attr.name}="${attr.value}"`);
      }
    }
  }

  // 5. Manifest & SW Links
  if (doc.querySelector('link[rel="manifest"]')) {
    errors.push('ar/index.html illegally contains PWA manifest link');
  }

  // 6. Action Links: Login must point to / (never /login)
  const links = doc.querySelectorAll('a');
  let loginCount = 0;
  for (const link of links) {
    const href = link.getAttribute('href') || '';
    const text = link.textContent.trim();

    if (href.startsWith('javascript:')) {
      errors.push(`Executable javascript: pseudo-protocol found in link: ${href}`);
    }

    if (text.includes('تسجيل الدخول')) {
      loginCount++;
      if (href !== '/') {
        errors.push(`Login link must point to '/', found '${href}'`);
      }
    }

    if (href === '/login' || href.startsWith('/login?')) {
      errors.push(`Direct link to /login found: '${href}'`);
    }

    // Local static file check if distDir provided
    if (distDir && href.startsWith('/') && !href.startsWith('//') && href.includes('.')) {
      const localFile = path.join(distDir, href.replace(/^\//, ''));
      if (!existsSync(localFile)) {
        errors.push(`Broken local asset link in ar/index.html: ${href}`);
      }
    }
  }

  if (loginCount < 2) {
    errors.push(`Expected at least 2 login links pointing to '/', found ${loginCount}`);
  }

  // 7. Check image assets on disk
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

  const locs = Array.from(doc.querySelectorAll('url > loc'));
  if (locs.length === 0) {
    errors.push('sitemap.xml contains no <url><loc> entries');
    return errors;
  }

  for (const loc of locs) {
    const url = loc.textContent.trim();
    if (!allowedUrls.has(url)) {
      errors.push(`Disallowed or unexpected URL in sitemap.xml: ${url}`);
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
  if (swContent.includes('ar/index.html') || swContent.includes('"ar/index') || swContent.includes('marketing/marketing.css')) {
    errors.push('sw.js precache manifest illegally contains marketing artifacts (ar/** or marketing/**)');
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
  const requiredFiles = ['ar/index.html', 'marketing/marketing.css', 'robots.txt', 'sitemap.xml', 'sw.js'];
  for (const rel of requiredFiles) {
    if (!existsSync(path.join(resolvedDist, rel))) {
      allErrors.push(`Missing required artifact: ${rel}`);
    }
  }

  if (allErrors.length > 0) {
    console.error('[verify-marketing] Missing files:\n' + allErrors.join('\n'));
    process.exit(1);
  }

  // 1. Validate HTML
  const arHtml = readFileSync(path.join(resolvedDist, 'ar/index.html'), 'utf8');
  allErrors.push(...validateMarketingHtml(arHtml, resolvedDist));

  // 2. Validate Sitemap
  const sitemapXml = readFileSync(path.join(resolvedDist, 'sitemap.xml'), 'utf8');
  allErrors.push(...validateSitemapXml(sitemapXml));

  // 3. Validate Robots.txt
  const robotsTxt = readFileSync(path.join(resolvedDist, 'robots.txt'), 'utf8');
  allErrors.push(...validateRobotsTxt(robotsTxt));

  // 4. Validate CSS Budget
  const cssContent = readFileSync(path.join(resolvedDist, 'marketing/marketing.css'), 'utf8');
  const cssResult = validateCssBudget(cssContent);
  allErrors.push(...cssResult.errors);
  console.log(`[verify-marketing] marketing.css raw size: ${(cssResult.rawBytes / 1024).toFixed(2)} KiB, gzip: ${(cssResult.gzipBytes / 1024).toFixed(2)} KiB`);

  // 5. Validate Precache
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
