import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import SuperAdminCommandPalette from './SuperAdminCommandPalette';
import { api } from '@/api';

const mockNavigate = vi.fn();
vi.mock('react-router-dom', async () => {
    const actual = await vi.importActual('react-router-dom');
    return {
        ...actual,
        useNavigate: () => mockNavigate,
    };
});

vi.mock('react-i18next', () => ({
    useTranslation: () => ({
        t: (key, fallback) => fallback || key,
        i18n: { language: 'ar' },
    }),
}));

vi.mock('@/api', () => ({
    api: {
        get: vi.fn(),
    },
}));

describe('SuperAdminCommandPalette MS-28', () => {
    beforeEach(() => {
        vi.clearAllMocks();
    });

    it('renders quick suggestions when query is empty and navigates on click', () => {
        const handleClose = vi.fn();
        render(
            <MemoryRouter>
                <SuperAdminCommandPalette isOpen={true} onClose={handleClose} />
            </MemoryRouter>
        );

        expect(screen.getByPlaceholderText('ابحث عن عيادة، مستخدم، أو صفحة إدارية...')).toBeInTheDocument();
        expect(screen.getByText('اقتراحات سريعة')).toBeInTheDocument();

        const clinicsBtn = screen.getByRole('button', { name: 'إدارة العيادات' });
        fireEvent.click(clinicsBtn);

        expect(mockNavigate).toHaveBeenCalledWith('/admin/tenants');
        expect(handleClose).toHaveBeenCalled();
    });

    it('searches static actions and API tenants on query input', async () => {
        api.get.mockResolvedValue({
            data: [
                { id: 101, name: 'عيادة النور', domain: 'alnoor', plan: 'enterprise' },
            ],
        });

        const handleClose = vi.fn();
        render(
            <MemoryRouter>
                <SuperAdminCommandPalette isOpen={true} onClose={handleClose} />
            </MemoryRouter>
        );

        const input = screen.getByPlaceholderText('ابحث عن عيادة، مستخدم، أو صفحة إدارية...');
        fireEvent.change(input, { target: { value: 'النور' } });

        await waitFor(() => {
            expect(api.get).toHaveBeenCalledWith('/api/v1/admin/tenants');
            expect(screen.getByText('عيادة النور')).toBeInTheDocument();
        });

        fireEvent.click(screen.getByText('عيادة النور'));
        expect(mockNavigate).toHaveBeenCalledWith('/admin/tenants?id=101');
    });

    it('closes on escape key press', () => {
        const handleClose = vi.fn();
        render(
            <MemoryRouter>
                <SuperAdminCommandPalette isOpen={true} onClose={handleClose} />
            </MemoryRouter>
        );

        fireEvent.keyDown(window, { key: 'Escape' });
        expect(handleClose).toHaveBeenCalled();
    });
});
