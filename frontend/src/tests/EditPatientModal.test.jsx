import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import EditPatientModal from '@/features/patients/modals/EditPatientModal';

vi.mock('react-i18next', () => ({
    useTranslation: () => ({
        t: (key, fallback) => (typeof fallback === 'string' ? fallback : key),
    }),
}));

vi.mock('@/api', () => ({
    getDoctors: vi.fn().mockResolvedValue({ data: [] }),
    getPriceLists: vi.fn().mockResolvedValue({ data: [] }),
}));

vi.mock('@/shared/ui/PriceListSelector', () => ({
    default: ({ value, onChange }) => (
        <select
            data-testid="price-list-selector"
            value={value === null || value === undefined ? '' : String(value)}
            onChange={(e) => {
                const v = e.target.value;
                onChange(v ? Number.parseInt(v, 10) : null);
            }}
        >
            <option value="">Default</option>
            <option value="10">VIP Plan</option>
        </select>
    ),
}));

describe('EditPatientModal', () => {
    let queryClient;

    beforeEach(() => {
        vi.clearAllMocks();
        queryClient = new QueryClient({
            defaultOptions: { queries: { retry: false } },
        });
    });

    const renderModal = (props) => {
        return render(
            <QueryClientProvider client={queryClient}>
                <EditPatientModal {...props} />
            </QueryClientProvider>
        );
    };

    it('sanitizes empty default_price_list_id and age to null on submit', async () => {
        const onSave = vi.fn();
        const initialData = {
            id: 329,
            name: 'John Doe',
            age: null,
            phone: '01012345678',
            address: 'Cairo',
            default_price_list_id: null,
            assigned_doctor_id: null,
        };

        renderModal({
            isOpen: true,
            onClose: vi.fn(),
            onSave,
            initialData,
        });

        const saveButton = screen.getByRole('button', { name: 'common.save' });
        fireEvent.click(saveButton);

        await waitFor(() => {
            expect(onSave).toHaveBeenCalledTimes(1);
        });

        const payload = onSave.mock.calls[0][0];
        expect(payload.name).toBe('John Doe');
        expect(payload.age).toBeNull();
        expect(payload.default_price_list_id).toBeNull();
        expect(payload.assigned_doctor_id).toBeNull();
    });

    it('parses numeric values correctly when entered', async () => {
        const onSave = vi.fn();
        const initialData = {
            id: 329,
            name: 'Jane Doe',
            age: 25,
            phone: '01099999999',
            address: 'Alexandria',
            default_price_list_id: 10,
            assigned_doctor_id: 2,
        };

        renderModal({
            isOpen: true,
            onClose: vi.fn(),
            onSave,
            initialData,
        });

        const saveButton = screen.getByRole('button', { name: 'common.save' });
        fireEvent.click(saveButton);

        await waitFor(() => {
            expect(onSave).toHaveBeenCalledTimes(1);
        });

        const payload = onSave.mock.calls[0][0];
        expect(payload.name).toBe('Jane Doe');
        expect(payload.age).toBe(25);
        expect(payload.default_price_list_id).toBe(10);
        expect(payload.assigned_doctor_id).toBe(2);
    });
});
