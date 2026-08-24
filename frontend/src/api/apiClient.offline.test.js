import { beforeEach, describe, expect, it } from 'vitest';
import { CONNECTION_STATES, useConnectivityStore } from '../pwa/connectivity/connectivityStore';
import { api, createOfflineWriteError } from './apiClient';

describe('offline write guard (plan §10.4)', () => {
    beforeEach(() => {
        useConnectivityStore.getState().resetForTests();
    });

    it('rejects state-changing requests immediately while confirmed offline', async () => {
        useConnectivityStore.getState().setState(CONNECTION_STATES.OFFLINE);

        await expect(api.post('/api/v1/payments', { amount: 100 })).rejects.toMatchObject({
            isOfflineWriteBlock: true,
            code: 'OFFLINE_WRITE_BLOCKED',
        });
        await expect(api.delete('/api/v1/patients/1')).rejects.toBeInstanceOf(Error);
    });

    it('never queues or replays the blocked write', async () => {
        useConnectivityStore.getState().setState(CONNECTION_STATES.OFFLINE);

        let caught = null;
        try {
            await api.post('/api/v1/inventory/movements', { qty: 2 });
        } catch (error) {
            caught = error;
        }
        expect(caught).toBeInstanceOf(Error);
        expect(caught.isOfflineWriteBlock).toBe(true);
        expect(caught).not.toBe(createOfflineWriteError.__queued);
    });

    it('keeps read requests and auth endpoints unaffected', async () => {
        useConnectivityStore.getState().setState(CONNECTION_STATES.OFFLINE);

        // GET passes the guard (it will fail later at transport level in jsdom,
        // but must NOT be rejected by the offline write blocker).
        let getError = null;
        try {
            await api.get('/api/v1/patients');
        } catch (error) {
            getError = error;
        }
        expect(getError?.isOfflineWriteBlock ?? false).toBe(false);

        // Logout stays exempt so a user is never trapped by the guard.
        let logoutError = null;
        try {
            await api.post('/api/v1/auth/logout', null);
        } catch (error) {
            logoutError = error;
        }
        expect(logoutError?.isOfflineWriteBlock ?? false).toBe(false);
    });

    it('allows writes again once connectivity is restored', async () => {
        useConnectivityStore.getState().setState(CONNECTION_STATES.OFFLINE);
        await expect(api.post('/api/v1/payments', {})).rejects.toMatchObject({
            isOfflineWriteBlock: true,
        });

        useConnectivityStore.getState().setState(CONNECTION_STATES.ONLINE);
        let error = null;
        try {
            await api.post('/api/v1/payments', {});
        } catch (err) {
            error = err;
        }
        // Transport will fail in jsdom, but the offline guard must not be the rejector.
        expect(error?.isOfflineWriteBlock ?? false).toBe(false);
    });
});
