#!/usr/bin/env node
/**
 * verify-marketing-artifacts.mjs
 * Validates production build artifacts for Dentix marketing and discovery assets.
 * Executes post-build without external dependencies.
 */
import { readFileSync, existsSync, statSync } from 'node:fs';
import path from 'node:path';
import { gzipSync } from 'node:zlib';

const distDir = path.resolve(process.argv[2] || 'dist');
console.log(`[verify-marketing] Inspecting build output at: ${distDir}`);

if (!existsSync(distDir)) {
    console.error(`[verify-marketing] Error: Dist directory does not exist: ${distDir}`);
    process.exit(1);
}

const errors = [];

// 1. Check required files exist
const requiredFiles = [
    'ar/index.html',
    'marketing/marketing.css',
    'robots.txt',
    'sitemap.xml',
    'sw.js',
];

for (const rel of requiredFiles) {
    const fullPath = path.join(distDir, rel);
    if (!existsSync(fullPath)) {
        errors.push(`Missing required artifact: ${rel}`);
    }
}

if (errors.length > 0) {
    console.error('[verify-marketing] Missing files:\n' + errors.join('\n'));
    process.exit(1);
}

// 2. Validate ar/index.html
const arHtml = readFileSync(path.join(distDir, 'ar/index.html'), 'utf8');

if (!arHtml.includes('<html lang="ar" dir="rtl">') && !arHtml.includes('<html dir="rtl" lang="ar">')) {
    errors.push('ar/index.html missing lang="ar" dir="rtl"');
}

if (!arHtml.includes('<link rel="canonical" href="https://www.dentixs.app/ar">')) {
    errors.push('ar/index.html missing or invalid canonical URL');
}

if (arHtml.includes('<script type="module"') || arHtml.includes('/assets/index-')) {
    errors.push('ar/index.html illegally includes React/SPA application script bundles');
}

if (arHtml.includes('navigator.serviceWorker') || arHtml.includes('registerSW')) {
    errors.push('ar/index.html illegally includes Service Worker registration');
}

if (arHtml.includes('manifest.webmanifest')) {
    errors.push('ar/index.html illegally links to PWA web manifest');
}

if (arHtml.includes('href="/login"') || arHtml.includes("href='/login'")) {
    errors.push('ar/index.html contains links to /login (login links must point to /)');
}

// Check local asset references exist in dist
const assetMatches = arHtml.matchAll(/(?:src|href)=["'](\/[a-zA-Z0-9_\-\.\/]+)["']/g);
for (const match of assetMatches) {
    const urlPath = match[1];
    // Skip external URLs or pure path links like /, /register, /terms, /privacy, /ar
    if (['/', '/ar', '/register', '/terms', '/privacy'].includes(urlPath)) {
        continue;
    }
    // Static asset file
    if (urlPath.includes('.')) {
        const localFilePath = path.join(distDir, urlPath.replace(/^\//, ''));
        if (!existsSync(localFilePath)) {
            errors.push(`ar/index.html references missing local asset: ${urlPath}`);
        }
    }
}

// 3. Validate marketing.css budget
const cssContent = readFileSync(path.join(distDir, 'marketing/marketing.css'), 'utf8');
const gzippedCss = gzipSync(Buffer.from(cssContent, 'utf8'));
const MAX_CSS_GZIP_BYTES = 25 * 1024; // 25 KiB budget
console.log(`[verify-marketing] marketing.css raw size: ${(cssContent.length / 1024).toFixed(2)} KiB, gzip: ${(gzippedCss.length / 1024).toFixed(2)} KiB`);

if (gzippedCss.length > MAX_CSS_GZIP_BYTES) {
    errors.push(`marketing.css exceeds gzip budget: ${gzippedCss.length} bytes > ${MAX_CSS_GZIP_BYTES} bytes`);
}

// 4. Validate robots.txt
const robotsTxt = readFileSync(path.join(distDir, 'robots.txt'), 'utf8');
if (!robotsTxt.includes('User-agent: *') || !robotsTxt.includes('Disallow: /api/')) {
    errors.push('robots.txt missing User-agent or Disallow rules');
}
if (!robotsTxt.includes('Sitemap: https://www.dentixs.app/sitemap.xml')) {
    errors.push('robots.txt missing Sitemap declaration');
}

// 5. Validate sitemap.xml
const sitemapXml = readFileSync(path.join(distDir, 'sitemap.xml'), 'utf8');
if (!sitemapXml.includes('<loc>https://www.dentixs.app/ar</loc>')) {
    errors.push('sitemap.xml missing https://www.dentixs.app/ar entry');
}
if (sitemapXml.includes('/login') || sitemapXml.includes('/register') || sitemapXml.includes('/api')) {
    errors.push('sitemap.xml illegally contains private/app routes');
}

// 6. Validate sw.js precache excludes marketing artifacts
const swContent = readFileSync(path.join(distDir, 'sw.js'), 'utf8');
if (swContent.includes('ar/index.html') || swContent.includes('"ar/index') || swContent.includes('marketing/marketing.css')) {
    errors.push('sw.js precache manifest illegally contains marketing artifacts (ar/** or marketing/**)');
}

if (errors.length > 0) {
    console.error('\n[verify-marketing] Validation FAILED with errors:');
    for (const err of errors) {
        console.error(`  - ${err}`);
    }
    process.exit(1);
}

console.log('[verify-marketing] All marketing artifact checks PASSED successfully.');
