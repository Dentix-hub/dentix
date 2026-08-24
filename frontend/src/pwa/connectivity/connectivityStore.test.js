import { beforeEach, describe, expect, it } from 'vitest';
import {
    CONNECTION_STATES,
    isConfirmedOffline,
    useConnectivityStore,
} from './connectivityStore';

describe('connectivity store', () => {
    beforeEach(() => {
        useConnectivityStore.getState().resetForTests();
    });

    it('starts ONLINE by default and tracks probe results', () => {
        expect(useConnectivityStore.getState().state).toBe(CONNECTION_STATES.ONLINE);

        useConnectivityStore.getState().markProbe(true);
        expect(useConnectivityStore.getState().lastProbeOk).toBe(true);
        expect(useConnectivityStore.getState().lastProbeAt).toBeGreaterThan(0);
    });

    it('exposes confirmed-offline only for the OFFLINE state', () => {
        useConnectivityStore.getState().setState(CONNECTION_STATES.OFFLINE);
        expect(isConfirmedOffline()).toBe(true);

        useConnectivityStore.getState().setState(CONNECTION_STATES.DEGRADED);
        expect(isConfirmedOffline()).toBe(false);

        useConnectivityStore.getState().setState(CONNECTION_STATES.RECOVERING);
        expect(isConfirmedOffline()).toBe(false);
    });
});
