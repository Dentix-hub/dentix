import { act, render } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { CONNECTION_STATES, useConnectivityStore } from './connectivityStore';
import { onConnectionRecovered } from './useConnectivity';

const probeMocks = vi.hoisted(() => ({
    probeBackend: vi.fn(),
}));

vi.mock('./probeBackend', () => ({
    probeBackend: probeMocks.probeBackend,
}));

vi.mock('@/lib/queryClient', () => ({
    queryClient: {
        invalidateQueries: vi.fn().mockResolvedValue(undefined),
    },
}));

import { queryClient } from '@/lib/queryClient';
import { evaluateConnectivity, useConnectivity } from './useConnectivity';

function HookProbe() {
    useConnectivity();
    return null;
}

async function setOnline() {
    await act(async () => {
        useConnectivityStore.setState({ state: CONNECTION_STATES.ONLINE });
    });
}

describe('connectivity controller', () => {
    beforeEach(() => {
        vi.clearAllMocks();
        useConnectivityStore.getState().resetForTests();
        probeMocks.probeBackend.mockResolvedValue(true);
    });

    afterEach(() => {
        vi.restoreAllMocks();
    });

    it('goes OFFLINE immediately on the browser offline event', async () => {
        render(<HookProbe />);
        await setOnline();

        await act(async () => {
            window.dispatchEvent(new Event('offline'));
        });
        expect(useConnectivityStore.getState().state).toBe(CONNECTION_STATES.OFFLINE);
    });

    it('recovers to ONLINE only after a successful backend probe', async () => {
        render(<HookProbe />);
        await act(async () => {
            useConnectivityStore.setState({ state: CONNECTION_STATES.OFFLINE });
        });

        probeMocks.probeBackend.mockResolvedValue(true);
        await act(async () => {
            await evaluateConnectivity();
        });
        expect(useConnectivityStore.getState().state).toBe(CONNECTION_STATES.ONLINE);
        expect(queryClient.invalidateQueries).toHaveBeenCalledWith({ type: 'active' });
    });

    it('lands in DEGRADED when the network is up but the backend is unreachable', async () => {
        render(<HookProbe />);
        await act(async () => {
            useConnectivityStore.setState({ state: CONNECTION_STATES.OFFLINE });
        });

        probeMocks.probeBackend.mockResolvedValue(false);
        await act(async () => {
            await evaluateConnectivity();
        });
        expect(useConnectivityStore.getState().state).toBe(CONNECTION_STATES.DEGRADED);
        expect(queryClient.invalidateQueries).not.toHaveBeenCalled();
    });

    it('does not invalidate queries on silent healthy-state probes', async () => {
        render(<HookProbe />);
        await setOnline();

        await act(async () => {
            await evaluateConnectivity();
        });
        expect(queryClient.invalidateQueries).not.toHaveBeenCalled();
        expect(useConnectivityStore.getState().state).toBe(CONNECTION_STATES.ONLINE);
    });

    it('notifies recovery listeners exactly once per verified recovery', async () => {
        const listener = vi.fn();
        const unsubscribe = onConnectionRecovered(listener);
        render(<HookProbe />);
        await act(async () => {
            useConnectivityStore.setState({ state: CONNECTION_STATES.DEGRADED });
        });

        await act(async () => {
            await evaluateConnectivity();
        });
        expect(listener).toHaveBeenCalledTimes(1);

        unsubscribe();
    });
});
