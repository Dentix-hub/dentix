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

describe('SystemPage Profile Update MS-18', () => {
    beforeEach(() => {
        vi.clearAllMocks();
        useAuthStore.setState({
            user: { id: 1, username: 'admin', email: 'admin@dentix.com', role: 'super_admin' },
            isAuthenticated: true,
        });

        api.get.mockImplementation((url) => {
            if (url === '/api/v1/admin/settings') return Promise.resolve({ data: [] });
            if (url === '/api/v1/admin/tenants') return Promise.resolve({ data: [] });
            if (url === '/api/v1/admin/system/backup/google-status') return Promise.resolve({ data: { connected: false } });
            if (url === '/api/v1/users/me') return Promise.resolve({ data: { is_2fa_enabled: false } });
            return Promise.resolve({ data: {} });
        });
    });

    it('renders profile tab and disables submit button when all fields are empty', async () => {
        render(<SystemPage />);

        // Switch to Profile Tab
        const profileTabBtn = await screen.findByRole('button', { name: /الحساب/ });
        fireEvent.click(profileTabBtn);

        expect(screen.getByText('تحديث بيانات المدير')).toBeInTheDocument();
        const submitBtn = screen.getByRole('button', { name: /super_admin.profile.save_changes/ });
        expect(submitBtn).toBeDisabled();
    });

    it('shows ConfirmDialog when form is submitted with non-empty fields', async () => {
        render(<SystemPage />);

        const profileTabBtn = await screen.findByRole('button', { name: /الحساب/ });
        fireEvent.click(profileTabBtn);

        const usernameInput = screen.getByLabelText('اسم المستخدم الجديد');
        fireEvent.change(usernameInput, { target: { value: 'new_super_name' } });

        const submitBtn = screen.getByRole('button', { name: /super_admin.profile.save_changes/ });
        expect(submitBtn).not.toBeDisabled();

        fireEvent.click(submitBtn);

        expect(screen.getByText('super_admin.profile.confirm_title')).toBeInTheDocument();
    });

    it('sends clean payload, updates auth store, and clears password on successful update', async () => {
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
        const passwordInput = screen.getByLabelText('كلمة المرور الجديدة');

        fireEvent.change(usernameInput, { target: { value: 'new_super_name' } });
        fireEvent.change(passwordInput, { target: { value: 'SecurePass9988!@#' } });

        const submitBtn = screen.getByRole('button', { name: /super_admin.profile.save_changes/ });
        fireEvent.click(submitBtn);

        // Confirm
        const confirmBtn = screen.getByRole('button', { name: 'common.confirm' });
        fireEvent.click(confirmBtn);

        await waitFor(() => {
            expect(api.put).toHaveBeenCalledWith('/api/v1/admin/system/profile', {
                username: 'new_super_name',
                password: 'SecurePass9988!@#',
            });
            expect(toast.success).toHaveBeenCalledWith('super_admin.profile.update_success');
            expect(useAuthStore.getState().user.username).toBe('new_super_name');
            expect(passwordInput.value).toBe('');
        });
    });

    it('displays detailed backend password validation error when update fails', async () => {
        api.put.mockRejectedValueOnce({
            response: {
                data: {
                    detail: 'كلمة المرور يجب أن تتكون من 8 أحرف على الأقل',
                },
            },
        });

        render(<SystemPage />);

        const profileTabBtn = await screen.findByRole('button', { name: /الحساب/ });
        fireEvent.click(profileTabBtn);

        const passwordInput = screen.getByLabelText('كلمة المرور الجديدة');
        fireEvent.change(passwordInput, { target: { value: 'short' } });

        const submitBtn = screen.getByRole('button', { name: /super_admin.profile.save_changes/ });
        fireEvent.click(submitBtn);

        const confirmBtn = screen.getByRole('button', { name: 'common.confirm' });
        fireEvent.click(confirmBtn);

        await waitFor(() => {
            expect(toast.error).toHaveBeenCalledWith('كلمة المرور يجب أن تتكون من 8 أحرف على الأقل');
        });
    });
});
