import { useEffect } from 'react';
import { queryClient } from '@/lib/queryClient';
import {
    CONNECTION_STATES,
    useConnectivityStore,
} from './connectivityStore';
import { probeBackend } from './probeBackend';

const recoveryListeners = new Set();

/**
 * Register a callback invoked once per verified recovery
 * (OFFLINE/DEGRADED -> probe success -> ONLINE).
 */
export function onConnectionRecovered(listener) {
    recoveryListeners.add(listener);
    return () => recoveryListeners.delete(listener);
}

function transition(state) {
    const store = useConnectivityStore.getState();
    const previous = store.state;
    if (previous === state) return;
    store.setState(state);
    if (state === CONNECTION_STATES.ONLINE && previous !== CONNECTION_STATES.ONLINE) {
        // Verified recovery (OFFLINE/DEGRADED -> ... -> ONLINE): revalidate
        // currently mounted read queries once. Mutations are never replayed
        // (React Query does not replay them and the query client keeps
        // retry: false for mutations).
        queryClient.invalidateQueries({ type: 'active' }).catch(() => {});
        recoveryListeners.forEach((listener) => {
            try {
                listener();
            } catch {
                // A broken listener must never break connectivity tracking.
            }
        });
    }
}

async function evaluate() {
    if (typeof navigator !== 'undefined' && navigator.onLine === false) {
        transition(CONNECTION_STATES.OFFLINE);
        return;
    }
    const current = useConnectivityStore.getState().state;
    if (current === CONNECTION_STATES.OFFLINE || current === CONNECTION_STATES.DEGRADED) {
        // Surface the recovery attempt only when recovering from a bad state;
        // background probes from a healthy state stay silent.
        transition(CONNECTION_STATES.RECOVERING);
    }
    const ok = await probeBackend();
    useConnectivityStore.getState().markProbe(ok);
    transition(ok ? CONNECTION_STATES.ONLINE : CONNECTION_STATES.DEGRADED);
}

let controllerStarted = false;

function startController() {
    if (controllerStarted || typeof window === 'undefined') return;
    controllerStarted = true;

    window.addEventListener('offline', () => transition(CONNECTION_STATES.OFFLINE));
    window.addEventListener('online', () => {
        evaluate();
    });
    document.addEventListener('visibilitychange', () => {
        if (document.visibilityState === 'visible') evaluate();
    });
}

/**
 * React binding for the connectivity controller (plan §10.2).
 * Mount once anywhere; the underlying controller is a singleton.
 */
export function useConnectivity() {
    useEffect(() => {
        startController();
    }, []);
}

export { evaluate as evaluateConnectivity };
