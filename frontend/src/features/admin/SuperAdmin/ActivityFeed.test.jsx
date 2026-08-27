import { render, screen, fireEvent } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import ActivityFeed from './ActivityFeed';

const mockNavigate = vi.fn();
vi.mock('react-router-dom', () => ({
    useNavigate: () => mockNavigate,
}));

vi.mock('react-i18next', () => ({
    useTranslation: () => ({
        t: (key, fallback) => fallback || key,
        i18n: { language: 'ar' },
    }),
}));

describe('ActivityFeed component routing and affordances', () => {
    beforeEach(() => {
        vi.clearAllMocks();
    });

    it('navigates to tenant deep link when tenant activity is clicked', () => {
        const activities = [
            {
                id: 42,
                type: 'tenant',
                title: 'عيادة النور',
                description: 'تم تسجيل عيادة جديدة',
                timestamp: '2026-08-26T00:00:00Z',
                link: '/admin/tenants?id=42',
            },
        ];

        render(<ActivityFeed activities={activities} />);

        const item = screen.getByText('عيادة النور').closest('[role="button"]');
        expect(item).toBeInTheDocument();
        fireEvent.click(item);

        expect(mockNavigate).toHaveBeenCalledWith('/admin/tenants?id=42');
    });

    it('navigates to system logs when error activity is clicked', () => {
        const activities = [
            {
                id: 101,
                type: 'error',
                title: 'خطأ في الخادم',
                description: 'Database timeout',
                timestamp: '2026-08-26T00:00:00Z',
                link: '/admin/system/logs',
            },
        ];

        render(<ActivityFeed activities={activities} />);

        const item = screen.getByText('خطأ في الخادم').closest('[role="button"]');
        fireEvent.click(item);

        expect(mockNavigate).toHaveBeenCalledWith('/admin/system/logs');
    });

    it('renders noninteractive layout without role="button" when activity has no link', () => {
        const activities = [
            {
                id: 202,
                type: 'audit',
                title: 'سجل تدقيق داخلي',
                description: 'Non-clickable log',
                timestamp: '2026-08-26T00:00:00Z',
                link: null,
            },
        ];

        render(<ActivityFeed activities={activities} />);

        expect(screen.getByText('سجل تدقيق داخلي')).toBeInTheDocument();
        expect(screen.queryByRole('button')).not.toBeInTheDocument();
    });
});
