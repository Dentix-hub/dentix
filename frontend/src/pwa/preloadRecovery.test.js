import { afterEach, describe, expect, it, vi } from 'vitest';
import { installPreloadRecovery } from './preloadRecovery';

describe('installPreloadRecovery', () => {
    afterEach(() => {
        window.sessionStorage.clear();
    });

    it('prevents the stale chunk error and reloads at most once per cooldown', () => {
        let now = 1_000;
        const reload = vi.fn();
        const cleanup = installPreloadRecovery(window, {
            now: () => now,
            reload,
            storage: window.sessionStorage,
            cooldownMs: 30_000,
        });

        const firstError = new Event('vite:preloadError', { cancelable: true });
        window.dispatchEvent(firstError);
        expect(firstError.defaultPrevented).toBe(true);
        expect(reload).toHaveBeenCalledTimes(1);

        const suppressedError = new Event('vite:preloadError', { cancelable: true });
        window.dispatchEvent(suppressedError);
        expect(suppressedError.defaultPrevented).toBe(false);
        expect(reload).toHaveBeenCalledTimes(1);

        now += 30_001;
        const afterCooldown = new Event('vite:preloadError', { cancelable: true });
        window.dispatchEvent(afterCooldown);
        expect(afterCooldown.defaultPrevented).toBe(true);
        expect(reload).toHaveBeenCalledTimes(2);

        cleanup();
        const afterCleanup = new Event('vite:preloadError', { cancelable: true });
        window.dispatchEvent(afterCleanup);
        expect(afterCleanup.defaultPrevented).toBe(false);
    });
});
