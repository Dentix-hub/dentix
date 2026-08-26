import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import SystemLogs from './SystemLogs';
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
        delete: vi.fn(),
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

describe('SystemLogs MS-25 (error states, clipboard safety, export URL revocation, pagination safety)', () => {
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

    it('renders distinct error state when log fetch fails', async () => {
        api.get.mockRejectedValueOnce(new Error('Network error loading logs'));

        render(
            <QueryClientProvider client={queryClient}>
                <SystemLogs />
            </QueryClientProvider>
        );

        expect(await screen.findByText(/Network error loading logs/)).toBeInTheDocument();
        expect(screen.getByRole('button', { name: /common.retry/ })).toBeInTheDocument();
    });

    it('copies log details safely and shows success toast', async () => {
        const writeTextMock = vi.fn().mockResolvedValue(undefined);
        Object.assign(navigator, {
            clipboard: {
                writeText: writeTextMock,
            },
        });

        api.get.mockResolvedValueOnce({
            data: [
                {
                    id: 1,
                    level: 'ERROR',
                    source: 'BACKEND',
                    message: 'Database deadlock detected',
                    path: '/api/v1/billing',
                    stack_trace: 'Traceback...',
                    created_at: '2026-08-20T12:00:00Z',
                },
            ],
        });

        render(
            <QueryClientProvider client={queryClient}>
                <SystemLogs />
            </QueryClientProvider>
        );

        const copyBtn = await screen.findByLabelText(/super_admin.logs.action_copy 1/);
        fireEvent.click(copyBtn);

        await waitFor(() => {
            expect(writeTextMock).toHaveBeenCalled();
            expect(toast.success).toHaveBeenCalledWith('super_admin.logs.copy_success');
        });
    });

    it('exports CSV logs and revokes blob URL', async () => {
        const createObjectURLMock = vi.fn().mockReturnValue('blob:http://localhost/test-uuid');
        const revokeObjectURLMock = vi.fn();
        window.URL.createObjectURL = createObjectURLMock;
        window.URL.revokeObjectURL = revokeObjectURLMock;

        api.get.mockImplementation((url) => {
            if (url.includes('/export')) {
                return Promise.resolve({ data: 'id,level,message\n1,ERROR,Test' });
            }
            return Promise.resolve({ data: [] });
        });

        render(
            <QueryClientProvider client={queryClient}>
                <SystemLogs />
            </QueryClientProvider>
        );

        const exportBtn = await screen.findByRole('button', { name: /super_admin.logs.export_csv/ });
        fireEvent.click(exportBtn);

        await waitFor(() => {
            expect(createObjectURLMock).toHaveBeenCalled();
            expect(revokeObjectURLMock).toHaveBeenCalledWith('blob:http://localhost/test-uuid');
            expect(toast.success).toHaveBeenCalledWith('super_admin.logs.export_success');
        });
    });
});
