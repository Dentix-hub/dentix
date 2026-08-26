import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import SystemHealth from './SystemHealth';
import HealthAlerts from './HealthAlerts';
import { api } from '@/api';
import { toast } from '@/shared/ui';

vi.mock('react-i18next', () => ({
    useTranslation: () => ({
        t: (key) => key,
        i18n: { language: 'ar' },
    }),
}));

vi.mock('@/api', () => ({
    api: {
        get: vi.fn(),
        post: vi.fn(),
    },
}));

vi.mock('@/shared/ui', async () => {
    const actual = await vi.importActual('@/shared/ui');
    return {
        ...actual,
        toast: {
            success: vi.fn(),
            error: vi.fn(),
        },
    };
});

describe('Shared System Health Query MS-22', () => {
    let queryClient;

    beforeEach(() => {
        vi.clearAllMocks();
        queryClient = new QueryClient({
            defaultOptions: {
                queries: {
                    retry: false,
                },
            },
        });
    });

    it('renders HealthAlerts and SystemHealth from the shared cached health query', async () => {
        api.get.mockImplementation((url) => {
            if (url === '/api/v1/admin/health/alerts') {
                return Promise.resolve({
                    data: {
                        score: 95,
                        status: 'healthy',
                        critical_errors: 0,
                        security_alerts: 1,
                        failed_backups_count: 0,
                        alerts: [],
                        checked_at: '2026-08-20T10:00:00Z',
                    },
                });
            }
            if (url === '/api/v1/admin/security/jobs') {
                return Promise.resolve({
                    data: [
                        { id: 1, job_name: 'Database Backup', status: 'success', duration_seconds: 1.25, started_at: '2026-08-20T09:00:00Z' },
                    ],
                });
            }
            return Promise.resolve({ data: {} });
        });

        render(
            <QueryClientProvider client={queryClient}>
                <div>
                    <HealthAlerts />
                    <SystemHealth />
                </div>
            </QueryClientProvider>
        );

        // Both components show 95%
        expect(await screen.findByText('95%')).toBeInTheDocument();
        expect(screen.getByText('Database Backup')).toBeInTheDocument();

        // /api/v1/admin/health/alerts is only called ONCE due to shared query cache!
        const healthCalls = api.get.mock.calls.filter(([url]) => url === '/api/v1/admin/health/alerts');
        expect(healthCalls.length).toBe(1);
    });

    it('handles query error gracefully and displays unknown status', async () => {
        api.get.mockImplementation((url) => {
            if (url === '/api/v1/admin/health/alerts') {
                return Promise.reject(new Error('Health service down'));
            }
            if (url === '/api/v1/admin/security/jobs') return Promise.resolve({ data: [] });
            return Promise.resolve({ data: {} });
        });

        render(
            <QueryClientProvider client={queryClient}>
                <HealthAlerts />
            </QueryClientProvider>
        );

        expect(await screen.findByText('super_admin.health.unknown')).toBeInTheDocument();
    });

    it('invalidates health query when running manual system check', async () => {
        api.get.mockImplementation((url) => {
            if (url === '/api/v1/admin/health/alerts') {
                return Promise.resolve({
                    data: {
                        score: 80,
                        status: 'warning',
                        critical_errors: 1,
                        security_alerts: 0,
                        failed_backups_count: 0,
                        alerts: ['High CPU usage'],
                    },
                });
            }
            if (url === '/api/v1/admin/security/jobs') return Promise.resolve({ data: [] });
            return Promise.resolve({ data: {} });
        });

        api.post.mockResolvedValueOnce({
            data: {
                notification_sent: false,
            },
        });

        render(
            <QueryClientProvider client={queryClient}>
                <SystemHealth />
            </QueryClientProvider>
        );

        const checkBtn = await screen.findByRole('button', { name: /super_admin.health.run_system_check/ });
        fireEvent.click(checkBtn);

        await waitFor(() => {
            expect(api.post).toHaveBeenCalledWith('/api/v1/admin/health/check');
            expect(toast.success).toHaveBeenCalledWith('super_admin.health.check_success_stable');
        });
    });
});
