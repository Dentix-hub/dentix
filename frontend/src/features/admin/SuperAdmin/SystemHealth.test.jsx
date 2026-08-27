import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import SystemHealth from './SystemHealth';
import HealthAlerts from './HealthAlerts';
import { api } from '@/api';

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

describe('SystemHealth and Background Jobs (MS-22 & MS-23)', () => {
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

    it('handles zero jobs without claiming 100% fake success rate (MS-23)', async () => {
        api.get.mockImplementation((url) => {
            if (url === '/api/v1/admin/health/alerts') {
                return Promise.resolve({ data: { score: 90, status: 'healthy', alerts: [] } });
            }
            if (url === '/api/v1/admin/security/jobs') return Promise.resolve({ data: [] });
            return Promise.resolve({ data: {} });
        });

        render(
            <QueryClientProvider client={queryClient}>
                <SystemHealth />
            </QueryClientProvider>
        );

        expect(await screen.findByText('super_admin.health.no_jobs')).toBeInTheDocument();
        // Rate is "—" for zero jobs
        const dashes = screen.getAllByText('—');
        expect(dashes.length).toBeGreaterThan(0);
    });

    it('handles jobs fetch error with distinct error state and retry button (MS-23)', async () => {
        api.get.mockImplementation((url) => {
            if (url === '/api/v1/admin/health/alerts') {
                return Promise.resolve({ data: { score: 90, status: 'healthy', alerts: [] } });
            }
            if (url === '/api/v1/admin/security/jobs') {
                return Promise.reject(new Error('Jobs DB connection timeout'));
            }
            return Promise.resolve({ data: {} });
        });

        render(
            <QueryClientProvider client={queryClient}>
                <SystemHealth />
            </QueryClientProvider>
        );

        expect(await screen.findByText(/Jobs DB connection timeout/)).toBeInTheDocument();
        expect(screen.getByRole('button', { name: 'common.retry' })).toBeInTheDocument();
    });

    it('safely formats null duration and unassigned fields in jobs table (MS-23)', async () => {
        api.get.mockImplementation((url) => {
            if (url === '/api/v1/admin/health/alerts') {
                return Promise.resolve({ data: { score: 90, status: 'healthy', alerts: [] } });
            }
            if (url === '/api/v1/admin/security/jobs') {
                return Promise.resolve({
                    data: [
                        { id: 2, job_name: null, status: 'running', duration_seconds: null, triggered_by: null, started_at: null },
                    ],
                });
            }
            return Promise.resolve({ data: {} });
        });

        render(
            <QueryClientProvider client={queryClient}>
                <SystemHealth />
            </QueryClientProvider>
        );

        expect(await screen.findByText('super_admin.health.unnamed_job')).toBeInTheDocument();
        expect(screen.getByText('super_admin.health.status_running')).toBeInTheDocument();
        expect(screen.getByText('system')).toBeInTheDocument();
    });
});
