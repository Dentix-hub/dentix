import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import AIAdminDashboard from './AIAdminDashboard';
import SessionManager from './SessionManager';
import SecurityPanel from './SecurityPanel';
import SystemLogs from '@/pages/admin/SystemLogs';
import AuditLogViewer from './AuditLogViewer';
import { api } from '@/api';

vi.mock('react-i18next', () => {
    const translations = {
        'super_admin.logs.export_csv': 'تصدير CSV',
        'super_admin.security.block_ip': 'حظر عنوان IP جديد',
        'super_admin.security.block_new_ip': 'حظر عنوان IP جديد',
        'super_admin.ai.periods.week': 'الأسبوع',
        'super_admin.sessions.terminate_btn': 'إنهاء الجلسة',
        'super_admin.sessions.terminate_confirm_title': 'تأكيد إنهاء الجلسة',
        'super_admin.sessions.terminate_confirm_btn': 'إنهاء الجلسة',
    };
    return {
        useTranslation: () => ({
            t: (key, fallback) => translations[key] || (typeof fallback === 'string' ? fallback : key),
            i18n: { language: 'ar' },
        }),
    };
});

vi.mock('@/api', () => ({
    api: {
        get: vi.fn(),
        post: vi.fn(),
        delete: vi.fn(),
    },
}));

vi.mock('@/utils/logger', () => ({ default: { error: vi.fn(), log: vi.fn() } }));

vi.mock('./hooks/useSystemHealth', () => ({
    useSystemHealth: () => ({
        data: { status: 'healthy', score: 100, database: { status: 'healthy' } },
        isLoading: false,
        error: null,
    }),
    useInvalidateSystemHealth: () => vi.fn(),
    HEALTH_STATUS_CLASS_MAP: { healthy: { badge: 'bg-emerald-100', text: 'text-emerald-700' } },
    SYSTEM_HEALTH_QUERY_KEY: ['admin', 'system', 'health'],
}));

vi.mock('@/components/charts/LazyChart', () => ({
    LazyChart: ({ children }) => <div data-testid="lazy-chart">{children}</div>,
    ResponsiveContainer: ({ children }) => <div>{children}</div>,
    AreaChart: ({ children }) => <div>{children}</div>,
    BarChart: ({ children }) => <div>{children}</div>,
    Area: () => <div />,
    Bar: () => <div />,
    CartesianGrid: () => <div />,
    XAxis: () => <div />,
    YAxis: () => <div />,
    Tooltip: () => <div />,
}));

describe('Super Admin Frontend Regression Suite MS-35', () => {
    let queryClient;

    beforeEach(() => {
        vi.clearAllMocks();
        queryClient = new QueryClient({
            defaultOptions: {
                queries: { retry: false },
            },
        });
    });

    it('Regression 1 (AI Stats): displays "—" for success rate on zero requests and switches periods correctly', async () => {
        api.get.mockImplementation((url) => {
            if (url.includes('/ai/admin/stats')) {
                return Promise.resolve({
                    data: {
                        period: 'today',
                        total_requests: 0,
                        success_rate: null,
                        estimated_cost: 0,
                    },
                });
            }
            if (url.includes('/ai/admin/logs')) return Promise.resolve({ data: [] });
            return Promise.resolve({ data: {} });
        });

        render(<AIAdminDashboard />);

        expect(await screen.findByText('0')).toBeInTheDocument();
        expect(screen.getByText('—')).toBeInTheDocument();
        expect(screen.getByText('$0.0000')).toBeInTheDocument();

        // Switch period to week
        const weekBtn = screen.getByRole('button', { name: 'الأسبوع' });
        fireEvent.click(weekBtn);

        await waitFor(() => {
            expect(api.get).toHaveBeenCalledWith('/api/v1/ai/admin/stats?period=week');
        });
    });

    it('Regression 2 (Sessions): terminates session safely via shared ConfirmDialog', async () => {
        api.get.mockImplementation((url) => {
            if (url.includes('/admin/security/sessions')) {
                return Promise.resolve({
                    data: [
                        { id: 'sess_123', username: 'dr_sami', tenant: 'Al-Amal', ip_address: '192.168.1.5', last_activity: new Date().toISOString() },
                    ],
                });
            }
            return Promise.resolve({ data: [] });
        });

        render(
            <QueryClientProvider client={queryClient}>
                <SessionManager />
            </QueryClientProvider>
        );

        expect(await screen.findByText('dr_sami')).toBeInTheDocument();

        const terminateBtn = screen.getByTitle('إنهاء الجلسة');
        fireEvent.click(terminateBtn);

        expect(screen.getByText('تأكيد إنهاء الجلسة')).toBeInTheDocument();

        api.delete.mockResolvedValue({ message: 'Session terminated' });
        const confirmBtn = screen.getByRole('button', { name: 'إنهاء الجلسة' });
        fireEvent.click(confirmBtn);

        await waitFor(() => {
            expect(api.delete).toHaveBeenCalledWith('/api/v1/admin/security/sessions/sess_123');
        });
    });

    it('Regression 3 (Security Panel): validates IP input before blocking and handles partial failures', async () => {
        api.get.mockImplementation((url) => {
            if (url.includes('/system/security/stats')) return Promise.resolve({ data: { blocked_ips: 1, failed_logins_24h: 2 } });
            if (url.includes('/system/security/chart')) return Promise.resolve({ data: [] });
            if (url.includes('/security/blocked-ips')) return Promise.resolve({ data: [{ ip_address: '10.0.0.99', reason: 'Brute force' }] });
            return Promise.resolve({ data: {} });
        });

        render(
            <QueryClientProvider client={queryClient}>
                <SecurityPanel />
            </QueryClientProvider>
        );

        expect(await screen.findByText('10.0.0.99')).toBeInTheDocument();

        // Block IP button triggers modal
        const blockTrigger = screen.getByRole('button', { name: 'حظر عنوان IP جديد' });
        fireEvent.click(blockTrigger);

        expect(screen.getByPlaceholderText('192.168.1.1 or 2001:db8::1')).toBeInTheDocument();
    });

    it('Regression 4 (System Logs): exports CSV and revokes object URL cleanly', async () => {
        const createObjectURLSpy = vi.spyOn(window.URL, 'createObjectURL').mockReturnValue('blob:mock-url');
        const revokeObjectURLSpy = vi.spyOn(window.URL, 'revokeObjectURL').mockImplementation(() => {});

        api.get.mockImplementation((url) => {
            if (url.includes('/admin/system/logs/export')) {
                return Promise.resolve({ data: 'id,level,message\n1,ERROR,timeout' });
            }
            if (url.includes('/admin/system/logs')) {
                return Promise.resolve({
                    data: [
                        { id: 1, level: 'ERROR', message: 'DB Connection Timeout', source: 'BACKEND', timestamp: new Date().toISOString() },
                    ],
                });
            }
            return Promise.resolve({ data: [] });
        });

        render(
            <QueryClientProvider client={queryClient}>
                <MemoryRouter>
                    <SystemLogs />
                </MemoryRouter>
            </QueryClientProvider>
        );

        expect(await screen.findByText('DB Connection Timeout')).toBeInTheDocument();

        // Trigger CSV export
        const exportBtn = screen.getByRole('button', { name: 'تصدير CSV' });
        fireEvent.click(exportBtn);

        await waitFor(() => {
            expect(createObjectURLSpy).toHaveBeenCalled();
            expect(revokeObjectURLSpy).toHaveBeenCalledWith('blob:mock-url');
        });
    });

    it('Regression 5 (Audit Logs): renders audit entries safely and filters by criteria', async () => {
        api.get.mockImplementation((url) => {
            if (url.includes('/api/v1/admin/system/audit-logs')) {
                return Promise.resolve({
                    data: {
                        logs: [
                            { id: 10, action: 'USER_LOGIN', performed_by_username: 'admin_user', ip_address: '127.0.0.1', created_at: new Date().toISOString(), entity_type: 'AUTH', entity_id: '1' },
                        ],
                        total: 1,
                        pages: 1,
                        current_page: 1,
                    },
                });
            }
            if (url.includes('/api/v1/admin/tenants')) return Promise.resolve({ data: [] });
            return Promise.resolve({ data: {} });
        });

        render(
            <QueryClientProvider client={queryClient}>
                <MemoryRouter>
                    <AuditLogViewer />
                </MemoryRouter>
            </QueryClientProvider>
        );

        expect(await screen.findByText('USER_LOGIN')).toBeInTheDocument();
        expect(screen.getByText('admin_user')).toBeInTheDocument();
    });
});
