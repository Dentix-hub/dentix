const DEFAULT_RELOAD_KEY = 'dentix:pwa:chunk-reload';
const DEFAULT_COOLDOWN_MS = 30_000;

async function purgeStaleSwAndReload() {
    try {
        if (typeof navigator !== 'undefined' && 'serviceWorker' in navigator) {
            const registrations = await navigator.serviceWorker.getRegistrations();
            await Promise.all(
                registrations.map((reg) => {
                    if (reg.waiting) {
                        reg.waiting.postMessage({ type: 'SKIP_WAITING' });
                    }
                    return reg.unregister();
                })
            );
        }
        if (typeof window !== 'undefined' && 'caches' in window) {
            const keys = await window.caches.keys();
            await Promise.all(
                keys
                    .filter((k) => k.startsWith('dentix-') || k.startsWith('workbox-'))
                    .map((k) => window.caches.delete(k))
            );
        }
    } catch {
        // Ignore cleanup failures and proceed with reload
    }
    window.location.reload();
}

export function installPreloadRecovery(target = window, options = {}) {
    let defaultStorage = null;
    try {
        defaultStorage = typeof window !== 'undefined' ? window.sessionStorage : null;
    } catch {
        defaultStorage = null;
    }
    const storage = options.storage ?? defaultStorage;
    const reload = options.reload ?? (() => { void purgeStaleSwAndReload(); });
    const now = options.now ?? Date.now;
    const cooldownMs = options.cooldownMs ?? DEFAULT_COOLDOWN_MS;
    const storageKey = options.storageKey ?? DEFAULT_RELOAD_KEY;

    const handlePreloadError = (event) => {
        const currentTime = now();
        let lastReload = null;
        try {
            const lastReloadValue = storage?.getItem(storageKey);
            lastReload = lastReloadValue === null ? null : Number(lastReloadValue);
        } catch {
            lastReload = null;
        }

        if (lastReload !== null && currentTime - lastReload <= cooldownMs) return;

        event.preventDefault();
        try {
            storage?.setItem(storageKey, String(currentTime));
        } catch {
            // Storage access might be restricted
        }
        reload();
    };

    target.addEventListener('vite:preloadError', handlePreloadError);
    return () => target.removeEventListener('vite:preloadError', handlePreloadError);
}
