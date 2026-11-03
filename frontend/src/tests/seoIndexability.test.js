import { cpSync, mkdtempSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import path from 'node:path';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { validateMarketingHtml } from '../../scripts/verify-marketing-artifacts.mjs';
import { checkRoute, routeTests } from '../../scripts/verify-vercel-preview-routes.mjs';
import { CURRENT_ACTIVE_INDEXABLE_ROUTES } from '../../scripts/routeInventory.mjs';

const arHtml = readFileSync('public/ar/index.html', 'utf8');
const temporaryDirs = [];
afterEach(() => {
    vi.unstubAllGlobals();
    for (const dir of temporaryDirs.splice(0)) rmSync(dir, { recursive: true, force: true });
});

describe('Public indexing regression protection', () => {
    it.each([
        ['robots', 'follow, noindex'],
        ['ROBOTS', 'INDEX, FOLLOW, NOINDEX'],
        ['googlebot', 'none'],
        ['bingbot', 'NoIndex'],
    ])('rejects restrictive %s metadata regardless of token order/case', (name, content) => {
        const html = arHtml.replace('</head>', `<meta name="${name}" content="${content}"></head>`);
        expect(validateMarketingHtml(html).some(error => /noindex|none/i.test(error))).toBe(true);
    });

    it('rejects a translated target with restrictive robots metadata', () => {
        const dir = mkdtempSync(path.join(tmpdir(), 'dentix-seo-indexing-'));
        temporaryDirs.push(dir);
        cpSync('public', dir, { recursive: true });
        const target = path.join(dir, 'en/index.html');
        writeFileSync(target, readFileSync(target, 'utf8').replace('</head>', '<meta name="robots" content="follow, noindex"></head>'));
        expect(validateMarketingHtml(arHtml, dir).some(error => /noindex/i.test(error))).toBe(true);
    });

    it('rejects a translated target with a conflicting canonical', () => {
        const dir = mkdtempSync(path.join(tmpdir(), 'dentix-seo-canonical-'));
        temporaryDirs.push(dir);
        cpSync('public', dir, { recursive: true });
        const target = path.join(dir, 'en/index.html');
        writeFileSync(target, readFileSync(target, 'utf8').replace('rel="canonical" href="https://www.dentixs.app/en"', 'rel="canonical" href="https://www.dentixs.app/"'));
        expect(validateMarketingHtml(arHtml, dir).some(error => /canonical/i.test(error))).toBe(true);
    });

    it('rejects a translated target without the return hreflang link', () => {
        const dir = mkdtempSync(path.join(tmpdir(), 'dentix-seo-reciprocity-'));
        temporaryDirs.push(dir);
        cpSync('public', dir, { recursive: true });
        const target = path.join(dir, 'en/index.html');
        writeFileSync(target, readFileSync(target, 'utf8').replace(/<link rel="alternate" hreflang="ar"[^>]*>/, ''));
        expect(validateMarketingHtml(arHtml, dir).some(error => /reciprocal/i.test(error))).toBe(true);
    });

    it.each(['noindex', 'follow, NOINDEX', 'googlebot: none', 'bingbot: noindex'])('rejects an HTTP indexing restriction: %s', async header => {
        vi.stubGlobal('fetch', vi.fn(async () => new Response(arHtml, {
            status: 200,
            headers: { 'content-type': 'text/html', 'x-robots-tag': header },
        })));
        const contract = routeTests.find(test => test.path === '/ar');
        const result = await checkRoute(contract.desc, contract.path, contract.expected);
        expect(result.passed).toBe(false);
        expect(result.details.some(error => /x-robots-tag/i.test(error))).toBe(true);
    });

    it('rejects SPA fallback HTML for every indexable public route in both languages', async () => {
        const shell = readFileSync('index.html', 'utf8');
        vi.stubGlobal('fetch', vi.fn(async () => new Response(shell, {
            status: 200, headers: { 'content-type': 'text/html' },
        })));
        for (const canonical of CURRENT_ACTIVE_INDEXABLE_ROUTES) {
            const pathname = new URL(canonical).pathname;
            const contract = routeTests.find(test => test.path === pathname);
            expect(contract, `Missing HTTP contract for ${pathname}`).toBeDefined();
            const result = await checkRoute(contract.desc, contract.path, contract.expected);
            expect(result.passed, `SPA fallback accepted for ${pathname}`).toBe(false);
        }
    });

    it('accepts each real public page with its canonical HTTP contract', async () => {
        for (const canonical of CURRENT_ACTIVE_INDEXABLE_ROUTES) {
            const pathname = new URL(canonical).pathname;
            const html = readFileSync(`public${pathname}/index.html`, 'utf8');
            vi.stubGlobal('fetch', vi.fn(async () => new Response(html, {
                status: 200,
                headers: {
                    'content-type': 'text/html',
                    'x-content-type-options': 'nosniff',
                    'referrer-policy': 'strict-origin-when-cross-origin',
                },
            })));
            const contract = routeTests.find(test => test.path === pathname);
            const result = await checkRoute(contract.desc, contract.path, contract.expected);
            expect(result.details, pathname).toEqual([]);
            expect(result.passed).toBe(true);
        }
    });
});
