import { readFileSync } from 'node:fs';
import path from 'node:path';
import { beforeEach, describe, expect, it, vi } from 'vitest';

// Vitest may present import.meta.url with a non-file scheme; path.resolve
// anchors on the CLI working directory (the frontend root).
const source = readFileSync(path.resolve('src/pwa/sw.js'), 'utf8');

const MANIFEST = [
    { revision: 'r1', url: 'index.html' },
    { revision: 'r2', url: 'assets/app-abc.js' },
];

function createStubs() {
    const cacheStub = {
        addAll: vi.fn().mockResolvedValue(undefined),
        put: vi.fn().mockResolvedValue(undefined),
        keys: vi.fn().mockResolvedValue([]),
    };
    const cachesStub = {
        open: vi.fn().mockResolvedValue(cacheStub),
        keys: vi.fn().mockResolvedValue([]),
        delete: vi.fn().mockResolvedValue(true),
        match: vi.fn().mockResolvedValue(undefined),
    };
    const listeners = {};
    const selfStub = {
        location: { origin: 'https://www.dentixs.app' },
        __WB_MANIFEST: MANIFEST,
        registration: { showNotification: vi.fn().mockResolvedValue(undefined) },
        clients: {
            matchAll: vi.fn().mockResolvedValue([]),
            openWindow: vi.fn().mockResolvedValue(undefined),
        },
        skipWaiting: vi.fn().mockResolvedValue(undefined),
        addEventListener: (type, handler) => { listeners[type] = handler; },
    };
    const fetchMock = vi.fn().mockResolvedValue(new Response('network'));
    const loader = new Function('self', 'caches', 'fetch', source);
    loader(selfStub, cachesStub, fetchMock);
    return { selfStub, cachesStub, cacheStub, listeners, fetchMock };
}

describe('custom service worker contract (plan §11)', () => {
    let stubs;
    beforeEach(() => {
        stubs = createStubs();
    });

    it('is push-capable and keeps the API NetworkOnly guard in source', () => {
        expect(source).toContain("addEventListener('push'");
        expect(source).toContain("addEventListener('notificationclick'");
        expect(source).toContain('/api/');
        // No runtime caching handlers may appear in the custom worker.
        expect(source).not.toContain('CacheFirst');
        expect(source).not.toContain('StaleWhileRevalidate');
        expect(source).not.toContain('BackgroundSync');
    });

    it('precaches the injected manifest at install without skipWaiting', async () => {
        const event = { waitUntil: (p) => p };
        stubs.listeners.install(event);
        await vi.waitFor(() => expect(stubs.cacheStub.addAll).toHaveBeenCalled());

        const urls = stubs.cacheStub.addAll.mock.calls[0][0];
        expect(urls.some((u) => u.endsWith('/index.html'))).toBe(true);
        expect(urls.some((u) => u.includes('/assets/app-abc.js'))).toBe(true);
        expect(stubs.selfStub.skipWaiting).not.toHaveBeenCalled();
    });

    it('cleans legacy workbox and older dentix cache generations at activate', async () => {
        stubs.cachesStub.keys.mockResolvedValue([
            'workbox-precache-v2-https://www.dentixs.app/',
            'dentix-precache-00000000',
            'other-unmanaged-cache',
        ]);
        const event = { waitUntil: (p) => p };
        stubs.listeners.activate(event);
        await vi.waitFor(() => expect(stubs.cachesStub.delete).toHaveBeenCalled());

        const deleted = stubs.cachesStub.delete.mock.calls.map((c) => c[0]);
        expect(deleted).toContain('workbox-precache-v2-https://www.dentixs.app/');
        expect(deleted).toContain('dentix-precache-00000000');
        expect(deleted).not.toContain('other-unmanaged-cache');
        expect(stubs.selfStub.skipWaiting).not.toHaveBeenCalled();
    });

    it('never intercepts /api requests (NetworkOnly)', () => {
        const request = new Request('https://www.dentixs.app/api/v1/patients');
        const event = { request, respondWith: vi.fn() };
        stubs.listeners.fetch(event);
        expect(event.respondWith).not.toHaveBeenCalled();
    });

    it('serves the precached shell for SPA navigations and cached assets cache-first', async () => {
        const shell = new Response('<html>shell</html>');
        // The worker passes either a Request or a URL to caches.match.
        stubs.cachesStub.match.mockImplementation(async (request) => (
            String(request.href ?? request.url).endsWith('/index.html') ? shell : undefined
        ));

        // Request cannot be constructed with mode 'navigate'; a plain stub
        // mirrors the fetch event request surface the worker relies on.
        const navEvent = {
            request: { url: 'https://www.dentixs.app/patients', mode: 'navigate', method: 'GET' },
            respondWith: vi.fn(),
        };
        stubs.listeners.fetch(navEvent);
        expect(navEvent.respondWith).toHaveBeenCalled();
        await expect(navEvent.respondWith.mock.calls[0][0]).resolves.toBe(shell);

        const assetEvent = {
            request: new Request('https://www.dentixs.app/assets/app-abc.js'),
            respondWith: vi.fn(),
        };
        stubs.listeners.fetch(assetEvent);
        const assetResponse = await assetEvent.respondWith.mock.calls[0][0];
        expect(assetResponse).toBeInstanceOf(Response);
        // Lazy build assets are runtime-cached for repeat use (public hashed content).
        await vi.waitFor(() => expect(stubs.cacheStub.put).toHaveBeenCalled());
    });

    it('activates updates only on the explicit SKIP_WAITING message', () => {
        stubs.listeners.message({ data: { type: 'OTHER' } });
        expect(stubs.selfStub.skipWaiting).not.toHaveBeenCalled();

        stubs.listeners.message({ data: { type: 'SKIP_WAITING' } });
        expect(stubs.selfStub.skipWaiting).toHaveBeenCalledTimes(1);
    });

    it('shows a privacy-safe default notification when the push payload is empty', async () => {
        const promises = [];
        const event = { data: null, waitUntil: (p) => promises.push(p) };
        stubs.listeners.push(event);
        await Promise.all(promises);

        expect(stubs.selfStub.registration.showNotification).toHaveBeenCalledWith(
            'DENTIX',
            expect.objectContaining({ dir: 'rtl', lang: 'ar' }),
        );
    });

    it('hands foreground pushes to the app instead of duplicating a system notification', async () => {
        const focusedClient = { focused: true, postMessage: vi.fn() };
        stubs.selfStub.clients.matchAll.mockResolvedValue([focusedClient]);

        const promises = [];
        const event = {
            data: { json: () => ({ notification: { title: 'DENTIX', body: 'تنبيه' } }) },
            waitUntil: (p) => promises.push(p),
        };
        stubs.listeners.push(event);
        await Promise.all(promises);

        expect(focusedClient.postMessage).toHaveBeenCalledWith({
            type: 'PUSH_RECEIVED',
            payload: { notification: { title: 'DENTIX', body: 'تنبيه' } },
        });
        expect(stubs.selfStub.registration.showNotification).not.toHaveBeenCalled();
    });

    it('only navigates to allowlisted same-origin routes from notification clicks', async () => {
        const promises = [];
        const evil = {
            notification: { close: vi.fn(), data: { navigate: 'https://evil.example/patients' } },
            waitUntil: (p) => promises.push(p),
        };
        stubs.listeners.notificationclick(evil);
        await Promise.all(promises);
        expect(stubs.selfStub.clients.openWindow).toHaveBeenCalledWith('/');

        stubs.selfStub.clients.openWindow.mockClear();
        const safe = {
            notification: { close: vi.fn(), data: { navigate: 'https://www.dentixs.app/appointments' } },
            waitUntil: (p) => promises.push(p),
        };
        stubs.listeners.notificationclick(safe);
        await Promise.all(promises);
        expect(stubs.selfStub.clients.openWindow).toHaveBeenCalledWith('/appointments');
    });
});
