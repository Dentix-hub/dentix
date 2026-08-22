import { render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import CommunicationsPage from './CommunicationsPage';


const apiMocks = vi.hoisted(() => ({
    apiGet: vi.fn(),
    getSupportMessages: vi.fn(),
    getNotifications: vi.fn(),
}));

vi.mock('@/api', () => ({
    api: { get: apiMocks.apiGet },
    getSupportMessages: apiMocks.getSupportMessages,
    getNotifications: apiMocks.getNotifications,
    broadcastNotification: vi.fn(),
    deleteNotification: vi.fn(),
    deleteSupportMessage: vi.fn(),
}));

vi.mock('@/utils/logger', () => ({ default: { error: vi.fn() } }));
vi.mock('@/shared/ui', () => ({ toast: { success: vi.fn(), error: vi.fn() } }));
vi.mock('@/features/admin/SuperAdmin/SupportInbox', () => ({
    default: ({ messages }) => <div data-testid="messages-count">{messages.length}</div>,
}));
vi.mock('@/features/admin/SuperAdmin/NotificationsManager', () => ({
    default: ({ notifications, tenants }) => (
        <div>{`notifications:${notifications.length};tenants:${tenants.length}`}</div>
    ),
}));

describe('CommunicationsPage API loading', () => {
    beforeEach(() => {
        vi.clearAllMocks();
        apiMocks.apiGet.mockResolvedValue({ data: [{ id: 3 }] });
        apiMocks.getNotifications.mockResolvedValue({ data: [] });
    });

    it('loads support messages through the canonical versioned API helper', async () => {
        apiMocks.getSupportMessages.mockResolvedValue({ data: [{ id: 1 }, { id: 2 }] });

        render(<CommunicationsPage />);

        expect(await screen.findByTestId('messages-count')).toHaveTextContent('2');
        expect(apiMocks.getSupportMessages).toHaveBeenCalledOnce();
        expect(apiMocks.apiGet).toHaveBeenCalledWith('/api/v1/admin/tenants');
        expect(apiMocks.apiGet).not.toHaveBeenCalledWith('/support/messages');
    });

    it('finishes loading when one independent endpoint fails', async () => {
        apiMocks.getSupportMessages.mockRejectedValue(new Error('support unavailable'));

        render(<CommunicationsPage />);

        await waitFor(() => expect(screen.getByTestId('messages-count')).toHaveTextContent('0'));
        expect(screen.queryByText('جاري تحميل الرسائل...')).not.toBeInTheDocument();
    });
});
