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

import { fileURLToPath } from 'node:url';
import path from 'node:path';
import { CURRENT_ACTIVE_INDEXABLE_ROUTES, APPLICATION_SHELL_ROUTES, PROTECTED_ROUTES, publicPageOptions } from './routeInventory.mjs';

import {
  validateApplicationShellNoindex,
  hasNoindexDirective,
  validateMarketingHtml,
  validateSitemapXml,
  validateRobotsTxt,
} from './verify-marketing-artifacts.mjs';

const targetUrl = process.argv[2] || process.env.VERCEL_PREVIEW_URL || 'http://localhost:3000';
const baseUrl = targetUrl.replace(/\/+$/, '');

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

    if (expected.indexable && hasNoindexDirective(res.headers.get('x-robots-tag') || '')) {
      result.passed = false;
      result.details.push('Public page is blocked by X-Robots-Tag noindex/none');
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

// Expected clean paths and aliases come from the public inventory, not from
// the deployment's rewrites: serving the SPA with HTTP 200 must fail.
export const routeTests = [
  ...CURRENT_ACTIVE_INDEXABLE_ROUTES.flatMap(canonical => {
    const pathname = new URL(canonical).pathname;
    return [
      {
        desc: `Public ${pathname} serves its indexable static page`,
        path: pathname,
        expected: {
          status: 200, contentType: 'text/html', indexable: true,
          validator: html => validateMarketingHtml(html, null, publicPageOptions(canonical)),
          headers: { 'x-content-type-options': 'nosniff', 'referrer-policy': 'strict-origin-when-cross-origin' },
        },
      },
      ...[`${pathname}/`, `${pathname}/index.html`].map(alias => ({
        desc: `${alias} redirects to its clean canonical path`,
        path: alias,
        expected: { status: 308, location: pathname },
      })),
      {
        desc: `${pathname} preserves canonical identity with query parameters`,
        path: `${pathname}?utm_source=preview_test`,
        expected: {
          status: 200, contentType: 'text/html', indexable: true,
          validator: html => validateMarketingHtml(html, null, publicPageOptions(canonical)),
        },
      },
    ];
  }),
  ...['privacy', 'terms'].flatMap(page => [`/${page}`, `/${page}/`].map(alias => ({
    desc: `Legacy ${alias} redirects to public legal content`,
    path: alias, expected: { status: 308, location: `/ar/${page}` },
  }))),
  ...[...APPLICATION_SHELL_ROUTES, ...PROTECTED_ROUTES].map(pathname => ({
    desc: `Application ${pathname} retains the noindexed SPA shell`,
    path: pathname,
    expected: { status: 200, contentType: 'text/html', validator: validateApplicationShellNoindex },
  })),
  ...['/ar/unknown', '/en/unknown', '/marketing/nonexistent.css'].map(pathname => ({
    desc: `Missing public resource ${pathname} returns 404`, path: pathname, expected: { status: 404 },
  })),
  { desc: 'Marketing CSS', path: '/marketing/marketing.css', expected: { status: 200, contentType: 'text/css' } },
  { desc: 'Robots policy', path: '/robots.txt', expected: { status: 200, contentType: 'text/plain', validator: validateRobotsTxt } },
  { desc: 'Sitemap', path: '/sitemap.xml', expected: { status: 200, contentType: 'xml', validator: validateSitemapXml } },
  { desc: 'API liveness stays JSON, outside the SPA', path: '/api/v1/health/live', expected: { status: 200, contentType: 'application/json', bodyContains: ['alive'] } },
  { desc: 'PWA service worker', path: '/sw.js', expected: { status: 200, contentType: 'javascript' } },
  { desc: 'PWA manifest', path: '/manifest.webmanifest', expected: { status: 200, contentTypeNot: 'text/html' } },
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

const isCli = process.argv[1] && fileURLToPath(import.meta.url) === path.resolve(process.argv[1]);
if (isCli) {
  main();
}
