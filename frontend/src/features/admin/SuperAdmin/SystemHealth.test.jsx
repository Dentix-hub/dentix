import { render, screen } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import SystemHealth from './SystemHealth';

const apiMocks = vi.hoisted(() => ({
    apiGet: vi.fn(),
    apiPost: vi.fn(),
}));

vi.mock('@/api', () => ({
    api: {
        get: apiMocks.apiGet,
        post: apiMocks.apiPost,
    },
}));

vi.mock('@/utils/logger', () => ({ default: { error: vi.fn() } }));
vi.mock('@/shared/ui', () => ({ toast: { success: vi.fn(), error: vi.fn() } }));
vi.mock('react-i18next', () => ({
    useTranslation: () => ({
        t: (key, fallback) => fallback || key,
        i18n: { language: 'ar' },
    }),
}));

describe('SystemHealth truth-state tests', () => {
    beforeEach(() => {
        vi.clearAllMocks();
    });

    it('renders success health score accurately when data is healthy', async () => {
        apiMocks.apiGet.mockImplementation((url) => {
            if (url === '/api/v1/admin/health/alerts') {
                return Promise.resolve({ data: { score: 95, alerts: [] } });
            }
            if (url === '/api/v1/admin/security/jobs') {
                return Promise.resolve({
                    data: [
                        { id: 1, job_name: 'Backup Job', status: 'success', duration_seconds: 1.2, started_at: '2026-08-26T00:00:00Z', triggered_by: 'system' }
                    ]
                });
            }
            return Promise.resolve({ data: {} });
        });

        render(<SystemHealth />);

        expect(await screen.findByText('95%')).toBeInTheDocument();
        expect(screen.getByText('super_admin.health.all_good')).toBeInTheDocument();
        expect(screen.getByText('100.0%')).toBeInTheDocument(); // 1 job, 1 success
    });

    it('renders warning and critical alerts accurately without defaulting to 100%', async () => {
        apiMocks.apiGet.mockImplementation((url) => {
            if (url === '/api/v1/admin/health/alerts') {
                return Promise.resolve({
                    data: {
                        score: 45,
                        alerts: [{ severity: 'critical', message: 'High CPU usage' }]
                    }
                });
            }
            if (url === '/api/v1/admin/security/jobs') {
                return Promise.resolve({
                    data: [
                        { id: 1, job_name: 'Job 1', status: 'failed', duration_seconds: 2.5, started_at: '2026-08-26T00:00:00Z', triggered_by: 'system' }
                    ]
                });
            }
            return Promise.resolve({ data: {} });
        });

        render(<SystemHealth />);

        expect(await screen.findByText('45%')).toBeInTheDocument();
        expect(screen.getByText('High CPU usage')).toBeInTheDocument();
        expect(screen.queryByText('100%')).not.toBeInTheDocument();
        expect(screen.getByText('0.0%')).toBeInTheDocument(); // 0 success
    });

    it('displays error state and does not claim healthy 100% when health API fails', async () => {
        apiMocks.apiGet.mockImplementation((url) => {
            if (url === '/api/v1/admin/health/alerts') {
                return Promise.reject(new Error('Network error'));
            }
            if (url === '/api/v1/admin/security/jobs') {
                return Promise.reject(new Error('Jobs unavailable'));
            }
            return Promise.reject(new Error('error'));
        });

        render(<SystemHealth />);

        const dashes = await screen.findAllByText('—');
        expect(dashes.length).toBeGreaterThanOrEqual(1);
        expect(screen.queryByText('100%')).not.toBeInTheDocument();
        expect(screen.queryByText('super_admin.health.all_good')).not.toBeInTheDocument();
        expect(screen.getByText('تعذر تحميل بيانات فحص النظام')).toBeInTheDocument();
        expect(screen.getByText('تعذر تحميل سجل المهام')).toBeInTheDocument();
    });
});
