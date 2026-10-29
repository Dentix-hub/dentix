#!/usr/bin/env node
/**
 * verify-vercel-preview-routes.mjs
 * Independent HTTP route verification for Vercel Preview deployment.
 * Validates clean URLs, 308 redirects, 404 fallthroughs, and security headers.
 * Zero state modification / Zero database mutations.
 *
 * Usage:
 *   node scripts/verify-vercel-preview-routes.mjs <DEPLOYMENT_URL>
 * Example:
 *   node scripts/verify-vercel-preview-routes.mjs https://dentix-preview.vercel.app
 */

const targetUrl = process.argv[2] || process.env.VERCEL_PREVIEW_URL;

if (!targetUrl) {
  console.log(`
[verify-vercel-preview] Usage: node scripts/verify-vercel-preview-routes.mjs <URL>
No URL provided. Set VERCEL_PREVIEW_URL or pass the deployment URL as the first argument.
This script performs non-mutating HTTP assertions (GET/HEAD only) against the deployment.
`);
  process.exit(1);
}

const baseUrl = targetUrl.replace(/\/+$/, '');
console.log(`[verify-vercel-preview] Target deployment: ${baseUrl}`);

async function checkRoute(description, path, expected) {
  const url = `${baseUrl}${path}`;
  const result = { description, path, passed: true, details: [] };

  try {
    const res = await fetch(url, { redirect: 'manual' });

    // Check status
    if (expected.status !== undefined && res.status !== expected.status) {
      result.passed = false;
      result.details.push(`Status mismatch: expected ${expected.status}, got ${res.status}`);
    }

    // Check redirect Location header
    if (expected.location !== undefined) {
      const loc = res.headers.get('location') || '';
      if (!loc.endsWith(expected.location)) {
        result.passed = false;
        result.details.push(`Location mismatch: expected ending with '${expected.location}', got '${loc}'`);
      }
    }

    // Check Content-Type header
    if (expected.contentType !== undefined) {
      const ct = res.headers.get('content-type') || '';
      if (!ct.includes(expected.contentType)) {
        result.passed = false;
        result.details.push(`Content-Type mismatch: expected '${expected.contentType}', got '${ct}'`);
      }
    }

    // Check body content if required
    if (expected.bodyContains !== undefined) {
      const body = await res.text();
      for (const expectedText of expected.bodyContains) {
        if (!body.includes(expectedText)) {
          result.passed = false;
          result.details.push(`Body missing required text: '${expectedText}'`);
        }
      }
      if (expected.bodyNotContains !== undefined) {
        for (const notExpected of expected.bodyNotContains) {
          if (body.includes(notExpected)) {
            result.passed = false;
            result.details.push(`Body illegally contains text: '${notExpected}'`);
          }
        }
      }
    }

    // Check headers
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

const routeTests = [
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
      bodyContains: [
        '<html lang="ar" dir="rtl">',
        'إدارة عيادة الأسنان من مكان واحد.',
        'https://www.dentixs.app/ar',
      ],
      bodyNotContains: ['registerSW', 'assets/index-'],
    },
  },
  {
    desc: 'Trailing slash /ar/ redirects with 308 to /ar',
    path: '/ar/',
    expected: { status: 308, location: '/ar' },
  },
  {
    desc: '/ar/index.html redirects with 308 to /ar',
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
    desc: '/robots.txt is served as plain text (HTTP 200)',
    path: '/robots.txt',
    expected: {
      status: 200,
      bodyContains: ['User-agent: *', 'Disallow: /api/', 'Sitemap: https://www.dentixs.app/sitemap.xml'],
      bodyNotContains: ['<!DOCTYPE', '<html'],
    },
  },
  {
    desc: '/sitemap.xml is served as valid XML containing only /ar (HTTP 200)',
    path: '/sitemap.xml',
    expected: {
      status: 200,
      bodyContains: ['<loc>https://www.dentixs.app/ar</loc>'],
      bodyNotContains: ['/patients', '/login', '/api/'],
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
];

async function main() {
  console.log(`\nExecuting ${routeTests.length} HTTP route contract assertions...\n`);
  let passedCount = 0;
  let failedCount = 0;

  for (const t of routeTests) {
    const res = await checkRoute(t.desc, t.path, t.expected);
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

main();
