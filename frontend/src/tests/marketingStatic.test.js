import { readFileSync, existsSync } from 'node:fs';
import path from 'node:path';
import { describe, expect, it } from 'vitest';
import {
    validateMarketingHtml,
    validateSitemapXml,
    validateRobotsTxt,
} from '../../scripts/verify-marketing-artifacts.mjs';
import { checkRoute } from '../../scripts/verify-vercel-preview-routes.mjs';

const arHtmlPath = path.resolve('public/ar/index.html');
const cssPath = path.resolve('public/marketing/marketing.css');
const robotsPath = path.resolve('public/robots.txt');
const sitemapPath = path.resolve('public/sitemap.xml');
const vercelJsonPath = path.resolve('vercel.json');

describe('Marketing Static Arabic Page Contract', () => {
    it('verifies public/ar/index.html exists and has valid metadata', () => {
        expect(existsSync(arHtmlPath)).toBe(true);
        const html = readFileSync(arHtmlPath, 'utf8');

        // Language & direction
        expect(html).toMatch(/<html[^>]*lang=["']ar["']/);
        expect(html).toMatch(/<html[^>]*dir=["']rtl["']/);

        // Title and description
        expect(html).toContain('<title>Dentix | برنامج إدارة عيادات الأسنان في مصر</title>');
        expect(html).toContain('<meta name="description" content="نظّم ملفات المرضى والمواعيد ومخطط الأسنان وتقارير العيادة مع Dentix، نظام سحابي لإدارة عيادات الأسنان بواجهة عربية وإنجليزية.">');

        // H1 and Core headings
        expect(html).toContain('<h1 class="hero-title">إدارة عيادة الأسنان من مكان واحد.</h1>');

        // Canonical URL
        expect(html).toContain('<link rel="canonical" href="https://www.dentixs.app/ar">');

        // Open Graph
        expect(html).toContain('<meta property="og:title" content="Dentix | برنامج إدارة عيادات الأسنان في مصر">');
        expect(html).toContain('<meta property="og:description" content="نظّم ملفات المرضى والمواعيد ومخطط الأسنان وتقارير العيادة مع Dentix، نظام سحابي لإدارة عيادات الأسنان بواجهة عربية وإنجليزية.">');
        expect(html).toContain('<meta property="og:url" content="https://www.dentixs.app/ar">');
        expect(html).toContain('<meta property="og:site_name" content="Dentix">');
        expect(html).toContain('<meta property="og:type" content="website">');
        expect(html).toContain('<meta property="og:locale" content="ar_EG">');
        expect(html).toContain('<meta property="og:image" content="https://www.dentixs.app/logo.webp">');

        // Twitter Card
        expect(html).toContain('<meta name="twitter:card" content="summary">');
        expect(html).toContain('<meta name="twitter:title" content="Dentix | برنامج إدارة عيادات الأسنان في مصر">');
        expect(html).toContain('<meta name="twitter:image" content="https://www.dentixs.app/logo.webp">');

        // Local CSS reference
        expect(html).toContain('<link rel="stylesheet" href="/marketing/marketing.css">');
    });

    it('guarantees zero executable scripts, zero react bundles, zero service worker or manifest in ar/index.html', () => {
        const html = readFileSync(arHtmlPath, 'utf8');

        // Any script tags must ONLY be JSON-LD
        const scriptMatches = html.match(/<script\b[^>]*>([\s\S]*?)<\/script>/gi) || [];
        for (const scriptTag of scriptMatches) {
            expect(scriptTag).toMatch(/type=["']application\/ld\+json["']/);
            expect(scriptTag).not.toMatch(/src=/);
        }

        expect(html).not.toContain('registerSW');
        expect(html).not.toContain('navigator.serviceWorker');
        expect(html).not.toContain('manifest.webmanifest');
        expect(html).not.toContain('main.jsx');
        expect(html).not.toContain('assets/index');
        expect(html).not.toContain('localhost');
        expect(html).not.toContain('127.0.0.1');
    });

    it('enforces navigation links contract: login points to / (NOT /login)', () => {
        const html = readFileSync(arHtmlPath, 'utf8');

        // Login links must point to / and never /login
        const loginLinkMatches = html.match(/<a\b[^>]*href=["']([^"']*)["'][^>]*>تسجيل الدخول[^<]*<\/a>/gi) || [];
        expect(loginLinkMatches.length).toBeGreaterThanOrEqual(2);
        for (const match of loginLinkMatches) {
            expect(match).toMatch(/href=["']\/["']/);
            expect(match).not.toMatch(/href=["']\/login["']/);
        }

        // Register links must point to /register
        expect(html).toContain('href="/register"');

        // Legal links
        expect(html).toContain('href="/terms"');
        expect(html).toContain('href="/privacy"');
    });

    it('validates structured data (JSON-LD) compliance', () => {
        const html = readFileSync(arHtmlPath, 'utf8');
        const jsonLdMatch = html.match(/<script type=["']application\/ld\+json["']>([\s\S]*?)<\/script>/);
        expect(jsonLdMatch).toBeTruthy();

        const data = JSON.parse(jsonLdMatch[1]);
        expect(data['@context']).toBe('https://schema.org');
        expect(Array.isArray(data['@graph'])).toBe(true);

        const types = data['@graph'].map((item) => item['@type']);
        expect(types).toContain('Organization');
        expect(types).toContain('WebSite');
        expect(types).toContain('SoftwareApplication');

        // Prohibited schema claims
        expect(types).not.toContain('Dentist');
        expect(types).not.toContain('LocalBusiness');
        const fullJson = JSON.stringify(data);
        expect(fullJson).not.toContain('legalName');
        expect(fullJson).not.toContain('aggregateRating');
        expect(fullJson).not.toContain('priceRange');
        expect(fullJson).not.toContain('offers');
    });

    it('verifies public/robots.txt content', () => {
        expect(existsSync(robotsPath)).toBe(true);
        const robots = readFileSync(robotsPath, 'utf8');
        expect(robots).toContain('User-agent: *');
        expect(robots).toContain('Disallow: /api/');
        expect(robots).toContain('Sitemap: https://www.dentixs.app/sitemap.xml');
        expect(robots).not.toContain('Disallow: /marketing/');
        expect(robots).not.toContain('Disallow: /ar');
        expect(robots).not.toContain('<!DOCTYPE');
    });

    it('verifies public/sitemap.xml content', () => {
        expect(existsSync(sitemapPath)).toBe(true);
        const sitemap = readFileSync(sitemapPath, 'utf8');
        expect(sitemap).toContain('<urlset');
        expect(sitemap).toContain('<loc>https://www.dentixs.app/ar</loc>');
        expect(sitemap).not.toContain('/login');
        expect(sitemap).not.toContain('/register');
        expect(sitemap).not.toContain('/api');
        expect(sitemap).not.toContain('/index.html');
    });

    it('verifies marketing.css exists and is responsive', () => {
        expect(existsSync(cssPath)).toBe(true);
        const css = readFileSync(cssPath, 'utf8');
        expect(css).toContain('--color-primary:');
        expect(css).toContain('--color-secondary:');
        expect(css).toContain('@media');
        expect(css).toContain('max-width: 640px');
    });

    it('validates vercel.json routing rules and fallback exclusions', () => {
        expect(existsSync(vercelJsonPath)).toBe(true);
        const config = JSON.parse(readFileSync(vercelJsonPath, 'utf8'));

        // Redirects
        expect(config.redirects).toBeDefined();
        const arTrailingRedirect = config.redirects.find((r) => r.source === '/ar/');
        expect(arTrailingRedirect).toEqual({
            source: '/ar/',
            destination: '/ar',
            permanent: true,
        });

        const arIndexRedirect = config.redirects.find((r) => r.source === '/ar/index.html');
        expect(arIndexRedirect).toEqual({
            source: '/ar/index.html',
            destination: '/ar',
            permanent: true,
        });

        // Rewrites
        expect(config.rewrites).toBeDefined();
        const arRewrite = config.rewrites.find((r) => r.source === '/ar');
        expect(arRewrite).toEqual({
            source: '/ar',
            destination: '/ar/index.html',
        });

        const fallback = config.rewrites.find((r) => r.destination === '/index.html');
        expect(fallback).toBeDefined();

        const pattern = new RegExp(`^${fallback.source}$`);

        // Normal app routes MUST match the fallback to /index.html
        expect(pattern.test('/')).toBe(true);
        expect(pattern.test('/login')).toBe(true);
        expect(pattern.test('/patients')).toBe(true);
        expect(pattern.test('/appointments')).toBe(true);
        expect(pattern.test('/archive')).toBe(true);
        expect(pattern.test('/arbitrary')).toBe(true);

        // Marketing and crawler routes MUST NOT match fallback
        expect(pattern.test('/ar')).toBe(false);
        expect(pattern.test('/ar/')).toBe(false);
        expect(pattern.test('/ar/unknown')).toBe(false);
        expect(pattern.test('/marketing/marketing.css')).toBe(false);
        expect(pattern.test('/marketing/unknown.css')).toBe(false);
        expect(pattern.test('/robots.txt')).toBe(false);
        expect(pattern.test('/sitemap.xml')).toBe(false);
        expect(pattern.test('/api/v1/patients')).toBe(false);
    });

    describe('Build Artifacts Semantic Parser & Negative Failure Proofs', () => {
        it('proves rejection of invalid XML in sitemap.xml', () => {
            const invalidXml = '<urlset><url><loc>https://www.dentixs.app/ar</loc></urlset';
            const errors = validateSitemapXml(invalidXml);
            expect(errors.length).toBeGreaterThan(0);
            expect(errors.some((e) => e.includes('XML') || e.includes('Invalid') || e.includes('unclosed'))).toBe(true);
        });

        it('proves rejection of sitemap with invalid root element like <not-a-sitemap>', () => {
            const invalidRoot = `<?xml version="1.0" encoding="UTF-8"?>
<not-a-sitemap xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url><loc>https://www.dentixs.app/ar</loc></url>
</not-a-sitemap>`;
            const errors = validateSitemapXml(invalidRoot);
            expect(errors.length).toBeGreaterThan(0);
            expect(errors.some((e) => e.includes('Invalid sitemap root element'))).toBe(true);
        });

        it('proves rejection of sitemap with wrong or missing namespace xmlns', () => {
            const wrongNamespace = `<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://example.com/wrong-schema">
  <url><loc>https://www.dentixs.app/ar</loc></url>
</urlset>`;
            const errors = validateSitemapXml(wrongNamespace);
            expect(errors.length).toBeGreaterThan(0);
            expect(errors.some((e) => e.includes('Invalid sitemap xmlns namespace'))).toBe(true);
        });

        it('proves rejection of sitemap missing the required /ar URL', () => {
            const emptySitemap = `<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url><loc>https://www.dentixs.app/other</loc></url>
</urlset>`;
            const errors = validateSitemapXml(emptySitemap);
            expect(errors.length).toBeGreaterThan(0);
            expect(errors.some((e) => e.includes('Required URL missing'))).toBe(true);
        });

        it('proves rejection of missing stylesheet or icon in <link> elements', () => {
            const htmlWithMissingCss = `<!DOCTYPE html><html lang="ar" dir="rtl"><head><title>Test</title><link rel="canonical" href="https://www.dentixs.app/ar"><link rel="stylesheet" href="/marketing/nonexistent-css-file.css"></head><body><a href="/">تسجيل الدخول</a><a href="/">تسجيل الدخول</a></body></html>`;
            const errorsCss = validateMarketingHtml(htmlWithMissingCss, path.resolve('public'));
            expect(errorsCss.length).toBeGreaterThan(0);
            expect(errorsCss.some((e) => e.includes('Referenced <link rel="stylesheet"> asset not found on disk'))).toBe(true);

            const htmlWithMissingIcon = `<!DOCTYPE html><html lang="ar" dir="rtl"><head><title>Test</title><link rel="canonical" href="https://www.dentixs.app/ar"><link rel="icon" href="/icons/missing-icon-file.png"></head><body><a href="/">تسجيل الدخول</a><a href="/">تسجيل الدخول</a></body></html>`;
            const errorsIcon = validateMarketingHtml(htmlWithMissingIcon, path.resolve('public'));
            expect(errorsIcon.length).toBeGreaterThan(0);
            expect(errorsIcon.some((e) => e.includes('Referenced <link rel="icon"> asset not found on disk'))).toBe(true);
        });

        it('proves rejection of disallowed or private routes like /patients in sitemap.xml', () => {
            const sitemapWithPatients = `<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url><loc>https://www.dentixs.app/ar</loc></url>
  <url><loc>https://www.dentixs.app/patients</loc></url>
</urlset>`;
            const errors = validateSitemapXml(sitemapWithPatients);
            expect(errors.length).toBeGreaterThan(0);
            expect(errors.some((e) => e.includes('https://www.dentixs.app/patients'))).toBe(true);
        });

        it('proves rejection of Disallow: / blocking crawl in robots.txt', () => {
            const blockingRobots = `User-agent: *\nDisallow: /\n\nSitemap: https://www.dentixs.app/sitemap.xml`;
            const errors = validateRobotsTxt(blockingRobots);
            expect(errors.length).toBeGreaterThan(0);
            expect(errors.some((e) => e.includes('blocks full site crawling'))).toBe(true);
        });

        it('proves rejection of executable JavaScript inside marketing HTML', () => {
            // Case A: inline executable <script>
            const htmlWithScript = `<!DOCTYPE html><html lang="ar" dir="rtl"><head><title>Test</title><link rel="canonical" href="https://www.dentixs.app/ar"><script>alert(1)</script></head><body><a href="/">تسجيل الدخول</a><a href="/">تسجيل الدخول</a></body></html>`;
            const errorsA = validateMarketingHtml(htmlWithScript);
            expect(errorsA.length).toBeGreaterThan(0);
            expect(errorsA.some((e) => e.includes('Executable script found'))).toBe(true);

            // Case B: external <script src="...">
            const htmlWithSrc = `<!DOCTYPE html><html lang="ar" dir="rtl"><head><title>Test</title><link rel="canonical" href="https://www.dentixs.app/ar"><script src="/assets/index-app.js"></script></head><body><a href="/">تسجيل الدخول</a><a href="/">تسجيل الدخول</a></body></html>`;
            const errorsB = validateMarketingHtml(htmlWithSrc);
            expect(errorsB.length).toBeGreaterThan(0);
            expect(errorsB.some((e) => e.includes('External script tag found'))).toBe(true);

            // Case C: inline event handler (e.g. onclick)
            const htmlWithEvent = `<!DOCTYPE html><html lang="ar" dir="rtl"><head><title>Test</title><link rel="canonical" href="https://www.dentixs.app/ar"></head><body><button onclick="console.log(1)">Click</button><a href="/">تسجيل الدخول</a><a href="/">تسجيل الدخول</a></body></html>`;
            const errorsC = validateMarketingHtml(htmlWithEvent);
            expect(errorsC.length).toBeGreaterThan(0);
            expect(errorsC.some((e) => e.includes('Inline event handler attribute found'))).toBe(true);
        });

        it('passes semantic validation cleanly on actual project source files', () => {
            const actualHtml = readFileSync(arHtmlPath, 'utf8');
            const actualSitemap = readFileSync(sitemapPath, 'utf8');
            const actualRobots = readFileSync(robotsPath, 'utf8');

            expect(validateMarketingHtml(actualHtml, path.resolve('public'))).toEqual([]);
            expect(validateSitemapXml(actualSitemap)).toEqual([]);
            expect(validateRobotsTxt(actualRobots)).toEqual([]);
        });
    });

    describe('Vercel Preview HTTP Route Validator Robustness Tests', () => {
        it('proves checkRoute catches and rejects cross-domain redirect attempt (open-redirect)', async () => {
            const originalFetch = globalThis.fetch;
            globalThis.fetch = async () => new Response(null, {
                status: 308,
                headers: { location: 'https://evil.attacker.com/ar' },
            });

            try {
                const res = await checkRoute('Trailing slash redirect', '/ar/', { status: 308, location: '/ar' });
                expect(res.passed).toBe(false);
                expect(res.details.some((d) => d.includes('Location origin mismatch'))).toBe(true);
            } finally {
                globalThis.fetch = originalFetch;
            }
        });

        it('proves checkRoute catches and rejects robots.txt served as text/html', async () => {
            const originalFetch = globalThis.fetch;
            globalThis.fetch = async () => new Response('User-agent: *\nDisallow: /api/\nSitemap: https://www.dentixs.app/sitemap.xml', {
                status: 200,
                headers: { 'content-type': 'text/html; charset=utf-8' },
            });

            try {
                const res = await checkRoute('Robots check', '/robots.txt', {
                    status: 200,
                    contentType: 'text/plain',
                    contentTypeNot: 'text/html',
                    validator: validateRobotsTxt,
                });
                expect(res.passed).toBe(false);
                expect(res.details.some((d) => d.includes('Content-Type'))).toBe(true);
            } finally {
                globalThis.fetch = originalFetch;
            }
        });

        it('proves checkRoute catches and rejects sitemap.xml with invalid XML or bad schema', async () => {
            const originalFetch = globalThis.fetch;
            globalThis.fetch = async () => new Response('<not-a-sitemap></not-a-sitemap>', {
                status: 200,
                headers: { 'content-type': 'application/xml; charset=utf-8' },
            });

            try {
                const res = await checkRoute('Sitemap check', '/sitemap.xml', {
                    status: 200,
                    contentType: 'xml',
                    validator: validateSitemapXml,
                });
                expect(res.passed).toBe(false);
                expect(res.details.some((d) => d.includes('Invalid sitemap root element'))).toBe(true);
            } finally {
                globalThis.fetch = originalFetch;
            }
        });
    });
});
