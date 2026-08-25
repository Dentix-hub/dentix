import { render, screen, fireEvent } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import TenantDetailPanel from './TenantDetailPanel';

const apiMocks = vi.hoisted(() => ({
    apiGet: vi.fn(),
}));

vi.mock('@/api', () => ({
    api: {
        get: apiMocks.apiGet,
    },
}));

vi.mock('@/utils/logger', () => ({ default: { error: vi.fn() } }));

describe('TenantDetailPanel impersonation contract and UI safety', () => {
    const mockOnImpersonate = vi.fn();
    const mockOnClose = vi.fn();

    beforeEach(() => {
        vi.clearAllMocks();
        apiMocks.apiGet.mockImplementation((url) => {
            if (url.includes('/details')) {
                return Promise.resolve({
                    data: {
                        tenant: { id: 10, name: 'Dental Plus', domain: 'plus', plan: 'pro' },
                        stats: { patients_count: 50, appointments_count: 100, total_revenue: 15000 },
                    },
                });
            }
            if (url.includes('/users')) {
                return Promise.resolve({
                    data: {
                        users: [
                            { id: 1, username: 'dr_sarah', email: 'sarah@plus.com', role: 'doctor', is_active: true },
                        ],
                    },
                });
            }
            return Promise.resolve({ data: {} });
        });
    });

    it('disables impersonation button when reason is less than 5 characters', async () => {
        render(<TenantDetailPanel tenantId={10} onClose={mockOnClose} onImpersonate={mockOnImpersonate} />);

        expect(await screen.findByText('Dental Plus')).toBeInTheDocument();

        const button = screen.getByText('دخول مؤقت للنظام').closest('button');
        expect(button).toBeDisabled();

        const input = screen.getByPlaceholderText(/سبب الدخول/);
        fireEvent.change(input, { target: { value: 'help' } }); // 4 chars

        expect(button).toBeDisabled();
        expect(screen.getByText('الحد الأدنى 5 أحرف')).toBeInTheDocument();
    });

    it('enables button and triggers onImpersonate with reason and read_only scope on valid input', async () => {
        render(<TenantDetailPanel tenantId={10} onClose={mockOnClose} onImpersonate={mockOnImpersonate} />);

        expect(await screen.findByText('Dental Plus')).toBeInTheDocument();

        const input = screen.getByPlaceholderText(/سبب الدخول/);
        fireEvent.change(input, { target: { value: 'استكشاف مشكلة في المواعيد' } });

        const button = screen.getByText('دخول مؤقت للنظام').closest('button');
        expect(button).not.toBeDisabled();

        fireEvent.click(button);

        expect(mockOnImpersonate).toHaveBeenCalledWith(
            10,
            '',
            'استكشاف مشكلة في المواعيد',
            'read_only'
        );
    });

    it('does not render dead ExternalLink icon/button', async () => {
        render(<TenantDetailPanel tenantId={10} onClose={mockOnClose} onImpersonate={mockOnImpersonate} />);

        await screen.findByText('Dental Plus');
        expect(screen.queryByTestId('external-link')).not.toBeInTheDocument();
    });
});
