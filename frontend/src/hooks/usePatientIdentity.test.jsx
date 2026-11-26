import { act, renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { queryKeys } from '@/lib/queryClient';
import { usePatient } from './usePatientDetails';
import { purgePatientIdentityScopeCache } from './usePatientIdentityAccess';

const { mockGetPatient } = vi.hoisted(() => ({ mockGetPatient: vi.fn() }));

vi.mock('@/api', async (importOriginal) => ({
    ...(await importOriginal()),
    getPatient: mockGetPatient,
}));

function wrapperWith(queryClient) {
    return function Wrapper({ children }) {
        return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>;
    };
}

describe('usePatient identity query', () => {
    beforeEach(() => {
        mockGetPatient.mockReset();
    });

    it('does not retry a terminal access denial', async () => {
        mockGetPatient.mockRejectedValue(Object.assign(new Error('denied'), {
            response: { status: 403, data: { detail: 'Access denied' } },
        }));
        const queryClient = new QueryClient({ defaultOptions: { queries: { retry: 1 } } });

        const { result } = renderHook(
            () => usePatient('123', { tenantKey: 101 }),
            { wrapper: wrapperWith(queryClient) },
        );

        await waitFor(() => expect(result.current.isError).toBe(true));
        expect(mockGetPatient).toHaveBeenCalledTimes(1);
    });

    it('discards stale identity and workspace data while keeping the denial in the active query', async () => {
        const denial = Object.assign(new Error('denied'), { response: { status: 403 } });
        const queryClient = new QueryClient();
        const identityKey = queryKeys.patientIdentity('123', 'clinic-a');
        const workspaceKey = queryKeys.patientClinicalWorkspace('123');
        queryClient.setQueryData(identityKey, { id: 123, name: 'Synthetic Patient' });
        queryClient.setQueryData(workspaceKey, { patient_id: 123 });
        mockGetPatient.mockRejectedValue(denial);

        const { result } = renderHook(() => {
            const { data, error, refetch } = usePatient('123', { tenantKey: 'clinic-a' });
            return { data, error, refetch };
        }, { wrapper: wrapperWith(queryClient) });

        await act(async () => result.current.refetch());
        await waitFor(() => expect(result.current.error).toBe(denial));
        act(() => purgePatientIdentityScopeCache(queryClient, '123'));

        await waitFor(() => expect(result.current.data).toBeUndefined());
        expect(queryClient.getQueryState(identityKey)).toMatchObject({ status: 'error', error: denial });
        expect(queryClient.getQueryData(workspaceKey)).toBeUndefined();
        expect(mockGetPatient).toHaveBeenCalledTimes(1);
    });

    it('isolates the same patient identity cache by active tenant', async () => {
        mockGetPatient.mockImplementation(async (patientId) => ({
            data: { id: Number(patientId), name: 'Synthetic Tenant Patient' },
        }));
        const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
        const wrapper = wrapperWith(queryClient);

        const { result, rerender } = renderHook(
            ({ tenantKey }) => usePatient('123', { tenantKey }),
            { initialProps: { tenantKey: 'tenant-a' }, wrapper },
        );
        await waitFor(() => expect(result.current.isSuccess).toBe(true));

        rerender({ tenantKey: 'tenant-b' });
        await waitFor(() => expect(result.current.isSuccess).toBe(true));

        const keys = queryClient.getQueryCache().getAll().map((query) => query.queryKey);
        expect(keys).toContainEqual(['patient', '123', 'identity', 'tenant-a']);
        expect(keys).toContainEqual(['patient', '123', 'identity', 'tenant-b']);
    });
});
