import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import TwoFactorSetup from './TwoFactorSetup';
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
        },
    };
});

describe('TwoFactorSetup MS-19', () => {
    beforeEach(() => {
        vi.clearAllMocks();
    });

    it('renders disabled state and starts setup when button is clicked', async () => {
        api.post.mockResolvedValueOnce({
            data: {
                data: {
                    secret: 'JBSWY3DPEHPK3PXP',
                    qr_code: 'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==',
                },
            },
        });

        render(<TwoFactorSetup isEnabled={false} onToggle={vi.fn()} />);

        const startBtn = screen.getByRole('button', { name: /super_admin.two_factor.start_setup/ });
        fireEvent.click(startBtn);

        await waitFor(() => {
            expect(api.post).toHaveBeenCalledWith('/api/v1/auth/2fa/setup');
            expect(screen.getByText('JBSWY3DPEHPK3PXP')).toBeInTheDocument();
            expect(screen.getByAltText('2FA QR Code')).toBeInTheDocument();
        });
    });

    it('cancels setup and clears secret and verification code', async () => {
        api.post.mockResolvedValueOnce({
            data: {
                data: {
                    secret: 'JBSWY3DPEHPK3PXP',
                    qr_code: 'base64qr',
                },
            },
        });

        render(<TwoFactorSetup isEnabled={false} onToggle={vi.fn()} />);

        fireEvent.click(screen.getByRole('button', { name: /super_admin.two_factor.start_setup/ }));

        await waitFor(() => {
            expect(screen.getByText('JBSWY3DPEHPK3PXP')).toBeInTheDocument();
        });

        const codeInput = screen.getByPlaceholderText('000000');
        fireEvent.change(codeInput, { target: { value: '123' } });

        const cancelBtn = screen.getByRole('button', { name: 'common.cancel' });
        fireEvent.click(cancelBtn);

        expect(screen.queryByText('JBSWY3DPEHPK3PXP')).not.toBeInTheDocument();
        expect(screen.getByRole('button', { name: /super_admin.two_factor.start_setup/ })).toBeInTheDocument();
    });

    it('verifies code and activates 2FA', async () => {
        const onToggle = vi.fn();
        api.post.mockResolvedValueOnce({
            data: {
                data: {
                    secret: 'JBSWY3DPEHPK3PXP',
                    qr_code: 'base64qr',
                },
            },
        });
        api.post.mockResolvedValueOnce({ data: { success: true } });

        render(<TwoFactorSetup isEnabled={false} onToggle={onToggle} />);

        fireEvent.click(screen.getByRole('button', { name: /super_admin.two_factor.start_setup/ }));

        await waitFor(() => {
            expect(screen.getByText('JBSWY3DPEHPK3PXP')).toBeInTheDocument();
        });

        const codeInput = screen.getByPlaceholderText('000000');
        fireEvent.change(codeInput, { target: { value: '123456' } });

        const activateBtn = screen.getByRole('button', { name: /super_admin.two_factor.activate_now/ });
        fireEvent.click(activateBtn);

        await waitFor(() => {
            expect(api.post).toHaveBeenCalledWith('/api/v1/auth/2fa/verify', {
                code: '123456',
                secret: 'JBSWY3DPEHPK3PXP',
            });
            expect(toast.success).toHaveBeenCalledWith('super_admin.two_factor.enable_success');
            expect(onToggle).toHaveBeenCalledWith(true);
        });
    });

    it('disables 2FA via ConfirmDialog', async () => {
        const onToggle = vi.fn();
        api.delete.mockResolvedValueOnce({ data: { success: true } });

        render(<TwoFactorSetup isEnabled={true} onToggle={onToggle} />);

        const disableBtn = screen.getByRole('button', { name: /super_admin.two_factor.disable_btn/ });
        fireEvent.click(disableBtn);

        // Confirmation modal appears
        expect(screen.getByText('super_admin.two_factor.disable_confirm_title')).toBeInTheDocument();

        const confirmBtn = screen.getByRole('button', { name: 'common.confirm' });
        fireEvent.click(confirmBtn);

        await waitFor(() => {
            expect(api.delete).toHaveBeenCalledWith('/api/v1/auth/2fa/disable');
            expect(toast.success).toHaveBeenCalledWith('super_admin.two_factor.disable_success');
            expect(onToggle).toHaveBeenCalledWith(false);
        });
    });

    it('handles clipboard copy correctly', async () => {
        Object.assign(navigator, {
            clipboard: {
                writeText: vi.fn().mockResolvedValueOnce(),
            },
        });

        api.post.mockResolvedValueOnce({
            data: {
                data: {
                    secret: 'JBSWY3DPEHPK3PXP',
                    qr_code: 'base64qr',
                },
            },
        });

        render(<TwoFactorSetup isEnabled={false} onToggle={vi.fn()} />);

        fireEvent.click(screen.getByRole('button', { name: /super_admin.two_factor.start_setup/ }));

        await waitFor(() => {
            expect(screen.getByText('JBSWY3DPEHPK3PXP')).toBeInTheDocument();
        });

        const copyBtn = screen.getByLabelText('common.copy');
        fireEvent.click(copyBtn);

        await waitFor(() => {
            expect(navigator.clipboard.writeText).toHaveBeenCalledWith('JBSWY3DPEHPK3PXP');
            expect(toast.success).toHaveBeenCalledWith('super_admin.two_factor.secret_copied');
        });
    });
});
