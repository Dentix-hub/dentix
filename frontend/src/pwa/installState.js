import { create } from 'zustand';
import { isStandalone } from './platform';

const DISMISSAL_KEY = 'dentix:pwa:install-dismissed-at';
const INSTALLED_KEY = 'dentix:pwa:app-installed';
// Do not nag: after a dismissal, stay quiet for a week (plan §9.2).
export const INSTALL_DISMISSAL_COOLDOWN_MS = 7 * 24 * 60 * 60 * 1000;
// Never prompt at first paint; require a short engagement dwell first.
export const INSTALL_ENGAGEMENT_DELAY_MS = 20 * 1000;

function readTimestamp(key) {
    if (typeof window === 'undefined') return null;
    try {
        const raw = window.localStorage?.getItem(key);
        if (!raw) return null;
        const value = Number(raw);
        return Number.isFinite(value) ? value : null;
    } catch {
        return null;
    }
}

function writeTimestamp(key, value) {
    if (typeof window === 'undefined') return;
    try {
        if (value === null) window.localStorage?.removeItem(key);
        else window.localStorage?.setItem(key, String(value));
    } catch {
        // Storage may be unavailable (private mode); state stays in memory.
    }
}

export function syncInstalledStatus() {
    const raw = readTimestamp(INSTALLED_KEY);
    if (raw !== null) {
        if (!isStandalone()) {
            writeTimestamp(INSTALLED_KEY, null);
            return false;
        }
        return true;
    }
    return false;
}

/**
 * Client state for the install manager (plan §9.1).
 * Persisted bits: last dismissal per surface + appinstalled receipt.
 */
export const useInstallStore = create((set, get) => ({
    promptAvailable: false,
    installed: syncInstalledStatus(),
    androidDismissedAt: readTimestamp(`${DISMISSAL_KEY}:android`),
    iosDismissedAt: readTimestamp(`${DISMISSAL_KEY}:ios`),
    inAppDismissedAt: readTimestamp(`${DISMISSAL_KEY}:inapp`),

    syncInstalledState: () => {
        const installed = syncInstalledStatus();
        set({ installed });
        return installed;
    },
    markPromptAvailable: () => set({ promptAvailable: true }),
    markInstalled: () => {
        writeTimestamp(INSTALLED_KEY, Date.now());
        set({ installed: true, promptAvailable: false });
    },
    dismiss: (surface) => {
        const at = Date.now();
        writeTimestamp(`${DISMISSAL_KEY}:${surface}`, at);
        if (surface === 'ios') set({ iosDismissedAt: at });
        else if (surface === 'inapp') set({ inAppDismissedAt: at });
        else set({ androidDismissedAt: at });
    },
    resetForTests: () => set({
        promptAvailable: false,
        installed: syncInstalledStatus(),
        androidDismissedAt: null,
        iosDismissedAt: null,
        inAppDismissedAt: null,
    }),
    isDismissalCooldownActive: (surface) => {
        let dismissedAt;
        if (surface === 'ios') dismissedAt = get().iosDismissedAt;
        else if (surface === 'inapp') dismissedAt = get().inAppDismissedAt;
        else dismissedAt = get().androidDismissedAt;
        if (!dismissedAt) return false;
        return Date.now() - dismissedAt < INSTALL_DISMISSAL_COOLDOWN_MS;
    },
}));
