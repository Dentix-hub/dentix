/**
 * PR-PWA-00 baseline artifact reporter.
 *
 * Asserts that a production frontend build produced the required PWA artifacts
 * (manifest.webmanifest, sw.js, offline-capable shell) and records measurable
 * baselines: Service Worker precache entry count/bytes and gzip sizes of the
 * largest built assets.
 *
 * Usage: node scripts/pwa-artifact-report.mjs [distDir]
 * Output: <distDir>/pwa-baseline.json plus a human-readable summary on stdout.
 */
import { readFileSync, writeFileSync, readdirSync, statSync } from 'node:fs';
import { join, resolve } from 'node:path';
import { gzipSync } from 'node:zlib';

const distDir = resolve(process.argv[2] || 'dist');

function fail(message) {
    console.error(`[pwa-baseline] FAIL: ${message}`);
    process.exit(1);
}

/**
 * Extracts the precache manifest from a built service worker.
 * Handles both shapes:
 *   - generateSW output: `precacheAndRoute([{url,revision},...])`
 *   - injectManifest placeholder: `self.__WB_MANIFEST=[...]`
 *
 * The minified generateSW output uses unquoted object keys, so instead of
 * JSON.parse we return the balanced `[...]` source slice and let the caller
 * pull out entry URLs.
 */
function extractPrecacheArraySource(source, startMarker) {
    const markerIndex = source.indexOf(startMarker);
    if (markerIndex === -1) return null;
    const open = source.indexOf('[', markerIndex);
    if (open === -1) return null;
    let depth = 0;
    let inString = false;
    let escaped = false;
    for (let i = open; i < source.length; i += 1) {
        const ch = source[i];
        if (inString) {
            if (escaped) escaped = false;
            else if (ch === '\\') escaped = true;
            else if (ch === '"') inString = false;
            continue;
        }
        if (ch === '"') {
            inString = true;
        } else if (ch === '[' || ch === '{') {
            depth += 1;
        } else if (ch === ']' || ch === '}') {
            depth -= 1;
            if (depth === 0) return source.slice(open, i + 1);
        }
    }
    return null;
}

function extractPrecacheManifest(swSource) {
    const slice = (
        extractPrecacheArraySource(swSource, 'precacheAndRoute(')
        || extractPrecacheArraySource(swSource, 'self.__WB_MANIFEST=')
        // injectManifest output: the token is replaced by a bare array literal.
        || extractPrecacheArraySource(swSource, '[{"revision"')
        || extractPrecacheArraySource(swSource, '[{"url"')
    );
    if (!slice) return null;
    // Matches `"url":"/x"`, `{url:"/x"}` and `'url':'/x'` shapes.
    const urls = [...slice.matchAll(/["']?url["']?\s*:\s*["']([^"']+)["']/g)].map((m) => ({ url: m[1] }));
    return urls.length > 0 ? urls : null;
}

function listAssets(dir, prefix = '') {
    let entries = [];
    for (const name of readdirSync(dir)) {
        const full = join(dir, name);
        if (statSync(full).isDirectory()) {
            entries = entries.concat(listAssets(full, `${prefix}${name}/`));
        } else {
            entries.push(`${prefix}${name}`);
        }
    }
    return entries;
}

// --- Required artifacts -------------------------------------------------
const manifestPath = join(distDir, 'manifest.webmanifest');
const swPath = join(distDir, 'sw.js');
const indexPath = join(distDir, 'index.html');

for (const [label, path] of [['manifest.webmanifest', manifestPath], ['sw.js', swPath], ['index.html', indexPath]]) {
    try {
        statSync(path);
    } catch {
        fail(`required production PWA artifact missing: ${label}`);
    }
}

let manifest;
try {
    manifest = JSON.parse(readFileSync(manifestPath, 'utf8'));
} catch (err) {
    fail(`manifest.webmanifest is not valid JSON: ${err.message}`);
}
if (!Array.isArray(manifest.icons) || manifest.icons.length === 0) {
    fail('manifest has no icons');
}

const swSource = readFileSync(swPath, 'utf8');
// Cache-generation cleanup contract (stale deployment recovery): the custom
// worker manages `dentix-precache-*` generations and deletes older ones.
if (!swSource.includes('dentix-precache-')) {
    fail('service worker does not reference managed dentix-precache cache generations');
}
// NetworkOnly contract for clinical/financial traffic.
if (!swSource.includes('/api/')) {
    fail('service worker has no /api guard (API traffic must never be cached)');
}
// Conservative guard: any explicit API route registration must not be cache-first.
const apiRouteRegistrations = swSource.match(/registerRoute\([^)]*\)/g) || [];
for (const registration of apiRouteRegistrations) {
    if (/api/.test(registration) && /CacheFirst|StaleWhileRevalidate/.test(registration)) {
        fail(`sensitive /api route registered with a caching handler: ${registration}`);
    }
}

// --- Precache baseline ---------------------------------------------------
const precacheEntries = extractPrecacheManifest(swSource);
if (!precacheEntries || precacheEntries.length === 0) {
    fail('service worker precache manifest missing or empty');
}
let precacheBytes = 0;
for (const entry of precacheEntries) {
    if (!entry.url) continue;
    try {
        precacheBytes += statSync(join(distDir, entry.url.replace(/^\//, '').split('?')[0])).size;
    } catch {
        fail(`precache entry points at a missing file: ${entry.url}`);
    }
}

// --- Largest assets (gzip) ------------------------------------------------
const assetFiles = listAssets(distDir)
    .filter((f) => /\.(js|css)$/i.test(f))
    .map((f) => {
        const buf = readFileSync(join(distDir, f));
        return { file: f, rawBytes: buf.byteLength, gzipBytes: gzipSync(buf).byteLength };
    })
    .sort((a, b) => b.gzipBytes - a.gzipBytes);

const baseline = {
    generatedAt: new Date().toISOString(),
    distDir,
    manifest: {
        id: manifest.id ?? null,
        name: manifest.name,
        display: manifest.display,
        scope: manifest.scope ?? null,
        start_url: manifest.start_url,
        iconCount: manifest.icons.length,
    },
    serviceWorker: {
        precacheEntryCount: precacheEntries.length,
        precacheTotalBytes: precacheBytes,
    },
    largestAssetsGzip: assetFiles.slice(0, 10),
};

writeFileSync(join(distDir, 'pwa-baseline.json'), `${JSON.stringify(baseline, null, 2)}\n`);

console.log('[pwa-baseline] All required PWA artifacts present.');
console.log(`[pwa-baseline] Precache entries: ${baseline.serviceWorker.precacheEntryCount}`);
console.log(`[pwa-baseline] Precache bytes:   ${(baseline.serviceWorker.precacheTotalBytes / (1024 * 1024)).toFixed(2)} MiB`);
console.log('[pwa-baseline] Largest gzipped assets:');
for (const asset of baseline.largestAssetsGzip.slice(0, 5)) {
    console.log(`  ${asset.file} -> gzip ${(asset.gzipBytes / 1024).toFixed(1)} KiB`);
}
