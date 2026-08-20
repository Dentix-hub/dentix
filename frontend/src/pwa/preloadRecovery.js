const DEFAULT_RELOAD_KEY = 'dentix:pwa:chunk-reload';
const DEFAULT_COOLDOWN_MS = 30_000;

export function installPreloadRecovery(target = window, options = {}) {
    const storage = options.storage ?? window.sessionStorage;
    const reload = options.reload ?? (() => window.location.reload());
    const now = options.now ?? Date.now;
    const cooldownMs = options.cooldownMs ?? DEFAULT_COOLDOWN_MS;
    const storageKey = options.storageKey ?? DEFAULT_RELOAD_KEY;

    const handlePreloadError = (event) => {
        const currentTime = now();
        const lastReloadValue = storage.getItem(storageKey);
        const lastReload = lastReloadValue === null ? null : Number(lastReloadValue);

        if (lastReload !== null && currentTime - lastReload <= cooldownMs) return;

        event.preventDefault();
        storage.setItem(storageKey, String(currentTime));
        reload();
    };

    target.addEventListener('vite:preloadError', handlePreloadError);
    return () => target.removeEventListener('vite:preloadError', handlePreloadError);
}
