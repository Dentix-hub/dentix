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

describe('SystemPage Profile and Backup Truthfulness (MS-18 & MS-20)', () => {
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

    it('renders profile tab and handles profile update properly (MS-18)', async () => {
        api.put.mockResolvedValueOnce({
            data: {
                success: true,
                data: { id: 1, username: 'new_super_name', email: 'new_email@dentix.com', role: 'super_admin' },
            },
        });

        render(<SystemPage />);

        const profileTabBtn = await screen.findByRole('button', { name: /الحساب/ });
        fireEvent.click(profileTabBtn);

        const usernameInput = screen.getByLabelText('اسم المستخدم الجديد');
        fireEvent.change(usernameInput, { target: { value: 'new_super_name' } });

        const submitBtn = screen.getByRole('button', { name: /super_admin.profile.save_changes/ });
        fireEvent.click(submitBtn);

        const confirmBtn = screen.getByRole('button', { name: 'common.confirm' });
        fireEvent.click(confirmBtn);

        await waitFor(() => {
            expect(api.put).toHaveBeenCalledWith('/api/v1/admin/system/profile', {
                username: 'new_super_name',
            });
            expect(toast.success).toHaveBeenCalledWith('super_admin.profile.update_success');
        });
    });

    it('renders connected backup status and last backup run details (MS-20)', async () => {
        render(<SystemPage />);

        const backupTabBtn = await screen.findByRole('button', { name: /النسخ الاحتياطي/ });
        fireEvent.click(backupTabBtn);

        expect(screen.getByText('common.connected')).toBeInTheDocument();
        expect(screen.getByText('common.success')).toBeInTheDocument();
        expect(screen.getByText(/Backup completed successfully/)).toBeInTheDocument();
    });

    it('triggers backup and shows started/processing toast instead of immediate completion (MS-20)', async () => {
        api.post.mockResolvedValueOnce({
            data: {
                success: true,
                message: 'Backup started in background.',
                status: 'processing',
            },
        });

        render(<SystemPage />);

        const backupTabBtn = await screen.findByRole('button', { name: /النسخ الاحتياطي/ });
        fireEvent.click(backupTabBtn);

        const triggerBtn = screen.getByRole('button', { name: /super_admin.backup.trigger_cloud_btn/ });
        fireEvent.click(triggerBtn);

        expect(screen.getByText('super_admin.backup.confirm_upload_title')).toBeInTheDocument();

        const confirmBtn = screen.getByRole('button', { name: 'super_admin.backup.confirm_start_btn' });
        fireEvent.click(confirmBtn);

        await waitFor(() => {
            expect(api.post).toHaveBeenCalledWith('/api/v1/admin/system/backup/google-upload');
            expect(toast.info).toHaveBeenCalledWith('Backup started in background.');
        });
    });

    it('disconnects Google Drive via ConfirmDialog (MS-20)', async () => {
        api.delete.mockResolvedValueOnce({
            data: {
                success: true,
                message: 'Google Drive disconnected successfully',
            },
        });

        render(<SystemPage />);

        const backupTabBtn = await screen.findByRole('button', { name: /النسخ الاحتياطي/ });
        fireEvent.click(backupTabBtn);

        const disconnectBtn = screen.getByRole('button', { name: /super_admin.backup.disconnect_btn/ });
        fireEvent.click(disconnectBtn);

        expect(screen.getByText('super_admin.backup.disconnect_confirm_title')).toBeInTheDocument();

        const confirmBtn = screen.getByRole('button', { name: 'common.confirm' });
        fireEvent.click(confirmBtn);

        await waitFor(() => {
            expect(api.delete).toHaveBeenCalledWith('/api/v1/admin/system/backup/google-auth');
            expect(toast.success).toHaveBeenCalledWith('super_admin.backup.disconnect_success');
            expect(screen.getByText('common.disconnected')).toBeInTheDocument();
        });
    });
});
