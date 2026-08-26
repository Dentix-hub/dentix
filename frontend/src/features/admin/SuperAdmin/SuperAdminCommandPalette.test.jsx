import { render, screen, fireEvent } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import SuperAdminCommandPalette from './SuperAdminCommandPalette';

const mockNavigate = vi.fn();

vi.mock('react-router-dom', () => ({
    useNavigate: () => mockNavigate,
}));

const apiMocks = vi.hoisted(() => ({
    apiGet: vi.fn(),
}));

vi.mock('@/api', () => ({
    api: {
        get: apiMocks.apiGet,
    },
}));

vi.mock('@/utils/logger', () => ({ default: { error: vi.fn() } }));

describe('SuperAdminCommandPalette search and deep linking', () => {
    const mockOnClose = vi.fn();

    beforeEach(() => {
        vi.clearAllMocks();
        apiMocks.apiGet.mockImplementation((url) => {
            if (url === '/api/v1/admin/tenants') {
                return Promise.resolve({
                    data: [
                        { id: 42, name: 'Smile Dental Clinic', domain: 'smiledental', plan: 'pro' },
                        { id: 99, name: 'Pearl Center', domain: 'pearl', plan: 'enterprise' },
                    ],
                });
            }
            return Promise.resolve({ data: [] });
        });
    });

    it('returns null when isOpen is false', () => {
        const { container } = render(<SuperAdminCommandPalette isOpen={false} onClose={mockOnClose} />);
        expect(container.firstChild).toBeNull();
    });

    it('renders quick suggestions when opened with empty query', () => {
        render(<SuperAdminCommandPalette isOpen={true} onClose={mockOnClose} />);

        expect(screen.getByText('اقتراحات سريعة')).toBeInTheDocument();
        expect(screen.getByText('إدارة العيادات')).toBeInTheDocument();
        expect(screen.getByText('سجل الأخطاء')).toBeInTheDocument();
    });

    it('searches static admin actions and deep links when selected', async () => {
        render(<SuperAdminCommandPalette isOpen={true} onClose={mockOnClose} />);

        const input = screen.getByPlaceholderText(/ابحث عن عيادة/);
        fireEvent.change(input, { target: { value: 'المالية' } });

        expect(await screen.findByText('التقارير المالية والفوترة')).toBeInTheDocument();

        fireEvent.click(screen.getByText('التقارير المالية والفوترة'));

        expect(mockNavigate).toHaveBeenCalledWith('/admin/finance');
        expect(mockOnClose).toHaveBeenCalled();
    });

    it('searches backend tenants and generates deep link to /admin/tenants?id=:id', async () => {
        render(<SuperAdminCommandPalette isOpen={true} onClose={mockOnClose} />);

        const input = screen.getByPlaceholderText(/ابحث عن عيادة/);
        fireEvent.change(input, { target: { value: 'Smile' } });

        expect(await screen.findByText('Smile Dental Clinic')).toBeInTheDocument();
        expect(screen.getByText(/smiledental\.dentix\.com/)).toBeInTheDocument();

        fireEvent.click(screen.getByText('Smile Dental Clinic'));

        expect(mockNavigate).toHaveBeenCalledWith('/admin/tenants?id=42');
        expect(mockOnClose).toHaveBeenCalled();
    });
});
