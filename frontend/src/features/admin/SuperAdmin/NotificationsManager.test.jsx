import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import NotificationsManager from './NotificationsManager';

vi.mock('react-i18next', () => ({
    useTranslation: () => ({
        t: (key) => key,
        i18n: { language: 'ar' },
    }),
}));

describe('NotificationsManager MS-16 (tenant targeting, normalization, double-send protection, deletion)', () => {
    const mockTenants = [
        { id: 10, name: 'Dental Care Clinic' },
        { id: 20, name: 'Apex Clinic' },
    ];

    const mockNotifications = [
        {
            id: 1,
            title: 'System Update',
            content: 'Midnight downtime',
            type: 'info',
            is_global: true,
            tenant_id: null,
            created_at: '2026-08-20T10:00:00Z',
        },
        {
            id: 2,
            title: 'License Expiry',
            content: 'Renew before end of month',
            type: 'warning',
            is_global: false,
            tenant_id: 10,
            created_at: '2026-08-21T10:00:00Z',
        },
    ];

    beforeEach(() => {
        vi.clearAllMocks();
    });

    it('renders notifications list and tenant labels correctly', () => {
        render(
            <NotificationsManager
                notifForm={{ title: '', content: '', type: 'info', is_global: true, tenant_id: null }}
                setNotifForm={vi.fn()}
                handleSendNotification={vi.fn()}
                notifications={mockNotifications}
                handleDeleteNotification={vi.fn()}
                tenants={mockTenants}
                isSending={false}
            />
        );

        expect(screen.getByText('System Update')).toBeInTheDocument();
        expect(screen.getByText('License Expiry')).toBeInTheDocument();
        expect(screen.getByText(/Dental Care Clinic/)).toBeInTheDocument();
    });

    it('normalizes tenant_id to null when switching target to all clinics', () => {
        const setNotifForm = vi.fn();

        render(
            <NotificationsManager
                notifForm={{ title: '', content: '', type: 'info', is_global: false, tenant_id: 10 }}
                setNotifForm={setNotifForm}
                handleSendNotification={vi.fn()}
                notifications={mockNotifications}
                handleDeleteNotification={vi.fn()}
                tenants={mockTenants}
                isSending={false}
            />
        );

        const targetSelect = screen.getByLabelText('super_admin.notifications.target');
        fireEvent.change(targetSelect, { target: { value: 'all' } });

        expect(setNotifForm).toHaveBeenCalled();
        const updater = setNotifForm.mock.calls[0][0];
        const updatedState = updater({ is_global: false, tenant_id: 10 });
        expect(updatedState.is_global).toBe(true);
        expect(updatedState.tenant_id).toBeNull();
    });

    it('selects first tenant by default when switching to specific clinic', () => {
        const setNotifForm = vi.fn();

        render(
            <NotificationsManager
                notifForm={{ title: '', content: '', type: 'info', is_global: true, tenant_id: null }}
                setNotifForm={setNotifForm}
                handleSendNotification={vi.fn()}
                notifications={mockNotifications}
                handleDeleteNotification={vi.fn()}
                tenants={mockTenants}
                isSending={false}
            />
        );

        const targetSelect = screen.getByLabelText('super_admin.notifications.target');
        fireEvent.change(targetSelect, { target: { value: 'specific' } });

        expect(setNotifForm).toHaveBeenCalled();
        const updater = setNotifForm.mock.calls[0][0];
        const updatedState = updater({ is_global: true, tenant_id: null });
        expect(updatedState.is_global).toBe(false);
        expect(updatedState.tenant_id).toBe(10);
    });

    it('disables submit button and shows loading state when isSending is true', () => {
        const handleSendNotification = vi.fn();

        render(
            <NotificationsManager
                notifForm={{ title: 'Notice', content: 'Details', type: 'info', is_global: true, tenant_id: null }}
                setNotifForm={vi.fn()}
                handleSendNotification={handleSendNotification}
                notifications={mockNotifications}
                handleDeleteNotification={vi.fn()}
                tenants={mockTenants}
                isSending={true}
            />
        );

        const submitBtn = screen.getByRole('button', { name: /common.saving/ });
        expect(submitBtn).toBeDisabled();

        fireEvent.click(submitBtn);
        expect(handleSendNotification).not.toHaveBeenCalled();
    });

    it('opens ConfirmDialog on delete notification and triggers handleDeleteNotification', async () => {
        const handleDeleteNotification = vi.fn().mockResolvedValue(true);

        render(
            <NotificationsManager
                notifForm={{ title: '', content: '', type: 'info', is_global: true, tenant_id: null }}
                setNotifForm={vi.fn()}
                handleSendNotification={vi.fn()}
                notifications={mockNotifications}
                handleDeleteNotification={handleDeleteNotification}
                tenants={mockTenants}
                isSending={false}
            />
        );

        const deleteBtns = screen.getAllByLabelText('super_admin.notifications.delete_notif');
        fireEvent.click(deleteBtns[0]);

        // Confirmation dialog appears
        expect(screen.getByText('super_admin.notifications.delete_confirm_msg')).toBeInTheDocument();

        // Confirm delete
        const confirmBtn = screen.getByRole('button', { name: 'common.delete' });
        fireEvent.click(confirmBtn);

        await waitFor(() => {
            expect(handleDeleteNotification).toHaveBeenCalledWith(1);
        });
    });
});
