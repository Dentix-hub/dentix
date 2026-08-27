import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import TenantsPage from './TenantsPage';
import UsersPage from './UsersPage';
import { api } from '@/api';

vi.mock('react-i18next', () => ({
    useTranslation: () => ({
        t: (key, fallback) => fallback || key,
        i18n: { language: 'ar' },
    }),
}));

vi.mock('@/api', () => ({
    api: {
        get: vi.fn(),
        post: vi.fn(),
        delete: vi.fn(),
    },
}));

vi.mock('@/utils/logger', () => ({ default: { error: vi.fn(), log: vi.fn() } }));

describe('Tenants and Users UI Consistency MS-30', () => {
    beforeEach(() => {
        vi.clearAllMocks();
    });

    describe('TenantsPage & TenantsManager', () => {
        it('renders tenants and handles archive and permanent delete confirmations safely', async () => {
            api.get.mockImplementation((url) => {
                if (url.includes('/admin/tenants')) {
                    return Promise.resolve({
                        data: [
                            { id: 1, name: 'عيادة الأمل', domain: 'alamal', plan: 'pro', is_active: true, is_deleted: false, total_revenue: 1000 },
                            { id: 2, name: 'عيادة الشفاء', domain: null, plan: 'basic', is_active: false, is_deleted: true, total_revenue: 0 },
                        ],
                    });
                }
                if (url.includes('/admin/subscriptions/plans')) {
                    return Promise.resolve({
                        data: [
                            { id: 10, name: 'Pro Plan', display_name_ar: 'الخطة المتقدمة', duration_days: 30 },
                        ],
                    });
                }
                return Promise.resolve({ data: [] });
            });

            render(
                <MemoryRouter>
                    <TenantsPage />
                </MemoryRouter>
            );

            expect(await screen.findByText('عيادة الأمل')).toBeInTheDocument();
            expect(screen.getByText('alamal.dentix.com')).toBeInTheDocument();
            expect(screen.getByText('عيادة الشفاء')).toBeInTheDocument();

            // 1. Test Archive Trigger
            const archiveBtn = screen.getByTitle('أرشفة العيادة (قابلة للاستعادة)');
            fireEvent.click(archiveBtn);

            expect(screen.getByText('أرشفة العيادة')).toBeInTheDocument();
            expect(screen.getByText('هل أنت متأكد من أرشفة هذه العيادة؟ يمكنك استعادتها وتفعيلها لاحقاً.')).toBeInTheDocument();

            api.delete.mockResolvedValue({ message: 'Archived' });
            const confirmArchiveBtn = screen.getByRole('button', { name: 'أرشفة' });
            fireEvent.click(confirmArchiveBtn);

            await waitFor(() => {
                expect(api.delete).toHaveBeenCalledWith('/api/v1/admin/tenants/1');
            });
        });

        it('handles manual renewal with internal auto-generated idempotency key without raw input', async () => {
            api.get.mockImplementation((url) => {
                if (url.includes('/admin/tenants')) {
                    return Promise.resolve({
                        data: [
                            { id: 5, name: 'عيادة الابتسامة', plan_id: 10, is_active: true, is_deleted: false },
                        ],
                    });
                }
                if (url.includes('/admin/subscriptions/plans')) {
                    return Promise.resolve({
                        data: [
                            { id: 10, name: 'Pro Plan', display_name_ar: 'الخطة المتقدمة', duration_days: 30 },
                        ],
                    });
                }
                return Promise.resolve({ data: [] });
            });

            render(
                <MemoryRouter>
                    <TenantsPage />
                </MemoryRouter>
            );

            const renewBtn = await screen.findByTitle('تجديد اشتراك يدوي');
            fireEvent.click(renewBtn);

            expect(screen.getByText('تجديد اشتراك يدوي موثق')).toBeInTheDocument();

            // Verify idempotency key input is NOT shown to the user
            expect(screen.queryByText('مفتاح عدم التكرار (Idempotency Key)')).not.toBeInTheDocument();

            api.post.mockResolvedValue({ message: 'Renewed successfully' });
            const submitBtn = screen.getByRole('button', { name: 'تأكيد وتوثيق التجديد' });
            fireEvent.click(submitBtn);

            await waitFor(() => {
                expect(api.post).toHaveBeenCalledWith(
                    '/api/v1/admin/tenants/5/renew',
                    expect.objectContaining({
                        plan_id: 10,
                        extension_days: 30,
                        idempotency_key: expect.stringMatching(/^manual_renew_5_\d+_/),
                    })
                );
            });
        });
    });

    describe('UsersPage & UsersManager', () => {
        it('searches users with Axios params and toggles status with ConfirmDialog', async () => {
            api.get.mockResolvedValue({
                data: [
                    { id: 20, username: 'dr_sarah', email: 'sarah@dentix.com', role: 'doctor', is_active: true, tenant_name: 'Al-Amal' },
                ],
            });

            render(
                <MemoryRouter>
                    <UsersPage />
                </MemoryRouter>
            );

            expect(await screen.findByText('dr_sarah')).toBeInTheDocument();
            expect(screen.getByText('طبيب')).toBeInTheDocument();

            // Search with term
            const searchInput = screen.getByPlaceholderText('البحث بالاسم أو البريد الإلكتروني...');
            fireEvent.change(searchInput, { target: { value: 'sarah' } });
            const searchBtn = screen.getByRole('button', { name: 'بحث' });
            fireEvent.click(searchBtn);

            await waitFor(() => {
                expect(api.get).toHaveBeenCalledWith('/api/v1/admin/users', {
                    params: { search_query: 'sarah' },
                });
            });

            // Toggle status confirmation
            const toggleBtn = screen.getByRole('button', { name: 'تعطيل' });
            fireEvent.click(toggleBtn);

            expect(screen.getByText('تغيير حالة المستخدم')).toBeInTheDocument();

            api.post.mockResolvedValue({ message: 'Status toggled' });
            const confirmToggleBtn = screen.getByRole('button', { name: 'تعطيل' });
            fireEvent.click(confirmToggleBtn);

            await waitFor(() => {
                expect(api.post).toHaveBeenCalledWith('/api/v1/admin/users/20/toggle-status');
            });
        });
    });
});
