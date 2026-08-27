import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import SettingsManager from './SettingsManager';
import GlobalBanner from '@/shared/ui/GlobalBanner';
import Support from '@/pages/Support';
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
        put: vi.fn(),
    },
    submitFeedback: vi.fn(),
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

describe('Settings and Global Announcement MS-17', () => {
    const mockSettings = [
        { key: 'maintenance_mode', value: 'false' },
        { key: 'global_announcement', value: 'Important server maintenance tonight' },
        { key: 'support_email', value: 'support@dentix.com' },
        { key: 'support_phone', value: '+20 120 130 1415' },
    ];

    beforeEach(() => {
        vi.clearAllMocks();
    });

    it('renders SettingsManager with initial settings values and without stale coming-soon text', () => {
        render(
            <SettingsManager
                settings={mockSettings}
                fetchData={vi.fn()}
            />
        );

        expect(screen.getByText('super_admin.settings.maintenance_title')).toBeInTheDocument();
        expect(screen.getByText('super_admin.settings.announcement_title')).toBeInTheDocument();
        expect(screen.queryByText(/قريباً/)).not.toBeInTheDocument();
        expect(screen.getByDisplayValue('Important server maintenance tonight')).toBeInTheDocument();
        expect(screen.getByDisplayValue('support@dentix.com')).toBeInTheDocument();
    });

    it('toggles maintenance mode via ConfirmDialog and sends api.put', async () => {
        api.put.mockResolvedValueOnce({ data: { success: true } });
        const fetchData = vi.fn();

        render(
            <SettingsManager
                settings={mockSettings}
                fetchData={fetchData}
            />
        );

        const toggleBtn = screen.getByLabelText('super_admin.settings.maintenance_toggle');
        fireEvent.click(toggleBtn);

        // Confirm dialog opens
        expect(screen.getByText('super_admin.settings.maintenance_confirm_title')).toBeInTheDocument();

        // Confirm
        const confirmBtn = screen.getByRole('button', { name: 'common.confirm' });
        fireEvent.click(confirmBtn);

        await waitFor(() => {
            expect(api.put).toHaveBeenCalledWith(
                '/api/v1/admin/settings/maintenance_mode',
                expect.objectContaining({ key: 'maintenance_mode', value: 'true' })
            );
            expect(toast.success).toHaveBeenCalledWith('super_admin.settings.save_success');
            expect(fetchData).toHaveBeenCalled();
        });
    });

    it('rolls back local state on updateSetting error', async () => {
        api.put.mockRejectedValueOnce(new Error('Update failed'));

        render(
            <SettingsManager
                settings={mockSettings}
                fetchData={vi.fn()}
            />
        );

        const textarea = screen.getByDisplayValue('Important server maintenance tonight');
        fireEvent.change(textarea, { target: { value: 'New text that fails' } });

        const saveBtn = screen.getByRole('button', { name: /super_admin.settings.save_changes/ });
        fireEvent.click(saveBtn);

        await waitFor(() => {
            expect(toast.error).toHaveBeenCalledWith('Update failed');
            // Reverts to original value
            expect(screen.getByDisplayValue('Important server maintenance tonight')).toBeInTheDocument();
        });
    });

    it('renders GlobalBanner from api response and dismisses on close button click', async () => {
        api.get.mockResolvedValueOnce({
            data: {
                success: true,
                data: { banner: 'Global announcement text active' },
            },
        });

        render(<GlobalBanner />);

        expect(await screen.findByText('Global announcement text active')).toBeInTheDocument();

        const closeBtn = screen.getByLabelText('Close announcement');
        fireEvent.click(closeBtn);

        expect(screen.queryByText('Global announcement text active')).not.toBeInTheDocument();
    });

    it('renders Support page with neutral Dentix support email and no static Available now claim', async () => {
        api.get.mockResolvedValueOnce({
            data: {
                data: {
                    support_email: 'support@dentix.com',
                    support_phone: '+20 120 130 1415',
                },
            },
        });

        render(<Support />);

        expect(await screen.findByTitle('support@dentix.com')).toBeInTheDocument();
        expect(screen.queryByText('static.support.available_now')).not.toBeInTheDocument();
    });
});
