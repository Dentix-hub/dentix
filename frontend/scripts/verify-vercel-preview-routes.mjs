#!/usr/bin/env node
/**
 * verify-vercel-preview-routes.mjs
 * Independent HTTP route verification for Vercel Preview deployment.
 * Validates clean URLs, 308 redirects (with strict origin/pathname comparison),
 * strict content-types, 404 fallthroughs, and semantic AST/XML validation.
 * Zero state modification / Zero database mutations.
 *
 * Usage:
 *   node scripts/verify-vercel-preview-routes.mjs <DEPLOYMENT_URL>
 * Example:
 *   node scripts/verify-vercel-preview-routes.mjs https://dentix-preview.vercel.app
 */

import {
  validateMarketingHtml,
  validateSitemapXml,
  validateRobotsTxt,
} from './verify-marketing-artifacts.mjs';

const targetUrl = process.argv[2] || process.env.VERCEL_PREVIEW_URL || 'http://localhost:3000';
const baseUrl = targetUrl.replace(/\/+$/, '');
const expectedOrigin = new URL(baseUrl).origin;

export async function checkRoute(description, path, expected, deploymentBaseUrl = baseUrl) {
  const currentBase = deploymentBaseUrl.replace(/\/+$/, '');
  const origin = new URL(currentBase).origin;
  const url = `${currentBase}${path}`;
  const result = { description, path, passed: true, details: [] };

  try {
    const res = await fetch(url, { redirect: 'manual' });

    // 1. Check HTTP status code
    if (expected.status !== undefined && res.status !== expected.status) {
      result.passed = false;
      result.details.push(`Status mismatch: expected ${expected.status}, got ${res.status}`);
    }

    // 2. Strict Redirect Location validation (origin + pathname)
    if (expected.location !== undefined) {
      const locHeader = res.headers.get('location');
      if (!locHeader) {
        result.passed = false;
        result.details.push('Location header missing in redirect response');
      } else {
        try {
          const resolvedLoc = new URL(locHeader, currentBase);
          // Origin must match expected deployment origin (reject cross-domain open redirects)
          if (resolvedLoc.origin !== origin) {
            result.passed = false;
            result.details.push(`Location origin mismatch (cross-domain redirect rejected): expected '${origin}', got '${resolvedLoc.origin}'`);
          }
          // Pathname must match exact expected destination
          if (resolvedLoc.pathname !== expected.location) {
            result.passed = false;
            result.details.push(`Location pathname mismatch: expected '${expected.location}', got '${resolvedLoc.pathname}'`);
          }
        } catch (e) {
          result.passed = false;
          result.details.push(`Invalid Location URL header: '${locHeader}' (${e.message})`);
        }
      }
    }

    // 3. Strict Content-Type validation
    const ct = (res.headers.get('content-type') || '').toLowerCase();
    if (expected.contentType !== undefined) {
      if (!ct.includes(expected.contentType.toLowerCase())) {
        result.passed = false;
        result.details.push(`Content-Type mismatch: expected containing '${expected.contentType}', got '${ct}'`);
      }
    }
    if (expected.contentTypeNot !== undefined) {
      if (ct.includes(expected.contentTypeNot.toLowerCase())) {
        result.passed = false;
        result.details.push(`Content-Type illegally contains '${expected.contentTypeNot}': '${ct}'`);
      }
    }

    // 4. Body reading and semantic validation
    if (expected.validator || expected.bodyContains || expected.bodyNotContains) {
      const body = await res.text();

      if (expected.bodyContains) {
        for (const text of expected.bodyContains) {
          if (!body.includes(text)) {
            result.passed = false;
            result.details.push(`Body missing required text: '${text}'`);
          }
        }
      }

      if (expected.bodyNotContains) {
        for (const text of expected.bodyNotContains) {
          if (body.includes(text)) {
            result.passed = false;
            result.details.push(`Body illegally contains text: '${text}'`);
          }
        }
      }

      // Reuse semantic parsers
      if (expected.validator) {
        const valErrors = expected.validator(body);
        if (valErrors.length > 0) {
          result.passed = false;
          result.details.push(...valErrors);
        }
      }
    }

    // 5. Security headers
    if (expected.headers) {
      for (const [hKey, hVal] of Object.entries(expected.headers)) {
        const val = res.headers.get(hKey);
        if (val !== hVal) {
          result.passed = false;
          result.details.push(`Header '${hKey}' mismatch: expected '${hVal}', got '${val}'`);
        }
      }
    }
  } catch (err) {
    result.passed = false;
    result.details.push(`Fetch failed: ${err.message}`);
  }

  return result;
}

export const routeTests = [
  {
    desc: 'Root / serves SPA application entry (HTTP 200)',
    path: '/',
    expected: { status: 200, contentType: 'text/html' },
  },
  {
    desc: 'Clean /ar serves Arabic static landing page (HTTP 200)',
    path: '/ar',
    expected: {
      status: 200,
      contentType: 'text/html',
      validator: (html) => validateMarketingHtml(html, null, {
        lang: 'ar',
        dir: 'rtl',
        canonical: 'https://www.dentixs.app/ar',
        loginTexts: ['تسجيل الدخول'],
        targetLangSwitch: '/en',
      }),
    },
  },
  {
    desc: 'Trailing slash /ar/ redirects with 308 to /ar on same origin',
    path: '/ar/',
    expected: { status: 308, location: '/ar' },
  },
  {
    desc: '/ar/index.html redirects with 308 to /ar on same origin',
    path: '/ar/index.html',
    expected: { status: 308, location: '/ar' },
  },
  {
    desc: '/ar with query parameters preserves canonical to /ar (HTTP 200)',
    path: '/ar?utm_source=preview_test',
    expected: {
      status: 200,
      contentType: 'text/html',
      bodyContains: ['<link rel="canonical" href="https://www.dentixs.app/ar">'],
    },
  },
  {
    desc: 'Unknown path /ar/unknown returns 404 (NOT 200 SPA login)',
    path: '/ar/unknown',
    expected: { status: 404 },
  },
  {
    desc: 'Clean /en serves English static landing page (HTTP 200)',
    path: '/en',
    expected: {
      status: 200,
      contentType: 'text/html',
      validator: (html) => validateMarketingHtml(html, null, {
        lang: 'en',
        dir: 'ltr',
        canonical: 'https://www.dentixs.app/en',
        loginTexts: ['log in', 'login'],
        targetLangSwitch: '/ar',
      }),
    },
  },
  {
    desc: 'Trailing slash /en/ redirects with 308 to /en on same origin',
    path: '/en/',
    expected: { status: 308, location: '/en' },
  },
  {
    desc: '/en/index.html redirects with 308 to /en on same origin',
    path: '/en/index.html',
    expected: { status: 308, location: '/en' },
  },
  {
    desc: '/en with query parameters preserves canonical to /en (HTTP 200)',
    path: '/en?utm_source=preview_test',
    expected: {
      status: 200,
      contentType: 'text/html',
      bodyContains: ['<link rel="canonical" href="https://www.dentixs.app/en">'],
    },
  },
  {
    desc: 'Unknown path /en/unknown returns 404 (NOT 200 SPA login)',
    path: '/en/unknown',
    expected: { status: 404 },
  },
  {
    desc: 'Marketing CSS is served with text/css (HTTP 200)',
    path: '/marketing/marketing.css',
    expected: { status: 200, contentType: 'text/css' },
  },
  {
    desc: 'Missing marketing asset returns 404 (NOT 200 SPA login)',
    path: '/marketing/nonexistent.css',
    expected: { status: 404 },
  },
  {
    desc: '/robots.txt is served as plain text (HTTP 200) and passes semantic robots validation',
    path: '/robots.txt',
    expected: {
      status: 200,
      contentType: 'text/plain',
      contentTypeNot: 'text/html',
      validator: (txt) => validateRobotsTxt(txt),
    },
  },
  {
    desc: '/sitemap.xml is served as XML (HTTP 200) and passes semantic XML validation',
    path: '/sitemap.xml',
    expected: {
      status: 200,
      contentType: 'xml',
      contentTypeNot: 'text/html',
      validator: (xml) => validateSitemapXml(xml),
    },
  },
  {
    desc: 'Security headers present on /ar',
    path: '/ar',
    expected: {
      headers: {
        'x-content-type-options': 'nosniff',
        'referrer-policy': 'strict-origin-when-cross-origin',
      },
    },
  },
  {
    desc: 'Security headers present on /en',
    path: '/en',
    expected: {
      headers: {
        'x-content-type-options': 'nosniff',
        'referrer-policy': 'strict-origin-when-cross-origin',
      },
    },
  },
];

async function main() {
  const cliUrl = process.argv[2] || process.env.VERCEL_PREVIEW_URL;
  if (!cliUrl) {
    console.log(`
[verify-vercel-preview] Usage: node scripts/verify-vercel-preview-routes.mjs <URL>
No URL provided. Set VERCEL_PREVIEW_URL or pass the deployment URL as the first argument.
This script performs non-mutating HTTP assertions (GET/HEAD only) against the deployment.
`);
    process.exit(1);
  }
  const currentBase = cliUrl.replace(/\/+$/, '');
  const currentOrigin = new URL(currentBase).origin;
  console.log(`[verify-vercel-preview] Target deployment: ${currentBase} (Origin: ${currentOrigin})`);

  console.log(`\nExecuting ${routeTests.length} HTTP route contract assertions...\n`);
  let passedCount = 0;
  let failedCount = 0;

  for (const t of routeTests) {
    const res = await checkRoute(t.desc, t.path, t.expected, currentBase);
    if (res.passed) {
      console.log(`  ✓ PASS: ${res.description}`);
      passedCount++;
    } else {
      console.error(`  ✗ FAIL: ${res.description}`);
      for (const d of res.details) {
        console.error(`      -> ${d}`);
      }
      failedCount++;
    }
  }

  console.log(`\nResults: ${passedCount} passed, ${failedCount} failed.`);
  if (failedCount > 0) {
    process.exit(1);
  }
}

const isCli = process.argv[1] && import.meta.url.endsWith(process.argv[1]);
if (isCli) {
  main();
}
