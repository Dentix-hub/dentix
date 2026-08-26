import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import SupportInbox from './SupportInbox';
import { updateMessageStatus } from '@/api';
import { toast } from '@/shared/ui';

vi.mock('react-i18next', () => ({
    useTranslation: () => ({
        t: (key) => key,
        i18n: { language: 'ar' },
    }),
}));

vi.mock('@/api', () => ({
    updateMessageStatus: vi.fn(),
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

describe('SupportInbox MS-15 (viewing, read status update, deletion, and stats)', () => {
    const mockMessages = [
        {
            id: 1,
            username: 'dr_sara',
            clinic_name: 'Cairo Dental',
            subject: 'Billing Inquiry',
            message: 'Need help with invoice receipt',
            priority: 'high',
            status: 'unread',
            created_at: '2026-08-20T10:00:00Z',
        },
        {
            id: 2,
            username: 'dr_ahmed',
            clinic_name: 'Alex Clinic',
            subject: 'System suggestion',
            message: 'Can we add dark mode report export?',
            priority: 'normal',
            status: 'read',
            created_at: '2026-08-19T12:00:00Z',
        },
    ];

    beforeEach(() => {
        vi.clearAllMocks();
    });

    it('renders message stats correctly', () => {
        render(
            <SupportInbox
                messages={mockMessages}
                setMessages={vi.fn()}
                handleDeleteMessage={vi.fn()}
                fetchData={vi.fn()}
            />
        );

        // Total = 2, unread = 1, high priority = 1
        expect(screen.getByText('2')).toBeInTheDocument();
        const ones = screen.getAllByText('1');
        expect(ones.length).toBeGreaterThanOrEqual(2);
    });

    it('opens modal and updates unread message to read on view', async () => {
        updateMessageStatus.mockResolvedValueOnce({ data: { success: true } });
        const setMessages = vi.fn();

        render(
            <SupportInbox
                messages={mockMessages}
                setMessages={setMessages}
                handleDeleteMessage={vi.fn()}
                fetchData={vi.fn()}
            />
        );

        const viewBtns = screen.getAllByLabelText('super_admin.support.view_details');
        fireEvent.click(viewBtns[0]); // first message is unread

        // Modal should open with message subject and content
        expect(screen.getAllByText('Billing Inquiry').length).toBeGreaterThanOrEqual(1);
        expect(screen.getAllByText('Need help with invoice receipt').length).toBeGreaterThanOrEqual(1);
        expect(screen.getByText('super_admin.support.message_body')).toBeInTheDocument();

        await waitFor(() => {
            expect(updateMessageStatus).toHaveBeenCalledWith(1, 'read');
            expect(setMessages).toHaveBeenCalled();
        });
    });

    it('opens modal without re-calling updateMessageStatus if message is already read', async () => {
        const setMessages = vi.fn();

        render(
            <SupportInbox
                messages={mockMessages}
                setMessages={setMessages}
                handleDeleteMessage={vi.fn()}
                fetchData={vi.fn()}
            />
        );

        const viewBtns = screen.getAllByLabelText('super_admin.support.view_details');
        fireEvent.click(viewBtns[1]); // second message is already read

        expect(screen.getAllByText('System suggestion').length).toBeGreaterThanOrEqual(1);
        expect(screen.getAllByText('Can we add dark mode report export?').length).toBeGreaterThanOrEqual(1);
        expect(updateMessageStatus).not.toHaveBeenCalled();
    });

    it('handles status update error gracefully and calls fetchData', async () => {
        updateMessageStatus.mockRejectedValueOnce(new Error('Network error'));
        const fetchData = vi.fn();

        render(
            <SupportInbox
                messages={mockMessages}
                setMessages={vi.fn()}
                handleDeleteMessage={vi.fn()}
                fetchData={fetchData}
            />
        );

        const viewBtns = screen.getAllByLabelText('super_admin.support.view_details');
        fireEvent.click(viewBtns[0]);

        await waitFor(() => {
            expect(toast.error).toHaveBeenCalledWith('super_admin.support.error_updating_status');
            expect(fetchData).toHaveBeenCalled();
        });
    });

    it('opens ConfirmDialog and deletes message on confirm', async () => {
        const handleDeleteMessage = vi.fn().mockResolvedValue(true);

        render(
            <SupportInbox
                messages={mockMessages}
                setMessages={vi.fn()}
                handleDeleteMessage={handleDeleteMessage}
                fetchData={vi.fn()}
            />
        );

        const deleteBtns = screen.getAllByLabelText('super_admin.support.delete_msg');
        fireEvent.click(deleteBtns[0]);

        // Confirmation dialog appears
        expect(screen.getByText('super_admin.support.delete_confirm_msg')).toBeInTheDocument();

        // Confirm delete
        const confirmBtn = screen.getByRole('button', { name: 'common.delete' });
        fireEvent.click(confirmBtn);

        await waitFor(() => {
            expect(handleDeleteMessage).toHaveBeenCalledWith(1);
        });
    });
});
