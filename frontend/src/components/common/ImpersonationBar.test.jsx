import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import ImpersonationBar from './ImpersonationBar';

vi.mock('@/lib/queryClient', () => ({
    queryClient: {
        cancelQueries: vi.fn().mockResolvedValue(undefined),
        clear: vi.fn(),
    },
}));

vi.mock('@/store/tenant.store', () => ({
    useTenantStore: {
        getState: () => ({
            clearTenant: vi.fn(),
        }),
    },
}));

describe('ImpersonationBar authentication return and UI states', () => {
    beforeEach(() => {
        vi.clearAllMocks();
        sessionStorage.clear();
        delete window.location;
        window.location = { href: '' };
    });

    it('renders null when there is no active impersonation token', () => {
        const { container } = render(<ImpersonationBar />);
        expect(container.firstChild).toBeNull();
    });

    it('renders simulation banner when impersonation token is present in sessionStorage', () => {
        sessionStorage.setItem('dentix_impersonation_token', 'mock_jwt_token');
        sessionStorage.setItem('dentix_impersonation_tenant', 'Al-Amal Dental');
        sessionStorage.setItem('dentix_impersonation_user', 'dr_amal');
        sessionStorage.setItem('dentix_impersonation_scope', 'read_only');

        render(<ImpersonationBar />);

        expect(screen.getByText(/وضع المحاكاة \(قراءة فقط\)/)).toBeInTheDocument();
        expect(screen.getByText(/عيادة Al-Amal Dental/)).toBeInTheDocument();
        expect(screen.getByText(/dr_amal/)).toBeInTheDocument();
        expect(screen.getByText('العودة للوحة الإشراف')).toBeInTheDocument();
    });

    it('clears impersonation session and redirects to /admin/tenants on return click', async () => {
        sessionStorage.setItem('dentix_impersonation_token', 'mock_jwt_token');
        sessionStorage.setItem('dentix_impersonation_tenant', 'Al-Amal Dental');

        render(<ImpersonationBar />);

        fireEvent.click(screen.getByText('العودة للوحة الإشراف'));

        await waitFor(() => {
            expect(sessionStorage.getItem('dentix_impersonation_token')).toBeNull();
            expect(window.location.href).toBe('/admin/tenants');
        });
    });
});
