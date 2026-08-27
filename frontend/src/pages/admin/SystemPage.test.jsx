import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import SystemPage from './SystemPage';
import { api } from '@/api';
import { toast } from '@/shared/ui';
import { useAuthStore } from '@/store/auth.store';

vi.mock('react-i18next', () => ({
    useTranslation: () => ({
        t: (key) => key,
        i18n: { language: 'ar' },
    }),
}));

vi.mock('@/api', () => ({
    api: {
        get: vi.fn(),
        put: vi.fn(),
        post: vi.fn(),
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
            info: vi.fn(),
        },
    };
});

describe('SystemPage Profile and Backup Truthfulness (MS-18, MS-20, MS-32)', () => {
    beforeEach(() => {
        vi.clearAllMocks();
        useAuthStore.setState({
            user: { id: 1, username: 'admin', email: 'admin@dentix.com', role: 'super_admin' },
            isAuthenticated: true,
        });

        api.get.mockImplementation((url) => {
            if (url === '/api/v1/admin/settings') return Promise.resolve({ data: [] });
            if (url === '/api/v1/admin/tenants') return Promise.resolve({ data: [] });
            if (url === '/api/v1/admin/system/backup/google-status') {
                return Promise.resolve({
                    data: {
                        connected: true,
                        last_backup: {
                            status: 'success',
                            message: 'Backup completed successfully',
                            date: '2026-08-20T12:00:00Z',
                        },
                    },
                });
            }
            if (url === '/api/v1/users/me') return Promise.resolve({ data: { is_2fa_enabled: false } });
            return Promise.resolve({ data: {} });
        });
    });

    it('renders localized system navigation and handles profile update properly', async () => {
        api.put.mockResolvedValueOnce({
            data: {
                success: true,
                data: { id: 1, username: 'new_super_name', email: 'new_email@dentix.com', role: 'super_admin' },
            },
        });

        render(<SystemPage />);

        expect(await screen.findByText('super_admin.system.title')).toBeInTheDocument();
        expect(api.get).toHaveBeenCalledTimes(4);
        const profileTabBtn = screen.getByRole('button', { name: 'super_admin.system.tabs.profile' });
        fireEvent.click(profileTabBtn);

        const usernameInput = screen.getByLabelText('super_admin.profile.username_label');
        fireEvent.change(usernameInput, { target: { value: 'new_super_name' } });

        fireEvent.click(screen.getByRole('button', { name: 'super_admin.profile.save_changes' }));
        fireEvent.click(screen.getByRole('button', { name: 'common.confirm' }));

        await waitFor(() => {
            expect(api.put).toHaveBeenCalledWith('/api/v1/admin/system/profile', {
                username: 'new_super_name',
            });
            expect(toast.success).toHaveBeenCalledWith('super_admin.profile.update_success');
        });
    });

    it('renders connected backup status and last backup run details', async () => {
        render(<SystemPage />);

        fireEvent.click(await screen.findByRole('button', { name: 'super_admin.system.tabs.backup' }));

        expect(screen.getByText('super_admin.backup.connected')).toBeInTheDocument();
        expect(screen.getByText('super_admin.backup.status_success')).toBeInTheDocument();
        expect(screen.getByText(/Backup completed successfully/)).toBeInTheDocument();
    });

    it('triggers backup and shows started/processing toast instead of immediate completion', async () => {
        api.post.mockResolvedValueOnce({
            data: {
                success: true,
                message: 'Backup started in background.',
                status: 'processing',
            },
        });

        render(<SystemPage />);
        fireEvent.click(await screen.findByRole('button', { name: 'super_admin.system.tabs.backup' }));
        fireEvent.click(screen.getByRole('button', { name: 'super_admin.backup.trigger_cloud_btn' }));

        expect(screen.getByText('super_admin.backup.confirm_upload_title')).toBeInTheDocument();
        fireEvent.click(screen.getByRole('button', { name: 'super_admin.backup.confirm_start_btn' }));

        await waitFor(() => {
            expect(api.post).toHaveBeenCalledWith('/api/v1/admin/system/backup/google-upload');
            expect(toast.info).toHaveBeenCalledWith('Backup started in background.');
        });
    });

    it('disconnects Google Drive via ConfirmDialog', async () => {
        api.delete.mockResolvedValueOnce({
            data: {
                success: true,
                message: 'Google Drive disconnected successfully',
            },
        });

        render(<SystemPage />);
        fireEvent.click(await screen.findByRole('button', { name: 'super_admin.system.tabs.backup' }));
        fireEvent.click(screen.getByRole('button', { name: 'super_admin.backup.disconnect_btn' }));

        expect(screen.getByText('super_admin.backup.disconnect_confirm_title')).toBeInTheDocument();
        fireEvent.click(screen.getByRole('button', { name: 'common.confirm' }));

        await waitFor(() => {
            expect(api.delete).toHaveBeenCalledWith('/api/v1/admin/system/backup/google-auth');
            expect(toast.success).toHaveBeenCalledWith('super_admin.backup.disconnect_success');
            expect(screen.getByText('super_admin.backup.disconnected')).toBeInTheDocument();
        });
    });
});
