import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import SecurityPanel from './SecurityPanel';
import { api } from '@/api';
import { toast } from '@/shared/ui';

vi.mock('react-i18next', () => ({
    useTranslation: () => ({
        t: (key, options) => {
            if (options?.ip) return `Unblock ${options.ip}`;
            return key;
        },
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

vi.mock('./HealthAlerts', () => ({
    default: () => <div data-testid="health-alerts">Health Alerts</div>,
}));

vi.mock('@/components/charts/LazyChart', () => ({
    LazyChart: ({ children }) => <div data-testid="lazy-chart">{children}</div>,
    ResponsiveContainer: ({ children }) => <div>{children}</div>,
    AreaChart: ({ children }) => <div>{children}</div>,
    Area: () => <div />,
    CartesianGrid: () => <div />,
    XAxis: () => <div />,
    YAxis: () => <div />,
    Tooltip: () => <div />,
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

describe('SecurityPanel MS-21 (partial failures, derived assurance, IP blocking & unblocking)', () => {
    beforeEach(() => {
        vi.clearAllMocks();
    });

    it('renders gracefully even when stats API fails (partial failure handling)', async () => {
        api.get.mockImplementation((url) => {
            if (url === '/api/v1/admin/system/security/stats') {
                return Promise.reject(new Error('Stats service offline'));
            }
            if (url === '/api/v1/admin/system/security/chart') {
                return Promise.resolve({
                    data: [{ date: '2026-08-20', success: 10, failed: 2 }],
                });
            }
            if (url === '/api/v1/admin/security/blocked-ips') {
                return Promise.resolve({
                    data: [{ id: 1, ip_address: '192.168.1.50', reason: 'Repeated bad logins' }],
                });
            }
            return Promise.resolve({ data: {} });
        });

        render(<SecurityPanel />);

        // Blocked IPs and chart still render properly despite stats failure
        expect(await screen.findByText('192.168.1.50')).toBeInTheDocument();
        expect(screen.getByText('Repeated bad logins')).toBeInTheDocument();
        expect(screen.getByTestId('lazy-chart')).toBeInTheDocument();
    });

    it('derives critical assurance level when there are many locked users or failures', async () => {
        api.get.mockImplementation((url) => {
            if (url === '/api/v1/admin/system/security/stats') {
                return Promise.resolve({
                    data: {
                        blocked_ips_count: 5,
                        locked_users: [1, 2, 3, 4, 5],
                        recent_failures: Array(20).fill({ id: 1, ip_address: '10.0.0.1' }),
                    },
                });
            }
            if (url === '/api/v1/admin/system/security/chart') return Promise.resolve({ data: [] });
            if (url === '/api/v1/admin/security/blocked-ips') return Promise.resolve({ data: [] });
            return Promise.resolve({ data: {} });
        });

        render(<SecurityPanel />);

        expect(await screen.findByText('super_admin.security.level_critical')).toBeInTheDocument();
    });

    it('blocks new IP via Modal and displays success toast', async () => {
        api.get.mockResolvedValue({ data: [] });
        api.post.mockResolvedValueOnce({ data: { success: true } });

        render(<SecurityPanel />);

        const openModalBtn = await screen.findByRole('button', { name: /super_admin.security.block_new_ip/ });
        fireEvent.click(openModalBtn);

        expect(screen.getByText('super_admin.security.block_modal_title')).toBeInTheDocument();

        const ipInput = screen.getByLabelText('super_admin.security.target_ip');
        const reasonInput = screen.getByLabelText('super_admin.security.block_reason');

        fireEvent.change(ipInput, { target: { value: '198.51.100.22' } });
        fireEvent.change(reasonInput, { target: { value: 'DDoS origin' } });

        const confirmBtn = screen.getByRole('button', { name: /super_admin.security.confirm_block/ });
        fireEvent.click(confirmBtn);

        await waitFor(() => {
            expect(api.post).toHaveBeenCalledWith('/api/v1/admin/security/ip-block', {
                ip_address: '198.51.100.22',
                reason: 'DDoS origin',
            });
            expect(toast.success).toHaveBeenCalledWith('super_admin.security.block_success');
        });
    });

    it('unblocks IP via ConfirmDialog', async () => {
        api.get.mockImplementation((url) => {
            if (url === '/api/v1/admin/security/blocked-ips') {
                return Promise.resolve({
                    data: [{ id: 1, ip_address: '198.51.100.99', reason: 'Blocked for testing' }],
                });
            }
            return Promise.resolve({ data: [] });
        });
        api.delete.mockResolvedValueOnce({ data: { success: true } });

        render(<SecurityPanel />);

        const unblockBtn = await screen.findByLabelText(/198.51.100.99/);
        fireEvent.click(unblockBtn);

        expect(screen.getByText('super_admin.security.unblock_confirm_title')).toBeInTheDocument();

        const confirmBtn = screen.getByRole('button', { name: 'super_admin.security.unblock' });
        fireEvent.click(confirmBtn);

        await waitFor(() => {
            expect(api.delete).toHaveBeenCalledWith('/api/v1/admin/security/ip-block/198.51.100.99');
            expect(toast.success).toHaveBeenCalledWith('super_admin.security.unblock_success');
        });
    });
});
