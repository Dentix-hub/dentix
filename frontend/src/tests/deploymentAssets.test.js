import fs from 'node:fs';
import path from 'node:path';
import { describe, expect, it } from 'vitest';

const frontendRoot = path.resolve(globalThis.process.cwd());
const repositoryRoot = path.resolve(frontendRoot, '..');

function readPngMetadata(relativePath) {
    const file = fs.readFileSync(path.join(frontendRoot, relativePath));
    return {
        signature: file.subarray(0, 8).toString('hex'),
        width: file.readUInt32BE(16),
        height: file.readUInt32BE(20),
    };
}

describe('production asset delivery contract', () => {
    it.each([
        ['public/icons/icon-192.png', 192],
        ['public/icons/icon-512.png', 512],
    ])('%s is a real PNG with the manifest dimensions', (relativePath, size) => {
        expect(readPngMetadata(relativePath)).toEqual({
            signature: '89504e470d0a1a0a',
            width: size,
            height: size,
        });
    });

    it('keeps deployment-critical icons out of Git LFS', () => {
        const attributes = fs.readFileSync(path.join(repositoryRoot, '.gitattributes'), 'utf8');
        expect(attributes).toContain('frontend/public/icons/icon-192.png -filter -diff -merge -text');
        expect(attributes).toContain('frontend/public/icons/icon-512.png -filter -diff -merge -text');
    });

    it('allows the deployment-critical icons into the repository', () => {
        const gitignore = fs.readFileSync(path.join(repositoryRoot, '.gitignore'), 'utf8');
        expect(gitignore).toContain('!frontend/public/icons/icon-192.png');
        expect(gitignore).toContain('!frontend/public/icons/icon-512.png');
    });

    it('uses the deployed PNG as the browser favicon', () => {
        const html = fs.readFileSync(path.join(frontendRoot, 'index.html'), 'utf8');
        expect(html).toContain('<link rel="icon" type="image/png" href="/icons/icon-192.png" />');
        expect(html).not.toContain('/vite.svg');
    });

    it('does not rewrite static or PWA asset misses to index.html', () => {
        const config = JSON.parse(fs.readFileSync(path.join(frontendRoot, 'vercel.json'), 'utf8'));
        const fallback = config.rewrites.find((rewrite) => rewrite.destination === '/index.html');
        const fallbackPattern = new RegExp(`^${fallback.source}$`);

        for (const assetPath of [
            '/assets/missing.js',
            '/icons/missing.png',
            '/sw.js',
            '/workbox-oldhash.js',
            '/registerSW.js',
            '/manifest.webmanifest',
            '/favicon.ico',
            '/api/session',
        ]) {
            expect(fallbackPattern.test(assetPath), assetPath).toBe(false);
        }

        expect(fallbackPattern.test('/patients/123')).toBe(true);
        expect(fallbackPattern.test('/login')).toBe(true);
    });

    it('configures service-worker updates as an explicit user prompt', () => {
        const viteConfig = fs.readFileSync(path.join(frontendRoot, 'vite.config.js'), 'utf8');
        expect(viteConfig).toContain("registerType: 'prompt'");
        expect(viteConfig).toContain('skipWaiting: false');
        expect(viteConfig).toContain('clientsClaim: false');
    });

    it('never runtime-caches broad image traffic that may contain patient data', () => {
        const viteConfig = fs.readFileSync(path.join(frontendRoot, 'vite.config.js'), 'utf8');
        expect(viteConfig).toContain("handler: 'NetworkOnly'");
        expect(viteConfig).not.toContain("handler: 'CacheFirst'");
        expect(viteConfig).not.toContain("cacheName: 'images-cache'");
    });

    it('starts legacy image-cache cleanup before rendering the application', () => {
        const main = fs.readFileSync(path.join(frontendRoot, 'src/main.jsx'), 'utf8');
        const cleanupCall = main.indexOf('await deleteLegacyImageCache();');
        const renderSetup = main.indexOf("document.getElementById('root')");

        expect(cleanupCall).toBeGreaterThan(-1);
        expect(cleanupCall).toBeLessThan(renderSetup);
    });

    it('canonicalizes www traffic before it reaches cookie-authenticated APIs', () => {
        const caddyfile = fs.readFileSync(path.join(repositoryRoot, 'Caddyfile'), 'utf8');
        const productionCompose = fs.readFileSync(path.join(repositoryRoot, 'docker-compose.production.yml'), 'utf8');

        expect(caddyfile).toContain('{$WWW_DOMAIN:www.dentixs.app}');
        expect(caddyfile).toContain('redir https://{$DOMAIN:dentixs.app}{uri} permanent');
        expect(caddyfile).toContain('header_up X-Forwarded-Host {host}');
        expect(productionCompose).toContain('WWW_DOMAIN: ${WWW_DOMAIN:-www.dentixs.app}');
    });
});
