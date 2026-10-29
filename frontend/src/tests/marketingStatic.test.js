import { readFileSync, existsSync } from 'node:fs';
import path from 'node:path';
import { describe, expect, it } from 'vitest';

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
});
