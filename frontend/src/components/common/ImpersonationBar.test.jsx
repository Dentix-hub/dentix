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

vi.mock('react-i18next', () => ({
    useTranslation: () => ({
        t: (key, options = {}) => {
            const values = {
                'super_admin.impersonation.read_only': 'قراءة فقط',
                'super_admin.impersonation.full_access': 'وصول كامل',
                'super_admin.impersonation.tenant_fallback': 'المستأجر',
                'super_admin.impersonation.return': 'العودة للوحة الإشراف',
            };
            if (key === 'super_admin.impersonation.banner') {
                return `وضع المحاكاة (${options.scope}): عيادة ${options.tenant}${options.user || ''}`;
            }
            return values[key] || key;
        },
    }),
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

    it('renders localized simulation banner when impersonation token is active', () => {
        sessionStorage.setItem('dentix_impersonation_token', 'mock_jwt_token');
        sessionStorage.setItem('dentix_impersonation_tenant', 'Al-Amal Dental');
        sessionStorage.setItem('dentix_impersonation_user', 'dr_amal');
        sessionStorage.setItem('dentix_impersonation_scope', 'read_only');

        render(<ImpersonationBar />);

        expect(screen.getByText(/وضع المحاكاة \(قراءة فقط\)/)).toBeInTheDocument();
        expect(screen.getByText(/Al-Amal Dental/)).toBeInTheDocument();
        expect(screen.getByText(/dr_amal/)).toBeInTheDocument();
        expect(screen.getByRole('button', { name: 'العودة للوحة الإشراف' })).toBeInTheDocument();
    });

    it('clears impersonation session and redirects to /admin/tenants on return click', async () => {
        sessionStorage.setItem('dentix_impersonation_token', 'mock_jwt_token');
        sessionStorage.setItem('dentix_impersonation_tenant', 'Al-Amal Dental');

        render(<ImpersonationBar />);
        fireEvent.click(screen.getByRole('button', { name: 'العودة للوحة الإشراف' }));

        await waitFor(() => {
            expect(sessionStorage.getItem('dentix_impersonation_token')).toBeNull();
            expect(window.location.href).toBe('/admin/tenants');
        });
    });
});
