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
vi.mock('@/shared/ui', () => ({
    DentixDrawer: ({ open, title, children }) => (
        open ? <div role="dialog" aria-label={title}>{children}</div> : null
    ),
}));
vi.mock('react-i18next', () => ({
    useTranslation: () => ({
        t: (key, options) => {
            const fallbacks = {
                'super_admin.tenant_detail.title': 'تفاصيل العيادة',
                'super_admin.tenant_detail.subtitle': 'إدارة بيانات وموارد المستأجر',
                'super_admin.tenant_detail.reason_placeholder': 'سبب الدخول (5 أحرف على الأقل)',
                'super_admin.tenant_detail.readonly_scope': 'نطاق الجلسة: قراءة فقط (Read-Only)',
                'super_admin.tenant_detail.min_reason': 'الحد الأدنى 5 أحرف',
                'super_admin.tenant_detail.start_impersonation': 'دخول مؤقت للنظام',
                'super_admin.tenant_detail.unnamed': 'بدون اسم',
                'super_admin.tenant_detail.unavailable': 'غير متوفر',
                'super_admin.tenant_detail.no_activity': 'لا يوجد',
            };
            if (key === 'super_admin.tenant_detail.clinic_number') return `عيادة #${options?.id}`;
            return fallbacks[key] || key;
        },
        i18n: { language: 'ar' },
    }),
}));

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

    it('uses the canonical shared drawer and disables impersonation for a short reason', async () => {
        render(<TenantDetailPanel tenantId={10} onClose={mockOnClose} onImpersonate={mockOnImpersonate} />);

        expect(await screen.findByText('Dental Plus')).toBeInTheDocument();
        expect(screen.getByRole('dialog', { name: 'تفاصيل العيادة' })).toBeInTheDocument();

        const button = screen.getByRole('button', { name: 'دخول مؤقت للنظام' });
        expect(button).toBeDisabled();

        const input = screen.getByLabelText('سبب الدخول (5 أحرف على الأقل)');
        fireEvent.change(input, { target: { value: 'help' } });

        expect(button).toBeDisabled();
        expect(screen.getByText('الحد الأدنى 5 أحرف')).toBeInTheDocument();
    });

    it('enables button and triggers onImpersonate with reason and read_only scope on valid input', async () => {
        render(<TenantDetailPanel tenantId={10} onClose={mockOnClose} onImpersonate={mockOnImpersonate} />);

        expect(await screen.findByText('Dental Plus')).toBeInTheDocument();

        const input = screen.getByLabelText('سبب الدخول (5 أحرف على الأقل)');
        fireEvent.change(input, { target: { value: 'استكشاف مشكلة في المواعيد' } });

        const button = screen.getByRole('button', { name: 'دخول مؤقت للنظام' });
        expect(button).not.toBeDisabled();

        fireEvent.click(button);

        expect(mockOnImpersonate).toHaveBeenCalledWith(
            10,
            '',
            'استكشاف مشكلة في المواعيد',
            'read_only',
        );
    });

    it('does not render dead ExternalLink affordances', async () => {
        render(<TenantDetailPanel tenantId={10} onClose={mockOnClose} onImpersonate={mockOnImpersonate} />);

        await screen.findByText('Dental Plus');
        expect(screen.queryByTestId('external-link')).not.toBeInTheDocument();
    });
});
