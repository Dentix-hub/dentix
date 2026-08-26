import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import SessionManager from './SessionManager';
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

describe('SessionManager MS-24 (null-safe search, terminate confirm, error states)', () => {
    beforeEach(() => {
        vi.clearAllMocks();
    });

    it('handles null and missing fields gracefully without crashing', async () => {
        api.get.mockResolvedValue({
            data: [
                {
                    id: 101,
                    username: null,
                    tenant: null,
                    ip_address: null,
                    location: null,
                    user_agent: null,
                    last_active: null,
                    created_at: null,
                },
                {
                    id: 102,
                    username: 'dr_sami',
                    tenant: 'Al-Amal Clinic',
                    ip_address: '192.168.1.55',
                    location: { city: 'Riyadh', country_code: 'SA' },
                    user_agent: 'Mozilla/5.0 (iPhone)',
                    last_active: '2026-08-20T10:00:00Z',
                    created_at: '2026-08-20T08:00:00Z',
                },
            ],
        });

        render(<SessionManager />);

        expect(await screen.findByText('dr_sami')).toBeInTheDocument();
        expect(screen.getByText('Al-Amal Clinic')).toBeInTheDocument();
        expect(screen.getByText('192.168.1.55')).toBeInTheDocument();
        expect(screen.getByText('super_admin.sessions.anonymous_user')).toBeInTheDocument();
    });

    it('performs search safely across username, tenant, and IP', async () => {
        api.get.mockResolvedValue({
            data: [
                { id: 1, username: 'admin_user', tenant: 'Main Dental', ip_address: '10.0.0.1' },
                { id: 2, username: 'reception_nour', tenant: 'Downtown Clinic', ip_address: '10.0.0.2' },
            ],
        });

        render(<SessionManager />);

        expect(await screen.findByText('admin_user')).toBeInTheDocument();
        expect(screen.getByText('reception_nour')).toBeInTheDocument();

        const searchInput = screen.getByPlaceholderText('super_admin.sessions.search_placeholder');
        fireEvent.change(searchInput, { target: { value: 'downtown' } });

        await waitFor(() => {
            expect(screen.queryByText('admin_user')).not.toBeInTheDocument();
            expect(screen.getByText('reception_nour')).toBeInTheDocument();
        });
    });

    it('terminates a session via ConfirmDialog and updates list', async () => {
        api.get.mockResolvedValue({
            data: [
                { id: 42, username: 'test_terminator', tenant: 'Clinic A', ip_address: '1.2.3.4' },
            ],
        });
        api.delete.mockResolvedValueOnce({ data: { success: true } });

        render(<SessionManager />);

        const terminateBtn = await screen.findByLabelText(/test_terminator/);
        fireEvent.click(terminateBtn);

        expect(screen.getByText('super_admin.sessions.terminate_confirm_title')).toBeInTheDocument();

        const confirmBtn = screen.getByRole('button', { name: 'super_admin.sessions.terminate_confirm_btn' });
        fireEvent.click(confirmBtn);

        await waitFor(() => {
            expect(api.delete).toHaveBeenCalledWith('/api/v1/admin/security/sessions/42');
            expect(toast.success).toHaveBeenCalledWith('super_admin.sessions.terminate_success');
            expect(screen.queryByText('test_terminator')).not.toBeInTheDocument();
        });
    });
});
