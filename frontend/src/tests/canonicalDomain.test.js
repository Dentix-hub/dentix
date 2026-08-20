import fs from 'node:fs';
import path from 'node:path';
import { describe, expect, it } from 'vitest';

const frontendRoot = path.resolve(globalThis.process.cwd());
const repositoryRoot = path.resolve(frontendRoot, '..');

describe('canonical production domain', () => {
    it('redirects www before cookie-authenticated API requests are proxied', () => {
        const caddyfile = fs.readFileSync(path.join(repositoryRoot, 'Caddyfile'), 'utf8');
        const productionCompose = fs.readFileSync(path.join(repositoryRoot, 'docker-compose.production.yml'), 'utf8');

        expect(caddyfile).toContain('{$WWW_DOMAIN:www.dentixs.app}');
        expect(caddyfile).toContain('redir https://{$DOMAIN:dentixs.app}{uri} permanent');
        expect(caddyfile).toContain('header_up X-Forwarded-Host {host}');
        expect(productionCompose).toContain('WWW_DOMAIN: ${WWW_DOMAIN:-www.dentixs.app}');
    });
});
