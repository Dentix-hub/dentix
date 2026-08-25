import { useEffect } from 'react';

// Keep long-lived installed sessions aware of new deployments without
// activating an update behind the user's back. The service worker remains in
// `waiting` until the existing update prompt calls updateServiceWorker(true).
export const PWA_UPDATE_CHECK_INTERVAL_MS = 60 * 60 * 1000;
export const PWA_UPDATE_CHECK_THROTTLE_MS = 60 * 1000;

export function usePwaUpdateChecks(registration) {
  useEffect(() => {
    if (!registration) return undefined;

    let lastCheckAt = Number.NEGATIVE_INFINITY;

    const checkForUpdate = () => {
      if (typeof navigator !== 'undefined' && navigator.onLine === false) return;
      if (typeof document !== 'undefined' && document.visibilityState === 'hidden') return;
      if (registration.installing) return;

      const now = Date.now();
      if (now - lastCheckAt < PWA_UPDATE_CHECK_THROTTLE_MS) return;
      lastCheckAt = now;

      try {
        registration.update().catch(() => {
          // A transient update-check failure must not interrupt clinical work.
          // The next resume, reconnect, or periodic check will retry.
        });
      } catch {
        // Browsers can throw while a registration is being torn down. A later
        // lifecycle trigger will retry without surfacing a user-facing error.
      }
    };

    const handleVisibilityChange = () => {
      if (document.visibilityState === 'visible') checkForUpdate();
    };

    const intervalId = window.setInterval(checkForUpdate, PWA_UPDATE_CHECK_INTERVAL_MS);
    document.addEventListener('visibilitychange', handleVisibilityChange);
    window.addEventListener('focus', checkForUpdate);
    window.addEventListener('online', checkForUpdate);

    return () => {
      window.clearInterval(intervalId);
      document.removeEventListener('visibilitychange', handleVisibilityChange);
      window.removeEventListener('focus', checkForUpdate);
      window.removeEventListener('online', checkForUpdate);
    };
  }, [registration]);
}
