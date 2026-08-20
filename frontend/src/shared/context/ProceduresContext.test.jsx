import { render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { getProcedures } from '@/api';
import { useAuth } from '@/auth/useAuth';
import { ProceduresProvider, useProcedures } from './ProceduresContext';

vi.mock('@/api', () => ({
    getProcedures: vi.fn(),
}));

vi.mock('@/auth/useAuth', () => ({
    useAuth: vi.fn(),
}));

function ProceduresProbe() {
    const { procedures, loading } = useProcedures();
    return <div>{loading ? 'loading' : `procedures:${procedures.map((procedure) => procedure.id).join(',')}`}</div>;
}

describe('ProceduresProvider', () => {
    beforeEach(() => {
        vi.clearAllMocks();
    });

    it('does not call the tenant-scoped endpoint for a platform user', async () => {
        useAuth.mockReturnValue({ user: { id: 1, role: 'super_admin', tenant_id: null } });

        render(
            <ProceduresProvider>
                <ProceduresProbe />
            </ProceduresProvider>
        );

        expect(await screen.findByText('procedures:')).toBeInTheDocument();
        expect(getProcedures).not.toHaveBeenCalled();
    });

    it('fetches procedures when an authenticated user has a tenant', async () => {
        useAuth.mockReturnValue({ user: { id: 2, role: 'admin', tenant_id: 7 } });
        getProcedures.mockResolvedValue({ data: [{ id: 10, name: 'Filling' }] });

        render(
            <ProceduresProvider>
                <ProceduresProbe />
            </ProceduresProvider>
        );

        await waitFor(() => expect(screen.getByText('procedures:10')).toBeInTheDocument());
        expect(getProcedures).toHaveBeenCalledTimes(1);
    });

    it('does not reuse cached procedures after the tenant changes', async () => {
        let currentUser = { id: 2, role: 'admin', tenant_id: 7 };
        useAuth.mockImplementation(() => ({ user: currentUser }));
        getProcedures
            .mockResolvedValueOnce({ data: [{ id: 10, name: 'Tenant 7 procedure' }] })
            .mockResolvedValueOnce({ data: [{ id: 20, name: 'Tenant 8 procedure' }] });

        const { rerender } = render(
            <ProceduresProvider>
                <ProceduresProbe />
            </ProceduresProvider>
        );

        await screen.findByText('procedures:10');
        currentUser = { id: 3, role: 'admin', tenant_id: 8 };
        rerender(
            <ProceduresProvider>
                <ProceduresProbe />
            </ProceduresProvider>
        );

        await screen.findByText('procedures:20');
        expect(getProcedures).toHaveBeenCalledTimes(2);
    });
});
