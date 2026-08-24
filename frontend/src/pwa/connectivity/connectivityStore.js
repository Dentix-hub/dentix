import { create } from 'zustand';

/**
 * Explicit connection states (plan §10.1).
 * navigator.onLine alone is never trusted: Wi-Fi can be up while the backend
 * is unreachable, which is DEGRADED, not healthy.
 */
export const CONNECTION_STATES = Object.freeze({
    ONLINE: 'ONLINE',
    DEGRADED: 'DEGRADED',
    OFFLINE: 'OFFLINE',
    RECOVERING: 'RECOVERING',
});

/**
 * Single centralized connectivity state source (plan §10.2).
 * The axios write guard, the status banner and the reconnect revalidation all
 * read from here instead of ad-hoc navigator.onLine checks.
 */
export const useConnectivityStore = create((set) => ({
    state: typeof navigator !== 'undefined' && navigator.onLine === false
        ? CONNECTION_STATES.OFFLINE
        : CONNECTION_STATES.ONLINE,
    lastProbeAt: null,
    lastProbeOk: null,

    setState: (state) => set({ state }),
    markProbe: (ok) => set({ lastProbeAt: Date.now(), lastProbeOk: ok }),
    resetForTests: () => set({
        state: CONNECTION_STATES.ONLINE,
        lastProbeAt: null,
        lastProbeOk: null,
    }),
}));

export function getConnectionState() {
    return useConnectivityStore.getState().state;
}

export function isConfirmedOffline() {
    return getConnectionState() === CONNECTION_STATES.OFFLINE;
}
