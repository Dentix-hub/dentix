/**
 * DENTIX custom service worker (vite-plugin-pwa `injectManifest`).
 *
 * Replaces the generated Workbox worker while preserving its exact contract:
 * - precached app shell + hashed build assets (injected `self.__WB_MANIFEST`);
 * - SPA navigation fallback to the cached shell (never for `/api`);
 * - `/api` is NetworkOnly: never intercepted, never cached (PHI/finance safety);
 * - outdated cache generations are deleted (stale deployment recovery);
 * - updates stay user-controlled: no skipWaiting at install, no clientsClaim;
 * - Web Push + notification click skeleton for the push phase (route allowlist).
 *
 * The precache cache name embeds a hash of the injected manifest so every
 * deployment gets a fresh generation and the previous one is cleaned up.
 */

const precacheManifest = self.__WB_MANIFEST || [];

function manifestGenerationHash() {
    // FNV-1a over sorted deduplicated manifest URLs: stable per build, changes
    // when the precache payload changes.
    const urls = Array.from(new Set(precacheManifest.map((entry) => entry.url))).sort().join('|');
    let hash = 0x811c9dc5;
    for (let i = 0; i < urls.length; i += 1) {
        hash ^= urls.charCodeAt(i);
        hash = Math.imul(hash, 0x01000193);
    }
    return (hash >>> 0).toString(16).padStart(8, '0');
}

const PRECACHE_CACHE = `dentix-precache-${manifestGenerationHash()}`;
// Public, content-hashed build assets excluded from precache land here on
// first use (plan §11.2: "selected hashed static chunks ... after measurement").
const RUNTIME_ASSET_CACHE = 'dentix-runtime-assets-v2';
const MANAGED_CACHE_PREFIXES = ['dentix-precache-', 'dentix-runtime-', 'workbox-precache-'];

async function precacheAll() {
    const cache = await caches.open(PRECACHE_CACHE);
    // Deduplicate normalized absolute URLs to avoid Cache.addAll() rejecting on duplicates
    const urls = Array.from(
        new Set(precacheManifest.map((entry) => new URL(entry.url, self.location.origin).href))
    );
    await cache.addAll(urls);
}

self.addEventListener('install', (event) => {
    event.waitUntil(precacheAll());
    // Deliberately NO skipWaiting(): the running clinical session keeps its
    // version until the user accepts the update prompt (plan §11.1).
});

async function cleanupOutdatedCaches() {
    const names = await caches.keys();
    await Promise.all(
        names
            .filter((name) => name !== PRECACHE_CACHE
                && MANAGED_CACHE_PREFIXES.some((prefix) => name.startsWith(prefix)))
            .map((name) => caches.delete(name)),
    );
}

self.addEventListener('activate', (event) => {
    event.waitUntil(cleanupOutdatedCaches());
    // Deliberately NO clientsClaim(): the worker takes control of open tabs
    // only after the user-confirmed reload.
});

function isApiUrl(url) {
    return url.pathname.startsWith('/api/');
}

async function handleRequest(request) {
    if (request.mode === 'navigate') {
        // SPA navigation fallback: serve the precached app shell offline.
        const shell = await caches.match(new URL('/index.html', self.location.origin))
            || await caches.match('/index.html');
        if (shell) return shell;
        try {
            return await fetch(request);
        } catch {
            // Network failed and shell wasn't in precache (e.g. initial install in flight, offline, or server restarting)
            const fallback = await caches.match('/index.html', { ignoreSearch: true })
                || await caches.match(request);
            if (fallback) return fallback;
            return new Response(
                '<!DOCTYPE html><html dir="rtl" lang="ar"><head><meta charset="utf-8"><title>DENTIX — غير متصل</title><meta name="viewport" content="width=device-width, initial-scale=1"></head><body style="font-family:system-ui,-apple-system,sans-serif;display:flex;align-items:center;justify-content:center;height:100vh;margin:0;background:#0f172a;color:#f8fafc;text-align:center;padding:1rem;"><div><h1 style="font-size:1.5rem;margin-bottom:0.5rem;">تعذر الاتصال بالخادم</h1><p style="color:#94a3b8;margin-bottom:1.5rem;">يرجى التحقق من اتصال الإنترنت أو الانتظار ريثما يستيقظ الخادم.</p><button onclick="location.reload()" style="background:#0ea5e9;color:white;border:none;padding:0.75rem 1.5rem;border-radius:0.5rem;font-weight:bold;cursor:pointer;">إعادة المحاولة</button></div></body></html>',
                {
                    status: 503,
                    statusText: 'Service Unavailable',
                    headers: { 'Content-Type': 'text/html; charset=utf-8' },
                }
            );
        }
    }
    const cached = await caches.match(request);
    if (cached) return cached;

    // Non-precached same-origin build assets (lazy vendor chunks): fetch and
    // cache for repeat use. These are public, content-hashed, non-PHI files.
    const url = new URL(request.url);
    if (url.pathname.startsWith('/assets/')) {
        try {
            const response = await fetch(request);
            if (response && response.ok) {
                const runtimeCache = await caches.open(RUNTIME_ASSET_CACHE);
                runtimeCache.put(request, response.clone()).catch(() => {});
            }
            return response;
        } catch {
            const fallbackAsset = await caches.match(request);
            if (fallbackAsset) return fallbackAsset;
            return new Response('Asset unavailable offline', {
                status: 504,
                statusText: 'Gateway Timeout',
                headers: { 'Content-Type': 'text/plain; charset=utf-8' },
            });
        }
    }

    // Everything else goes straight to the network and is never cached
    // (no PHI may enter Cache Storage, plan §11.2).
    return fetch(request);
}

self.addEventListener('fetch', (event) => {
    const { request } = event;
    if (request.method !== 'GET') return;

    const url = new URL(request.url);
    if (url.origin !== self.location.origin) return; // cross-origin: network only
    if (isApiUrl(url)) return; // NetworkOnly: clinical/financial traffic is never cached

    event.respondWith(handleRequest(request));
});

// Update prompt contract used by virtual:pwa-register (registerType: 'prompt').
self.addEventListener('message', (event) => {
    if (event.data && event.data.type === 'SKIP_WAITING') {
        self.skipWaiting();
    }
});

// --- Web Push (plan §12.5–§12.7): privacy-safe display + allowlisted clicks ---

const NOTIFICATION_DEFAULTS = {
    title: 'DENTIX',
    body: 'يوجد تنبيه جديد يحتاج مراجعتك',
    lang: 'ar',
    dir: 'rtl',
};

const NOTIFICATION_ROUTE_ALLOWLIST = [
    '/appointments',
    '/patients',
    '/inventory',
    '/finance/overview',
    '/settings',
];

function safeNavigationPath(rawUrl) {
    try {
        const url = new URL(rawUrl, self.location.origin);
        if (url.origin !== self.location.origin) return null;
        const path = url.pathname;
        const allowed = NOTIFICATION_ROUTE_ALLOWLIST.some((route) => (
            path === route || path.startsWith(`${route}/`)
        ));
        return allowed ? `${path}${url.search}` : null;
    } catch {
        return null;
    }
}

self.addEventListener('push', (event) => {
    let payload = {};
    try {
        if (event.data) payload = event.data.json();
    } catch {
        payload = {};
    }
    const notification = payload.notification || {};
    const title = typeof notification.title === 'string' && notification.title
        ? notification.title
        : NOTIFICATION_DEFAULTS.title;
    const body = typeof notification.body === 'string' && notification.body
        ? notification.body
        : NOTIFICATION_DEFAULTS.body;

    event.waitUntil((async () => {
        // Foreground convergence (plan §13.1): when the app is focused, hand
        // the push to the in-app notification center instead of duplicating
        // it as a system notification.
        const clientList = await self.clients.matchAll({
            type: 'window',
            includeUncontrolled: true,
        });
        const focused = clientList.find((client) => client.focused);
        if (focused) {
            focused.postMessage({ type: 'PUSH_RECEIVED', payload });
            return;
        }

        await self.registration.showNotification(title, {
            body,
            lang: notification.lang || NOTIFICATION_DEFAULTS.lang,
            dir: notification.dir || NOTIFICATION_DEFAULTS.dir,
            icon: '/icons/icon-192.png',
            badge: '/icons/icon-192.png',
            tag: typeof notification.tag === 'string' ? notification.tag : 'dentix',
            data: { navigate: notification.navigate || null },
        });
    })());
});

self.addEventListener('notificationclick', (event) => {
    event.notification.close();

    const targetPath = safeNavigationPath(event.notification.data?.navigate || '/');
    event.waitUntil((async () => {
        const clientList = await self.clients.matchAll({
            type: 'window',
            includeUncontrolled: true,
        });
        for (const client of clientList) {
            if (targetPath && 'focus' in client) {
                client.navigate(targetPath).catch(() => {});
                return client.focus();
            }
            if ('focus' in client) return client.focus();
        }
        if (self.clients.openWindow) {
            return self.clients.openWindow(targetPath || '/');
        }
        return undefined;
    })());
});
